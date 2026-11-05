import hashlib
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from posts.db import IdempotencyRecord, get_async_session

logger = logging.getLogger(__name__)

STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
# How long a retry with the same key gets the stored response.
KEY_RETENTION = timedelta(hours=24)
# A claim this old belongs to a request that died, so a retry may take it over.
ABANDONED_AFTER = timedelta(minutes=5)


def file_digest(file: UploadFile) -> str:
    """Hash an upload's content. File names aren't used: clients may generate them per attempt."""
    digest = hashlib.file_digest(file.file, "sha256").hexdigest()
    file.file.seek(0)
    return digest


class Idempotency:
    """Runs a write once per key, so a repeated request can't repeat its effect.

    The key is claimed in its own commit before the write starts. If the write
    succeeds its response is stored for replay; if it fails the claim is released,
    so a retry runs normally. A crash between the write's commit and storing the
    response leaves a claim that a retry can take over after ABANDONED_AFTER, which
    would repeat that write.
    """

    def __init__(self, request: Request, session: AsyncSession, key: str | None):
        self.request = request
        self.session = session
        self.key = key

    async def run(self, user_id, payload: Any, operation: Callable[[], Awaitable[Any]]):
        if self.key is None:
            return await operation()

        fingerprint = self._fingerprint(payload)
        claim = await self._claim(user_id, fingerprint)
        if isinstance(claim, JSONResponse):
            return claim

        try:
            result = await operation()
        except Exception:
            await self._release(user_id, claim)
            raise

        await self._store(user_id, claim, result)
        return result

    def _fingerprint(self, payload: Any) -> str:
        content = json.dumps(
            {
                "method": self.request.method,
                "path": self.request.url.path,
                "payload": payload,
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(content.encode()).hexdigest()

    def _key_filter(self, user_id):
        return (
            IdempotencyRecord.user_id == user_id,
            IdempotencyRecord.key == self.key,
        )

    async def _claim(self, user_id, fingerprint: str) -> datetime | JSONResponse:
        """Returns the claim's timestamp, or the stored response to replay."""
        now = datetime.utcnow()
        await self.session.execute(
            delete(IdempotencyRecord).where(IdempotencyRecord.created_at < now - KEY_RETENTION)
        )
        try:
            await self.session.execute(
                insert(IdempotencyRecord).values(
                    user_id=user_id,
                    key=self.key,
                    fingerprint=fingerprint,
                    status=STATUS_IN_PROGRESS,
                    locked_at=now,
                    created_at=now,
                )
            )
            await self.session.commit()
            return now
        except IntegrityError:
            await self.session.rollback()

        result = await self.session.execute(
            select(
                IdempotencyRecord.fingerprint,
                IdempotencyRecord.status,
                IdempotencyRecord.locked_at,
                IdempotencyRecord.response_status,
                IdempotencyRecord.response_body,
            ).where(*self._key_filter(user_id))
        )
        existing = result.one_or_none()
        if existing is None:
            self._raise_in_progress()
        if existing.fingerprint != fingerprint:
            raise HTTPException(
                status_code=422,
                detail="This Idempotency-Key was already used with a different request",
            )
        if existing.status == STATUS_COMPLETED:
            return JSONResponse(
                content=existing.response_body,
                status_code=existing.response_status,
                headers={"Idempotency-Replayed": "true"},
            )
        if existing.locked_at < now - ABANDONED_AFTER:
            taken_over = await self.session.execute(
                update(IdempotencyRecord)
                .where(
                    *self._key_filter(user_id),
                    IdempotencyRecord.status == STATUS_IN_PROGRESS,
                    IdempotencyRecord.locked_at == existing.locked_at,
                )
                .values(locked_at=now)
            )
            await self.session.commit()
            if taken_over.rowcount == 1:
                return now
        self._raise_in_progress()

    @staticmethod
    def _raise_in_progress():
        raise HTTPException(
            status_code=409,
            detail="A request with this Idempotency-Key is still in progress",
            headers={"Retry-After": "1"},
        )

    async def _release(self, user_id, claim: datetime) -> None:
        # Failing here must not hide the error that caused the release.
        try:
            await self.session.rollback()
            await self.session.execute(
                delete(IdempotencyRecord).where(
                    *self._key_filter(user_id),
                    IdempotencyRecord.locked_at == claim,
                )
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            logger.exception("Could not release an idempotency key")

    async def _store(self, user_id, claim: datetime, result: Any) -> None:
        # The write has already committed, so failing here must not report it as failed.
        route = self.request.scope.get("route")
        try:
            await self.session.execute(
                update(IdempotencyRecord)
                .where(
                    *self._key_filter(user_id),
                    IdempotencyRecord.locked_at == claim,
                )
                .values(
                    status=STATUS_COMPLETED,
                    response_status=getattr(route, "status_code", None) or 200,
                    response_body=jsonable_encoder(result),
                )
            )
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            logger.exception("Could not store an idempotent response")


async def get_idempotency(
        request: Request,
        session: Annotated[AsyncSession, Depends(get_async_session)],
        key: Annotated[
            str | None,
            Header(
                alias="Idempotency-Key",
                min_length=1,
                max_length=255,
                description=(
                    "A unique value, such as a UUID, for this action. Sending the same "
                    "request with the same key within 24 hours returns the first "
                    "response instead of repeating the action."
                ),
            ),
        ] = None,
) -> Idempotency:
    return Idempotency(request, session, key)
