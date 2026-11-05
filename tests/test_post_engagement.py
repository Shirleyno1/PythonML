import asyncio
import io
import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langsmith import Client
from langsmith.run_helpers import is_traceable_function, tracing_context
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import posts.app as posts_app
from chatbot.routes.ai import user_delete
from observability import tracing
from observability.tracing import trace_engagement_input, trace_engagement_output
from posts.app import comments_router, points_router, posts_router, tasks_router
from posts.db import (
    Base,
    Comment,
    CommentReaction,
    IdempotencyRecord,
    PointTransaction,
    Post,
    PostImage,
    PostReaction,
    User,
    get_async_session,
    migrate_post_reactions,
)
from posts.idempotency import ABANDONED_AFTER, KEY_RETENTION, Idempotency
from posts.repository import PostRepository
from posts.schema import PointSource, PostReactionType, PostType, ReactionType
from posts.service import PostService
from posts.users import current_active_user, current_superuser


class Api:
    """Test client whose requests are made as whichever user is passed in."""

    def __init__(self, client, holder, session_maker):
        self.client = client
        self.holder = holder
        self.session_maker = session_maker

    def request(self, method, url, user, **kwargs):
        self.holder.user = user
        return self.client.request(method, url, **kwargs)

    def run(self, coroutine):
        return asyncio.run(coroutine)

    def make_post(self, owner, post_type=PostType.QUESTION, **fields):
        async def create():
            async with self.session_maker() as session:
                post = Post(user_id=owner.id, post_type=post_type.value, caption="c", **fields)
                session.add(post)
                await session.commit()
                return post.id

        return self.run(create())

    def comment(self, post_id, user, content="an answer"):
        response = self.request(
            "POST", f"/posts/{post_id}/comments", user, json={"content": content}
        )
        assert response.status_code == 201, response.text
        return response.json()["id"]

    def total_points(self, user):
        return self.request("GET", "/points/me", user).json()["total"]


def make_user(session, email):
    user = User(id=uuid.uuid4(), email=email, hashed_password="x", is_active=True)
    session.add(user)
    return user


@pytest.fixture
def api(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'engagement.db'}", poolclass=NullPool
    )
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def setup():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with session_maker() as session:
            users = [make_user(session, f"{name}@example.com") for name in ("asker", "alice", "bob")]
            await session.commit()
            return users

    asker, alice, bob = asyncio.run(setup())

    app = FastAPI()
    for router in (posts_router, comments_router, points_router, tasks_router):
        app.include_router(router)

    async def override_session():
        async with session_maker() as session:
            yield session

    holder = SimpleNamespace(user=None)
    app.dependency_overrides[get_async_session] = override_session
    app.dependency_overrides[current_active_user] = lambda: holder.user
    app.dependency_overrides[current_superuser] = lambda: holder.user

    with TestClient(app) as client:
        yield SimpleNamespace(
            http=Api(client, holder, session_maker), asker=asker, alice=alice, bob=bob
        )


def test_users_can_comment_and_read_comments(api):
    post_id = api.http.make_post(api.asker)

    created = api.http.request(
        "POST", f"/posts/{post_id}/comments", api.alice, json={"content": "  try this  "}
    )
    assert created.status_code == 201
    assert created.json()["content"] == "try this"
    assert created.json()["email"] == "alice@example.com"

    comments = api.http.request("GET", f"/posts/{post_id}/comments", api.bob).json()["comments"]
    assert [comment["content"] for comment in comments] == ["try this"]
    assert comments[0]["is_owner"] is False


def test_blank_comment_is_rejected(api):
    post_id = api.http.make_post(api.asker)
    response = api.http.request("POST", f"/posts/{post_id}/comments", api.alice, json={"content": "   "})
    assert response.status_code == 422


def test_cannot_comment_when_comments_are_disabled(api):
    post_id = api.http.make_post(api.asker, comments_disabled=True)
    response = api.http.request("POST", f"/posts/{post_id}/comments", api.alice, json={"content": "hi"})
    assert response.status_code == 403


def test_owner_can_toggle_comments_but_others_cannot(api):
    post_id = api.http.make_post(api.asker)

    denied = api.http.request("PATCH", f"/posts/{post_id}", api.alice, json={"commentsDisabled": True})
    assert denied.status_code == 403

    updated = api.http.request("PATCH", f"/posts/{post_id}", api.asker, json={"commentsDisabled": True})
    assert updated.json()["commentsDisabled"] is True
    blocked = api.http.request("POST", f"/posts/{post_id}/comments", api.alice, json={"content": "hi"})
    assert blocked.status_code == 403

    api.http.request("PATCH", f"/posts/{post_id}", api.asker, json={"commentsDisabled": False})
    api.http.comment(post_id, api.alice)


def test_upload_can_disable_comments(api, monkeypatch):
    monkeypatch.setattr(
        posts_app,
        "imagekit",
        SimpleNamespace(
            files=SimpleNamespace(
                upload=lambda **_: SimpleNamespace(url="http://image", name="a.png")
            )
        ),
    )
    response = api.http.request(
        "POST",
        "/posts/upload",
        api.asker,
        files={"file": ("a.png", io.BytesIO(b"x"), "image/png")},
        data={"commentsDisabled": "true"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["commentsDisabled"] is True


def test_private_post_is_hidden_from_other_users(api):
    post_id = api.http.make_post(api.asker, is_private=True)
    comment_id = api.http.comment(post_id, api.asker)

    for method, url, body in (
        ("GET", f"/posts/{post_id}/comments", None),
        ("POST", f"/posts/{post_id}/comments", {"content": "hi"}),
        ("PUT", f"/posts/{post_id}/reactions/love", None),
        ("DELETE", f"/posts/{post_id}/reactions/collect", None),
        ("PATCH", f"/posts/{post_id}", {"commentsDisabled": True}),
        ("PUT", f"/comments/{comment_id}/reaction", {"reaction": "up"}),
        ("POST", f"/comments/{comment_id}/points", {"points": 1}),
    ):
        assert api.http.request(method, url, api.alice, json=body).status_code == 404, url


def test_love_and_collect_are_independent_and_can_be_removed(api):
    post_id = api.http.make_post(api.asker)
    love = f"/posts/{post_id}/reactions/love"
    collect = f"/posts/{post_id}/reactions/collect"

    first = api.http.request("PUT", love, api.alice).json()
    assert first == {"love_count": 1, "collect_count": 0, "loved": True, "collected": False}

    repeated = api.http.request("PUT", love, api.alice).json()
    assert repeated["love_count"] == 1

    both = api.http.request("PUT", collect, api.alice).json()
    assert both == {"love_count": 1, "collect_count": 1, "loved": True, "collected": True}

    other = api.http.request("PUT", love, api.bob).json()
    assert other == {"love_count": 2, "collect_count": 1, "loved": True, "collected": False}

    removed = api.http.request("DELETE", love, api.alice).json()
    assert removed == {"love_count": 1, "collect_count": 1, "loved": False, "collected": True}


@pytest.mark.parametrize("reaction", ["up", "down", "meh"])
def test_thumbs_and_unknown_reactions_are_rejected_on_posts(api, reaction):
    post_id = api.http.make_post(api.asker)
    response = api.http.request("PUT", f"/posts/{post_id}/reactions/{reaction}", api.alice)
    assert response.status_code == 422


def test_old_post_thumb_route_is_gone(api):
    post_id = api.http.make_post(api.asker)
    response = api.http.request("PUT", f"/posts/{post_id}/reaction", api.alice, json={"reaction": "up"})
    assert response.status_code in (404, 405)


def test_collected_posts_lists_only_what_the_user_collected(api):
    collected = api.http.make_post(api.asker)
    loved_only = api.http.make_post(api.asker)
    uncollected = api.http.make_post(api.asker)
    api.http.request("PUT", f"/posts/{collected}/reactions/collect", api.alice)
    api.http.request("PUT", f"/posts/{loved_only}/reactions/love", api.alice)
    api.http.request("PUT", f"/posts/{uncollected}/reactions/collect", api.alice)
    api.http.request("DELETE", f"/posts/{uncollected}/reactions/collect", api.alice)

    posts = api.http.request("GET", "/posts/collected", api.alice).json()["posts"]
    assert [post["id"] for post in posts] == [collected]
    assert posts[0]["collected"] is True
    assert api.http.request("GET", "/posts/collected", api.bob).json()["posts"] == []


def test_collected_posts_hide_posts_that_are_private_to_someone_else(api):
    hidden = api.http.make_post(api.asker)
    own_private = api.http.make_post(api.alice, is_private=True)
    api.http.request("PUT", f"/posts/{hidden}/reactions/collect", api.alice)
    api.http.request("PUT", f"/posts/{own_private}/reactions/collect", api.alice)

    async def make_private():
        async with api.http.session_maker() as session:
            post = await session.get(Post, hidden)
            post.is_private = True
            await session.commit()

    api.http.run(make_private())

    posts = api.http.request("GET", "/posts/collected", api.alice).json()["posts"]
    assert [post["id"] for post in posts] == [own_private]


def test_old_thumb_table_is_replaced_and_new_table_is_left_alone(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE post_reactions (post_id VARCHAR NOT NULL, user_id CHAR(36) NOT NULL, "
            "reaction VARCHAR NOT NULL, PRIMARY KEY (post_id, user_id), "
            "CHECK (reaction IN ('up', 'down')))"
        ))
        connection.execute(text("INSERT INTO post_reactions VALUES ('p', 'u', 'up')"))

    insert_love = text("INSERT INTO post_reactions VALUES ('p', 'u', 'love')")
    insert_collect = text("INSERT INTO post_reactions VALUES ('p', 'u', 'collect')")
    with engine.begin() as connection:
        migrate_post_reactions(connection)
        assert "reaction" in inspect(connection).get_pk_constraint("post_reactions")["constrained_columns"]
        connection.execute(insert_love)
        connection.execute(insert_collect)

    with engine.begin() as connection:
        migrate_post_reactions(connection)
        assert connection.execute(text("SELECT count(*) FROM post_reactions")).scalar_one() == 2
    engine.dispose()


def test_comment_reactions_appear_in_comment_list(api):
    post_id = api.http.make_post(api.asker)
    comment_id = api.http.comment(post_id, api.alice)
    url = f"/comments/{comment_id}/reaction"

    api.http.request("PUT", url, api.asker, json={"reaction": "up"})
    api.http.request("PUT", url, api.bob, json={"reaction": "down"})

    comment = api.http.request("GET", f"/posts/{post_id}/comments", api.bob).json()["comments"][0]
    assert comment["thumbs_up"] == 1
    assert comment["thumbs_down"] == 1
    assert comment["my_reaction"] == "down"

    api.http.request("DELETE", url, api.bob)
    comment = api.http.request("GET", f"/posts/{post_id}/comments", api.bob).json()["comments"][0]
    assert comment["thumbs_down"] == 0
    assert comment["my_reaction"] is None


def test_question_owner_can_give_points_up_to_the_limit_across_comments(api):
    post_id = api.http.make_post(api.asker)
    alice_comment = api.http.comment(post_id, api.alice)
    bob_comment = api.http.comment(post_id, api.bob)

    first = api.http.request("POST", f"/comments/{alice_comment}/points", api.asker, json={"points": 3})
    assert first.status_code == 200
    assert first.json()["points_remaining"] == 2

    over = api.http.request("POST", f"/comments/{bob_comment}/points", api.asker, json={"points": 3})
    assert over.status_code == 400
    assert "2 remaining" in over.json()["detail"]

    assert api.http.request(
        "POST", f"/comments/{bob_comment}/points", api.asker, json={"points": 2}
    ).status_code == 200
    assert api.http.request(
        "POST", f"/comments/{alice_comment}/points", api.asker, json={"points": 1}
    ).status_code == 400

    assert api.http.total_points(api.alice) == 3
    assert api.http.total_points(api.bob) == 2
    assert api.http.total_points(api.asker) == 0

    comments = api.http.request("GET", f"/posts/{post_id}/comments", api.asker).json()["comments"]
    assert [comment["points_awarded"] for comment in comments] == [3, 2]


@pytest.mark.parametrize("points", [0, -1, 6])
def test_award_outside_range_is_rejected(api, points):
    post_id = api.http.make_post(api.asker)
    comment_id = api.http.comment(post_id, api.alice)
    response = api.http.request("POST", f"/comments/{comment_id}/points", api.asker, json={"points": points})
    assert response.status_code == 422
    assert api.http.total_points(api.alice) == 0


def test_share_post_comments_cannot_receive_points(api):
    post_id = api.http.make_post(api.asker, post_type=PostType.SHARE)
    comment_id = api.http.comment(post_id, api.alice)
    response = api.http.request("POST", f"/comments/{comment_id}/points", api.asker, json={"points": 1})
    assert response.status_code == 400
    assert api.http.total_points(api.alice) == 0


def test_only_question_owner_can_give_points(api):
    post_id = api.http.make_post(api.asker)
    comment_id = api.http.comment(post_id, api.alice)
    response = api.http.request("POST", f"/comments/{comment_id}/points", api.bob, json={"points": 1})
    assert response.status_code == 403


def test_owner_cannot_give_points_to_own_comment(api):
    post_id = api.http.make_post(api.asker)
    comment_id = api.http.comment(post_id, api.asker)
    response = api.http.request("POST", f"/comments/{comment_id}/points", api.asker, json={"points": 1})
    assert response.status_code == 400
    assert api.http.total_points(api.asker) == 0


def test_task_can_be_completed_once_for_its_points(api):
    task = api.http.request(
        "POST", "/tasks", api.asker, json={"title": "Fill in profile", "points": 10}
    )
    assert task.status_code == 201
    task_id = task.json()["id"]

    tasks = api.http.request("GET", "/tasks", api.alice).json()["tasks"]
    assert tasks[0]["completed"] is False

    completed = api.http.request("POST", f"/tasks/{task_id}/complete", api.alice)
    assert completed.status_code == 200
    assert completed.json()["total"] == 10

    again = api.http.request("POST", f"/tasks/{task_id}/complete", api.alice)
    assert again.status_code == 409
    assert api.http.total_points(api.alice) == 10

    tasks = api.http.request("GET", "/tasks", api.alice).json()["tasks"]
    assert tasks[0]["completed"] is True
    assert api.http.request("POST", f"/tasks/{task_id}/complete", api.bob).status_code == 200


def test_completing_missing_task_returns_404(api):
    assert api.http.request("POST", "/tasks/missing/complete", api.alice).status_code == 404


def test_point_history_covers_answers_and_tasks(api):
    post_id = api.http.make_post(api.asker)
    comment_id = api.http.comment(post_id, api.alice)
    api.http.request("POST", f"/comments/{comment_id}/points", api.asker, json={"points": 4})
    task_id = api.http.request(
        "POST", "/tasks", api.asker, json={"title": "t", "points": 7}
    ).json()["id"]
    api.http.request("POST", f"/tasks/{task_id}/complete", api.alice)

    points = api.http.request("GET", "/points/me", api.alice).json()
    assert points["total"] == 11
    assert {entry["source"] for entry in points["history"]} == {
        PointSource.ANSWER.value,
        PointSource.TASK.value,
    }


def test_post_listing_includes_engagement(api):
    question_id = api.http.make_post(api.asker)
    share_id = api.http.make_post(api.asker, post_type=PostType.SHARE)
    comment_id = api.http.comment(question_id, api.alice)
    api.http.request("POST", f"/comments/{comment_id}/points", api.asker, json={"points": 2})
    api.http.request("PUT", f"/posts/{question_id}/reactions/love", api.asker)

    posts = {post["id"]: post for post in api.http.request("GET", "/posts/mine", api.asker).json()["posts"]}
    question = posts[question_id]
    assert question["comment_count"] == 1
    assert question["love_count"] == 1
    assert question["loved"] is True
    assert question["collect_count"] == 0
    assert question["collected"] is False
    assert "thumbs_up" not in question
    assert question["points_awarded"] == 2
    assert question["points_remaining"] == 3
    assert question["commentsDisabled"] is False
    assert posts[share_id]["points_remaining"] is None


def test_deleting_post_removes_engagement_but_keeps_earned_points(api):
    post_id = api.http.make_post(api.asker)
    comment_id = api.http.comment(post_id, api.alice)
    api.http.request("POST", f"/comments/{comment_id}/points", api.asker, json={"points": 5})
    api.http.request("PUT", f"/posts/{post_id}/reactions/collect", api.alice)
    api.http.request("PUT", f"/comments/{comment_id}/reaction", api.bob, json={"reaction": "up"})

    async def delete_and_inspect():
        async with api.http.session_maker() as session:
            await PostRepository(session).delete_post(post_id, api.asker.id)
            counts = {}
            for model in (Comment, PostReaction, CommentReaction):
                counts[model.__name__] = len((await session.execute(select(model))).scalars().all())
            entry = (await session.execute(select(PointTransaction))).scalars().one()
            return counts, entry.post_id, entry.comment_id

    counts, ledger_post, ledger_comment = api.http.run(delete_and_inspect())
    assert counts == {"Comment": 0, "PostReaction": 0, "CommentReaction": 0}
    assert (ledger_post, ledger_comment) == (None, None)
    assert api.http.total_points(api.alice) == 5


@pytest.mark.parametrize(
    "method",
    [
        "update_post",
        "add_comment",
        "get_comments",
        "add_post_reaction",
        "remove_post_reaction",
        "get_collected_posts",
        "react_to_comment",
        "award_points",
        "get_my_points",
        "create_task",
        "get_tasks",
        "complete_task",
    ],
)
def test_engagement_service_methods_are_traced(method):
    assert is_traceable_function(getattr(PostService, method))


def test_engagement_trace_input_excludes_user_id_and_text():
    assert trace_engagement_input(
        {
            "self": object(),
            "post_id": "post-1",
            "user_id": "private-user-id",
            "content": "private comment",
            "title": "private title",
            "description": "private description",
        }
    ) == {"post_id": "post-1", "content_length": 15}


@pytest.mark.parametrize(
    ("reaction", "expected"),
    [(ReactionType.UP, "up"), (PostReactionType.COLLECT, "collect"), (None, None)],
)
def test_engagement_trace_input_records_reaction(reaction, expected):
    assert trace_engagement_input({"reaction": reaction})["reaction"] == expected


def test_engagement_trace_output_excludes_private_comment_fields():
    assert trace_engagement_output(
        {
            "id": "comment-1",
            "post_id": "post-1",
            "user_id": "private-user-id",
            "email": "private@example.com",
            "content": "private comment",
            "thumbs_up": 2,
        }
    ) == {"id": "comment-1", "post_id": "post-1", "thumbs_up": 2}


def test_engagement_trace_output_counts_lists_instead_of_copying_them():
    assert trace_engagement_output(
        {"total": 8, "history": [{"points": 5}, {"points": 3}]}
    ) == {"total": 8, "history_count": 2}


def test_traced_call_sends_only_filtered_data_and_records_failures(monkeypatch):
    monkeypatch.setattr(tracing.settings, "LANGSMITH_TRACING", True)

    @tracing.engagement_traceable("Add Comment")
    async def add_comment(post_id, user_id, content):
        if content == "fail":
            raise ValueError("rejected")
        return {"id": "comment-1", "email": "private@example.com", "content": content}

    client = Mock(spec=Client, tracing_sampling_rate=1.0)

    async def call():
        with tracing_context(client=client):
            await add_comment("post-1", "private-user-id", "private comment")
            with pytest.raises(ValueError):
                await add_comment("post-1", "private-user-id", "fail")

    asyncio.run(call())

    assert client.create_run.call_count == 2
    sent = repr(client.create_run.call_args_list) + repr(client.update_run.call_args_list)
    assert "post-1" in sent
    assert "rejected" in sent
    for private in ("private-user-id", "private comment", "private@example.com"):
        assert private not in sent


def keyed(key):
    return {"Idempotency-Key": key}


def stored_record(api, user, key="key-1"):
    async def load():
        async with api.http.session_maker() as session:
            return await session.get(IdempotencyRecord, (user.id, key))

    return api.http.run(load())


def test_comment_with_same_key_is_created_once_and_replayed(api):
    post_id = api.http.make_post(api.asker)
    url = f"/posts/{post_id}/comments"

    first = api.http.request("POST", url, api.alice, json={"content": "hi"}, headers=keyed("key-1"))
    second = api.http.request("POST", url, api.alice, json={"content": "hi"}, headers=keyed("key-1"))

    assert first.status_code == second.status_code == 201
    assert second.json() == first.json()
    assert "Idempotency-Replayed" not in first.headers
    assert second.headers["Idempotency-Replayed"] == "true"
    assert len(api.http.request("GET", url, api.alice).json()["comments"]) == 1


def test_requests_without_a_key_are_not_deduplicated(api):
    post_id = api.http.make_post(api.asker)
    api.http.comment(post_id, api.alice, "same")
    api.http.comment(post_id, api.alice, "same")

    url = f"/posts/{post_id}/comments"
    assert len(api.http.request("GET", url, api.alice).json()["comments"]) == 2


def test_different_keys_create_separate_comments(api):
    post_id = api.http.make_post(api.asker)
    url = f"/posts/{post_id}/comments"

    for key in ("key-1", "key-2"):
        api.http.request("POST", url, api.alice, json={"content": "hi"}, headers=keyed(key))

    assert len(api.http.request("GET", url, api.alice).json()["comments"]) == 2


def test_same_key_from_another_user_is_independent(api):
    post_id = api.http.make_post(api.asker)
    url = f"/posts/{post_id}/comments"

    alice = api.http.request("POST", url, api.alice, json={"content": "hi"}, headers=keyed("key-1"))
    bob = api.http.request("POST", url, api.bob, json={"content": "hi"}, headers=keyed("key-1"))

    assert "Idempotency-Replayed" not in bob.headers
    assert bob.json()["id"] != alice.json()["id"]
    assert bob.json()["email"] == "bob@example.com"


@pytest.mark.parametrize(
    "second_body, second_post",
    [({"content": "different"}, False), ({"content": "hi"}, True)],
)
def test_reusing_a_key_for_a_different_request_is_rejected(api, second_body, second_post):
    post_id = api.http.make_post(api.asker)
    other_post_id = api.http.make_post(api.asker)
    api.http.request(
        "POST", f"/posts/{post_id}/comments", api.alice, json={"content": "hi"}, headers=keyed("key-1")
    )

    response = api.http.request(
        "POST",
        f"/posts/{other_post_id if second_post else post_id}/comments",
        api.alice,
        json=second_body,
        headers=keyed("key-1"),
    )

    assert response.status_code == 422
    assert "different request" in response.json()["detail"]


def test_points_with_same_key_are_awarded_once(api):
    post_id = api.http.make_post(api.asker)
    comment_id = api.http.comment(post_id, api.alice)
    url = f"/comments/{comment_id}/points"

    for _ in range(3):
        response = api.http.request("POST", url, api.asker, json={"points": 2}, headers=keyed("key-1"))
        assert response.status_code == 200
        assert response.json()["points_remaining"] == 3

    assert api.http.total_points(api.alice) == 2


def test_completing_a_task_with_same_key_replays_success(api):
    task_id = api.http.request(
        "POST", "/tasks", api.asker, json={"title": "water", "points": 3}, headers=keyed("task")
    ).json()["id"]
    replayed_task = api.http.request(
        "POST", "/tasks", api.asker, json={"title": "water", "points": 3}, headers=keyed("task")
    )
    assert replayed_task.json()["id"] == task_id
    assert len(api.http.request("GET", "/tasks", api.asker).json()["tasks"]) == 1

    url = f"/tasks/{task_id}/complete"
    first = api.http.request("POST", url, api.alice, headers=keyed("key-1"))
    second = api.http.request("POST", url, api.alice, headers=keyed("key-1"))
    unkeyed = api.http.request("POST", url, api.alice)

    assert first.status_code == second.status_code == 200
    assert second.json() == first.json()
    assert unkeyed.status_code == 409
    assert api.http.total_points(api.alice) == 3


def test_failed_request_releases_its_key_so_a_retry_can_succeed(api):
    post_id = api.http.make_post(api.asker, comments_disabled=True)
    url = f"/posts/{post_id}/comments"

    rejected = api.http.request("POST", url, api.alice, json={"content": "hi"}, headers=keyed("key-1"))
    assert rejected.status_code == 403
    assert stored_record(api, api.alice) is None

    api.http.request("PATCH", f"/posts/{post_id}", api.asker, json={"commentsDisabled": False})
    retried = api.http.request("POST", url, api.alice, json={"content": "hi"}, headers=keyed("key-1"))
    assert retried.status_code == 201


def insert_record(api, user, *, locked_at, created_at=None, fingerprint=None):
    async def insert():
        async with api.http.session_maker() as session:
            session.add(
                IdempotencyRecord(
                    user_id=user.id,
                    key="key-1",
                    fingerprint=fingerprint or "unused",
                    status="in_progress",
                    locked_at=locked_at,
                    created_at=created_at or locked_at,
                )
            )
            await session.commit()

    api.http.run(insert())


def fingerprint_of(path, payload):
    request = SimpleNamespace(method="POST", url=SimpleNamespace(path=path))
    return Idempotency(request, None, "key-1")._fingerprint(payload)


def test_request_still_in_progress_returns_conflict(api):
    post_id = api.http.make_post(api.asker)
    url = f"/posts/{post_id}/comments"
    insert_record(
        api, api.alice, locked_at=datetime.utcnow(), fingerprint=fingerprint_of(url, {"content": "hi"})
    )

    response = api.http.request("POST", url, api.alice, json={"content": "hi"}, headers=keyed("key-1"))

    assert response.status_code == 409
    assert response.headers["Retry-After"] == "1"
    assert api.http.request("GET", url, api.alice).json()["comments"] == []


def test_abandoned_claim_can_be_taken_over(api):
    post_id = api.http.make_post(api.asker)
    url = f"/posts/{post_id}/comments"
    insert_record(
        api,
        api.alice,
        locked_at=datetime.utcnow() - ABANDONED_AFTER - timedelta(seconds=1),
        fingerprint=fingerprint_of(url, {"content": "hi"}),
    )

    response = api.http.request("POST", url, api.alice, json={"content": "hi"}, headers=keyed("key-1"))

    assert response.status_code == 201
    assert stored_record(api, api.alice).status == "completed"


def test_expired_key_can_be_used_again(api):
    post_id = api.http.make_post(api.asker)
    url = f"/posts/{post_id}/comments"
    expired = datetime.utcnow() - KEY_RETENTION - timedelta(seconds=1)
    insert_record(api, api.alice, locked_at=expired, fingerprint="an older request")

    response = api.http.request("POST", url, api.alice, json={"content": "hi"}, headers=keyed("key-1"))

    assert response.status_code == 201
    assert "Idempotency-Replayed" not in response.headers


def test_concurrent_requests_with_same_key_create_one_comment(api):
    post_id = api.http.make_post(api.asker)
    url = f"/posts/{post_id}/comments"
    api.http.holder.user = api.alice

    async def send_all():
        transport = httpx.ASGITransport(app=api.http.client.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await asyncio.gather(
                *[
                    client.post(url, json={"content": "hi"}, headers=keyed("key-1"))
                    for _ in range(8)
                ]
            )

    responses = api.http.run(send_all())

    assert {response.status_code for response in responses} <= {201, 409}
    created = [
        response
        for response in responses
        if response.status_code == 201 and "Idempotency-Replayed" not in response.headers
    ]
    assert len(created) == 1
    assert len(api.http.request("GET", url, api.alice).json()["comments"]) == 1


def test_upload_with_same_key_uploads_and_creates_once(api, monkeypatch):
    upload = Mock(return_value=SimpleNamespace(url="https://img.example/a.png", name="a.png"))
    monkeypatch.setattr(posts_app.imagekit.files, "upload", upload)

    def send(file_name, content=b"image"):
        return api.http.request(
            "POST",
            "/posts/upload",
            api.alice,
            data={"caption": "c", "type": "share"},
            files=[("file", (file_name, io.BytesIO(content), "image/png"))],
            headers=keyed("key-1"),
        )

    first = send("a.png")
    # Clients may generate a new file name per attempt, so only the content counts.
    second = send("renamed.png")
    different = send("a.png", content=b"another image")

    assert first.status_code == second.status_code == 200
    assert second.json() == first.json()
    assert upload.call_count == 1
    assert different.status_code == 422
    assert len(api.http.request("GET", "/posts/mine", api.alice).json()["posts"]) == 1


@pytest.mark.parametrize("key", ["", "x" * 256])
def test_invalid_key_is_rejected(api, key):
    post_id = api.http.make_post(api.asker)

    response = api.http.request(
        "POST", f"/posts/{post_id}/comments", api.alice, json={"content": "hi"}, headers=keyed(key)
    )

    assert response.status_code == 422


def test_owner_can_delete_post_with_images_and_engagement(api, monkeypatch):
    upload = Mock(return_value=SimpleNamespace(url="https://img.example/a.png", name="a.png"))
    monkeypatch.setattr(posts_app.imagekit.files, "upload", upload)
    post_id = api.http.request(
        "POST",
        "/posts/upload",
        api.asker,
        data={"caption": "c", "type": "question"},
        files=[("file", ("a.png", io.BytesIO(b"image"), "image/png"))],
    ).json()["id"]
    comment_id = api.http.comment(post_id, api.alice)
    api.http.request("POST", f"/comments/{comment_id}/points", api.asker, json={"points": 2})

    response = api.http.request("DELETE", f"/posts/{post_id}", api.asker)

    assert response.status_code == 200
    assert api.http.request("GET", "/posts/mine", api.asker).json()["posts"] == []
    assert api.http.request("GET", f"/posts/{post_id}/comments", api.asker).status_code == 404
    assert api.http.total_points(api.alice) == 2

    async def image_count():
        async with api.http.session_maker() as session:
            return len((await session.execute(select(PostImage))).scalars().all())

    assert api.http.run(image_count()) == 0


def test_deleting_a_deleted_post_returns_not_found(api):
    post_id = api.http.make_post(api.asker)
    api.http.request("DELETE", f"/posts/{post_id}", api.asker)

    assert api.http.request("DELETE", f"/posts/{post_id}", api.asker).status_code == 404


def test_other_users_cannot_delete_a_post(api):
    public_id = api.http.make_post(api.asker)
    private_id = api.http.make_post(api.asker, is_private=True)

    assert api.http.request("DELETE", f"/posts/{public_id}", api.alice).status_code == 403
    # Private posts look like they don't exist to anyone but their owner.
    assert api.http.request("DELETE", f"/posts/{private_id}", api.alice).status_code == 404
    assert len(api.http.request("GET", "/posts/mine", api.asker).json()["posts"]) == 2


def test_delete_rejects_a_malformed_post_id(api):
    assert api.http.request("DELETE", "/posts/not-a-uuid", api.asker).status_code == 400


def ask_ai_to_delete(api, post_id, user):
    async def delete():
        async with api.http.session_maker() as session:
            return await user_delete(SimpleNamespace(query=post_id), session, user)

    return api.http.run(delete())


def test_ai_delete_asks_for_confirmation_and_keeps_the_post(api):
    post_id = api.http.make_post(api.asker)

    result = ask_ai_to_delete(api, post_id, api.asker)

    assert result["status"] == "confirmation_required"
    assert result["post"] == {"id": post_id, "title": "c"}
    assert result["confirm"] == {"method": "DELETE", "path": f"/posts/{post_id}"}
    assert len(api.http.request("GET", "/posts/mine", api.asker).json()["posts"]) == 1

    # The confirmation step is the regular delete call.
    assert api.http.request("DELETE", result["confirm"]["path"], api.asker).status_code == 200
    assert api.http.request("GET", "/posts/mine", api.asker).json()["posts"] == []


@pytest.mark.parametrize("private", [False, True])
def test_ai_delete_of_another_users_post_is_not_offered(api, private):
    post_id = api.http.make_post(api.asker, is_private=private)

    result = ask_ai_to_delete(api, post_id, api.alice)

    assert result["status"] == "not_found"
    assert "post" not in result


def test_ai_delete_of_a_missing_post_is_not_offered(api):
    assert ask_ai_to_delete(api, "post 15", api.asker)["status"] == "not_found"
