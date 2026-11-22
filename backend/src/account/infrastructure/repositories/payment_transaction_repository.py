from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.account.application.ports.payment_ports import (
    PaymentTransactionRecordDTO,
    PaymentTransactionRepositoryPort,
)
from src.account.infrastructure.orm.user_orm import PaymentTransactionORM


def _to_dto(row: PaymentTransactionORM) -> PaymentTransactionRecordDTO:
    return PaymentTransactionRecordDTO(
        id=row.id,
        user_id=row.user_id,
        transaction_ref=row.transaction_ref,
        gateway_provider=row.gateway_provider,
        amount_vnd=row.amount_vnd,
        currency=row.currency,
        status=row.status,
        qr_code_url=row.qr_code_url,
        webhook_signature_verified=row.webhook_signature_verified,
        paid_at=row.paid_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyPaymentTransactionRepository(PaymentTransactionRepositoryPort):
    """SQLAlchemy 2.0 Async Repository for `payment_transactions`.

    Only performs add/flush; transactions are committed by AsyncUnitOfWork.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_recent_pending(
        self,
        *,
        user_id: UUID,
        amount_vnd: int,
        since: datetime,
    ) -> PaymentTransactionRecordDTO | None:
        stmt = (
            select(PaymentTransactionORM)
            .where(
                PaymentTransactionORM.user_id == user_id,
                PaymentTransactionORM.amount_vnd == amount_vnd,
                PaymentTransactionORM.status == "PENDING",
                PaymentTransactionORM.created_at >= since,
            )
            .order_by(PaymentTransactionORM.created_at.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_dto(row) if row is not None else None

    async def find_by_id(self, transaction_id: UUID) -> PaymentTransactionRecordDTO | None:
        stmt = select(PaymentTransactionORM).where(PaymentTransactionORM.id == transaction_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_dto(row) if row is not None else None

    async def find_by_id_for_update(
        self, transaction_id: UUID
    ) -> PaymentTransactionRecordDTO | None:
        stmt = (
            select(PaymentTransactionORM)
            .where(PaymentTransactionORM.id == transaction_id)
            .with_for_update()
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_dto(row) if row is not None else None

    async def find_by_ref(self, transaction_ref: str) -> PaymentTransactionRecordDTO | None:
        stmt = select(PaymentTransactionORM).where(
            PaymentTransactionORM.transaction_ref == transaction_ref
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_dto(row) if row is not None else None

    async def find_by_ref_for_update(
        self, transaction_ref: str
    ) -> PaymentTransactionRecordDTO | None:
        stmt = (
            select(PaymentTransactionORM)
            .where(PaymentTransactionORM.transaction_ref == transaction_ref)
            .with_for_update()
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _to_dto(row) if row is not None else None

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        limit: int = 50,
    ) -> list[PaymentTransactionRecordDTO]:
        stmt = (
            select(PaymentTransactionORM)
            .where(PaymentTransactionORM.user_id == user_id)
            .order_by(PaymentTransactionORM.created_at.desc(), PaymentTransactionORM.id.desc())
            .limit(max(1, min(limit, 100)))
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_dto(r) for r in rows]

    async def create_pending(
        self,
        *,
        transaction_id: UUID,
        user_id: UUID,
        transaction_ref: str,
        gateway_provider: str,
        amount_vnd: int,
        qr_code_url: str | None,
        now: datetime,
    ) -> PaymentTransactionRecordDTO:
        orm_obj = PaymentTransactionORM(
            id=transaction_id,
            user_id=user_id,
            transaction_ref=transaction_ref,
            gateway_provider=gateway_provider,
            amount_vnd=amount_vnd,
            currency="VND",
            status="PENDING",
            qr_code_url=qr_code_url,
            webhook_signature_verified=False,
            paid_at=None,
            created_at=now,
            updated_at=now,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        return _to_dto(orm_obj)

    async def mark_paid(
        self,
        transaction_id: UUID,
        *,
        paid_at: datetime,
        webhook_signature_verified: bool,
    ) -> PaymentTransactionRecordDTO | None:
        stmt = (
            select(PaymentTransactionORM)
            .where(PaymentTransactionORM.id == transaction_id)
            .with_for_update()
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None or row.status != "PENDING":
            return None

        row.status = "PAID"
        row.paid_at = paid_at
        row.webhook_signature_verified = webhook_signature_verified
        await self._session.flush()
        await self._session.refresh(row)
        return _to_dto(row)
