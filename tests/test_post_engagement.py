import asyncio
import io
import uuid
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import posts.app as posts_app
from posts.app import comments_router, points_router, posts_router, tasks_router
from posts.db import (
    Base,
    Comment,
    CommentReaction,
    PointTransaction,
    Post,
    PostReaction,
    User,
    get_async_session,
)
from posts.repository import PostRepository
from posts.schema import PointSource, PostType
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
        ("PUT", f"/posts/{post_id}/reaction", {"reaction": "up"}),
        ("PATCH", f"/posts/{post_id}", {"commentsDisabled": True}),
        ("PUT", f"/comments/{comment_id}/reaction", {"reaction": "up"}),
        ("POST", f"/comments/{comment_id}/points", {"points": 1}),
    ):
        assert api.http.request(method, url, api.alice, json=body).status_code == 404, url


def test_post_reactions_are_one_per_user_and_can_change(api):
    post_id = api.http.make_post(api.asker)
    url = f"/posts/{post_id}/reaction"

    first = api.http.request("PUT", url, api.alice, json={"reaction": "up"}).json()
    assert first == {"thumbs_up": 1, "thumbs_down": 0, "my_reaction": "up"}

    repeated = api.http.request("PUT", url, api.alice, json={"reaction": "up"}).json()
    assert repeated["thumbs_up"] == 1

    changed = api.http.request("PUT", url, api.alice, json={"reaction": "down"}).json()
    assert changed == {"thumbs_up": 0, "thumbs_down": 1, "my_reaction": "down"}

    other = api.http.request("PUT", url, api.bob, json={"reaction": "down"}).json()
    assert other["thumbs_down"] == 2

    removed = api.http.request("DELETE", url, api.alice).json()
    assert removed == {"thumbs_up": 0, "thumbs_down": 1, "my_reaction": None}


def test_invalid_reaction_is_rejected(api):
    post_id = api.http.make_post(api.asker)
    response = api.http.request("PUT", f"/posts/{post_id}/reaction", api.alice, json={"reaction": "meh"})
    assert response.status_code == 422


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
    api.http.request("PUT", f"/posts/{question_id}/reaction", api.asker, json={"reaction": "up"})

    posts = {post["id"]: post for post in api.http.request("GET", "/posts/mine", api.asker).json()["posts"]}
    question = posts[question_id]
    assert question["comment_count"] == 1
    assert question["thumbs_up"] == 1
    assert question["my_reaction"] == "up"
    assert question["points_awarded"] == 2
    assert question["points_remaining"] == 3
    assert question["commentsDisabled"] is False
    assert posts[share_id]["points_remaining"] is None


def test_deleting_post_removes_engagement_but_keeps_earned_points(api):
    post_id = api.http.make_post(api.asker)
    comment_id = api.http.comment(post_id, api.alice)
    api.http.request("POST", f"/comments/{comment_id}/points", api.asker, json={"points": 5})
    api.http.request("PUT", f"/posts/{post_id}/reaction", api.alice, json={"reaction": "up"})
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
