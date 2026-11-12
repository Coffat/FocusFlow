"""A second concurrent reservation cannot spend credits held by the first."""

from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy import delete
from uuid6 import uuid7

from src.account.infrastructure.adapters.quota_facade_adapter import QuotaFacadeAdapter
from src.account.infrastructure.orm.user_orm import UserORM
from src.account.public_api import QuotaExceededException
from src.shared_kernel.infrastructure.database.session import async_session_factory


@settings(max_examples=9, derandomize=True, deadline=None)
@given(first=st.integers(1, 3), second=st.integers(1, 3))
async def test_reservations_never_exceed_available_credits(first: int, second: int) -> None:
    user_id = uuid7()
    async with async_session_factory() as session:
        session.add(
            UserORM(
                id=user_id,
                email=f"quota_property_{user_id.hex[:12]}@focusflow.vn",
                password_hash="argon2id$mockhash",
                full_name="Quota Property Learner",
                timezone="Asia/Ho_Chi_Minh",
                role="LEARNER",
                tier="FREE",
                is_locked=False,
            )
        )
        await session.commit()
    try:
        async with async_session_factory() as session:
            facade = QuotaFacadeAdapter(session=session, default_free_credits=3)
            await facade.reserve_quota(user_id=user_id, cost=first)
            await session.commit()
            if first + second <= 3:
                await facade.reserve_quota(user_id=user_id, cost=second)
            else:
                try:
                    await facade.reserve_quota(user_id=user_id, cost=second)
                except QuotaExceededException:
                    pass
                else:
                    raise AssertionError("Credits already reserved were spent twice")
    finally:
        async with async_session_factory() as session:
            await session.execute(delete(UserORM).where(UserORM.id == user_id))
            await session.commit()
