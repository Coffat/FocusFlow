from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PaymentTransactionRecordDTO:
    """Immutable persistence snapshot of a PaymentTransaction row."""

    id: UUID
    user_id: UUID
    transaction_ref: str
    gateway_provider: str
    amount_vnd: int
    currency: str
    status: str
    qr_code_url: str | None
    webhook_signature_verified: bool
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PaymentCheckoutPayloadDTO:
    """Checkout details returned by a PaymentProviderPort implementation."""

    provider: str
    checkout_url: str
    qr_code_url: str
    is_mock_provider: bool


class PaymentTransactionRepositoryPort(Protocol):
    """Driven port for `payment_transactions` persistence in Account context."""

    async def find_recent_pending(
        self,
        *,
        user_id: UUID,
        amount_vnd: int,
        since: datetime,
    ) -> PaymentTransactionRecordDTO | None: ...

    async def find_by_id(self, transaction_id: UUID) -> PaymentTransactionRecordDTO | None: ...

    async def find_by_id_for_update(
        self, transaction_id: UUID
    ) -> PaymentTransactionRecordDTO | None: ...

    async def find_by_ref(self, transaction_ref: str) -> PaymentTransactionRecordDTO | None: ...

    async def find_by_ref_for_update(
        self, transaction_ref: str
    ) -> PaymentTransactionRecordDTO | None: ...

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        limit: int = 50,
    ) -> list[PaymentTransactionRecordDTO]: ...

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
    ) -> PaymentTransactionRecordDTO: ...

    async def mark_paid(
        self,
        transaction_id: UUID,
        *,
        paid_at: datetime,
        webhook_signature_verified: bool,
    ) -> PaymentTransactionRecordDTO | None: ...


class PaymentProviderPort(Protocol):
    """Driven port for external or local-mock payment gateway checkout creation."""

    def create_checkout(
        self,
        *,
        transaction_id: UUID,
        transaction_ref: str,
        plan_code: str,
        amount_vnd: int,
    ) -> PaymentCheckoutPayloadDTO: ...
