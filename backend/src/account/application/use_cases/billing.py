from datetime import UTC, datetime, timedelta
from uuid import UUID

from uuid6 import uuid7

from src.account.application.dtos.billing import (
    BillingPlanDTO,
    BillingWebhookResponseDTO,
    CheckoutResponseDTO,
    CreateCheckoutRequestDTO,
    PaymentTransactionDTO,
)
from src.account.application.ports.payment_ports import (
    PaymentProviderPort,
    PaymentTransactionRecordDTO,
    PaymentTransactionRepositoryPort,
)
from src.account.application.ports.user_repository_port import UserRepositoryPort
from src.account.domain.exceptions.billing import (
    InvalidPaymentPlanError,
    InvalidWebhookPayloadError,
    PaymentTransactionNotFoundError,
)
from src.shared_kernel.application.uow import AsyncUnitOfWork

PREMIUM_MONTHLY_AI_QUOTA = 300
PREMIUM_MAX_ACTIVE_ROADMAPS = 15

BILLING_PLANS: tuple[BillingPlanDTO, ...] = (
    BillingPlanDTO(
        plan_code="PREMIUM_MONTHLY",
        name="Premium Hàng Tháng",
        amount_vnd=99_000,
        currency="VND",
        billing_cycle="MONTHLY",
        ai_monthly_limit=PREMIUM_MONTHLY_AI_QUOTA,
        max_active_roadmaps=PREMIUM_MAX_ACTIVE_ROADMAPS,
    ),
    BillingPlanDTO(
        plan_code="PREMIUM_YEARLY",
        name="Premium Hàng Năm",
        amount_vnd=990_000,
        currency="VND",
        billing_cycle="YEARLY",
        ai_monthly_limit=PREMIUM_MONTHLY_AI_QUOTA,
        max_active_roadmaps=PREMIUM_MAX_ACTIVE_ROADMAPS,
    ),
)

PLAN_PRICING_VND: dict[str, int] = {plan.plan_code: plan.amount_vnd for plan in BILLING_PLANS}
_PLAN_REF_PREFIX: dict[str, str] = {
    "PREMIUM_MONTHLY": "FF-PM-",
    "PREMIUM_YEARLY": "FF-PY-",
}
PENDING_CHECKOUT_TTL = timedelta(minutes=15)
ALLOWED_SETTLEMENT_EVENT_TYPES: frozenset[str] = frozenset(
    {"payment.succeeded", "payment_succeeded", "paid"}
)


def infer_plan_code(transaction_ref: str, amount_vnd: int) -> str:
    if transaction_ref.startswith("FF-PY-") or amount_vnd >= PLAN_PRICING_VND["PREMIUM_YEARLY"]:
        return "PREMIUM_YEARLY"
    return "PREMIUM_MONTHLY"


def _to_transaction_dto(rec: PaymentTransactionRecordDTO) -> PaymentTransactionDTO:
    return PaymentTransactionDTO(
        id=rec.id,
        transaction_ref=rec.transaction_ref,
        plan_code=infer_plan_code(rec.transaction_ref, rec.amount_vnd),
        amount_vnd=rec.amount_vnd,
        currency=rec.currency,
        status=rec.status,
        provider=rec.gateway_provider,
        qr_code_url=rec.qr_code_url,
        webhook_signature_verified=rec.webhook_signature_verified,
        paid_at=rec.paid_at,
        created_at=rec.created_at,
    )


class CreateBillingCheckoutUseCase:
    """Create or reuse a 15-minute PENDING checkout transaction (UC-04/05)."""

    def __init__(
        self,
        *,
        payment_repo: PaymentTransactionRepositoryPort,
        payment_provider: PaymentProviderPort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self._payment_repo = payment_repo
        self._payment_provider = payment_provider
        self._uow = uow

    async def execute(
        self,
        *,
        user_id: UUID,
        request: CreateCheckoutRequestDTO,
        now: datetime | None = None,
    ) -> CheckoutResponseDTO:
        plan_code = request.plan_code
        amount_vnd = PLAN_PRICING_VND.get(plan_code)
        if amount_vnd is None:
            raise InvalidPaymentPlanError(f"Unsupported plan_code: {plan_code}")

        effective_now = now or datetime.now(UTC)
        cutoff = effective_now - PENDING_CHECKOUT_TTL

        # Validate provider availability FIRST (fail-closed -> BillingUnavailableError / 503)
        # Reuse existing non-expired PENDING transaction if present
        existing = await self._payment_repo.find_recent_pending(
            user_id=user_id,
            amount_vnd=amount_vnd,
            since=cutoff,
        )
        if existing is not None:
            checkout = self._payment_provider.create_checkout(
                transaction_id=existing.id,
                transaction_ref=existing.transaction_ref,
                plan_code=plan_code,
                amount_vnd=existing.amount_vnd,
            )
            return CheckoutResponseDTO(
                transaction_id=existing.id,
                transaction_ref=existing.transaction_ref,
                plan_code=plan_code,
                amount_vnd=existing.amount_vnd,
                status=existing.status,
                provider=existing.gateway_provider,
                checkout_url=checkout.checkout_url,
                qr_code_url=existing.qr_code_url or checkout.qr_code_url,
                expires_at=existing.created_at + PENDING_CHECKOUT_TTL,
                is_mock_provider=checkout.is_mock_provider,
            )

        new_txn_id = uuid7()
        prefix = _PLAN_REF_PREFIX[plan_code]
        txn_ref = f"{prefix}{new_txn_id.hex[:16].upper()}"
        checkout = self._payment_provider.create_checkout(
            transaction_id=new_txn_id,
            transaction_ref=txn_ref,
            plan_code=plan_code,
            amount_vnd=amount_vnd,
        )

        async with self._uow:
            created = await self._payment_repo.create_pending(
                transaction_id=new_txn_id,
                user_id=user_id,
                transaction_ref=txn_ref,
                gateway_provider=checkout.provider,
                amount_vnd=amount_vnd,
                qr_code_url=checkout.qr_code_url,
                now=effective_now,
            )
            await self._uow.commit()

        return CheckoutResponseDTO(
            transaction_id=created.id,
            transaction_ref=created.transaction_ref,
            plan_code=plan_code,
            amount_vnd=created.amount_vnd,
            status=created.status,
            provider=created.gateway_provider,
            checkout_url=checkout.checkout_url,
            qr_code_url=created.qr_code_url or checkout.qr_code_url,
            expires_at=created.created_at + PENDING_CHECKOUT_TTL,
            is_mock_provider=checkout.is_mock_provider,
        )


class ListBillingTransactionsUseCase:
    """List billing transactions belonging to the authenticated learner."""

    def __init__(self, *, payment_repo: PaymentTransactionRepositoryPort) -> None:
        self._payment_repo = payment_repo

    async def execute(self, *, user_id: UUID, limit: int = 50) -> list[PaymentTransactionDTO]:
        rows = await self._payment_repo.list_for_user(user_id, limit=limit)
        return [_to_transaction_dto(r) for r in rows]


class SettlePaymentTransactionUseCase:
    """Idempotently settle a PENDING transaction -> PAID and upgrade user to PREMIUM (UC-27).

    Uses row-level locking (`SELECT ... FOR UPDATE`) inside `AsyncUnitOfWork` so concurrent
    webhook deliveries for the same transaction never double-credit AI quota or duplicate
    entitlement upgrades.
    """

    def __init__(
        self,
        *,
        payment_repo: PaymentTransactionRepositoryPort,
        user_repo: UserRepositoryPort,
        uow: AsyncUnitOfWork,
    ) -> None:
        self._payment_repo = payment_repo
        self._user_repo = user_repo
        self._uow = uow

    async def execute(
        self,
        *,
        transaction_id: UUID | None = None,
        transaction_ref: str | None = None,
        event_type: str,
        payment_status: str,
        amount_vnd: int,
        currency: str,
        payload_user_id: UUID | None = None,
        webhook_signature_verified: bool = True,
        now: datetime | None = None,
    ) -> BillingWebhookResponseDTO:
        if not webhook_signature_verified:
            raise InvalidWebhookPayloadError("Webhook signature verification is required.")

        normalized_event = event_type.strip().lower()
        if normalized_event not in ALLOWED_SETTLEMENT_EVENT_TYPES:
            raise InvalidWebhookPayloadError(
                f"Unsupported webhook event_type for settlement: '{event_type}'."
            )

        normalized_status = payment_status.strip().upper()
        if normalized_status != "PAID":
            raise InvalidWebhookPayloadError(
                f"Webhook payment status '{payment_status}' is not eligible for settlement."
            )

        if amount_vnd <= 0:
            raise InvalidWebhookPayloadError("Webhook amount_vnd must be positive.")

        normalized_currency = currency.strip().upper()
        if not normalized_currency:
            raise InvalidWebhookPayloadError("Webhook currency is required.")

        effective_now = now or datetime.now(UTC)
        async with self._uow:
            record: PaymentTransactionRecordDTO | None = None
            if transaction_id is not None:
                record = await self._payment_repo.find_by_id_for_update(transaction_id)
            elif transaction_ref:
                record = await self._payment_repo.find_by_ref_for_update(transaction_ref)

            if record is None:
                raise PaymentTransactionNotFoundError("Không tìm thấy giao dịch thanh toán.")

            if (
                transaction_id is not None
                and transaction_ref
                and record.transaction_ref != transaction_ref
            ):
                raise InvalidWebhookPayloadError(
                    "Webhook transaction_ref does not match transaction_id."
                )

            if payload_user_id is not None and record.user_id != payload_user_id:
                raise InvalidWebhookPayloadError(
                    "Webhook user_id does not match payment transaction owner."
                )

            if amount_vnd != record.amount_vnd:
                raise InvalidWebhookPayloadError(
                    f"Webhook amount_vnd ({amount_vnd}) does not match expected "
                    f"transaction amount ({record.amount_vnd})."
                )

            if normalized_currency != record.currency.strip().upper():
                raise InvalidWebhookPayloadError(
                    f"Webhook currency ({normalized_currency}) does not match expected "
                    f"currency ({record.currency})."
                )

            # Idempotency guard under FOR UPDATE lock: already PAID -> no-op
            if record.status == "PAID":
                return BillingWebhookResponseDTO(
                    status="PAID",
                    transaction_id=record.id,
                    already_processed=True,
                )

            if record.status != "PENDING":
                raise InvalidWebhookPayloadError(
                    f"Cannot settle payment transaction in status '{record.status}'."
                )

            updated = await self._payment_repo.mark_paid(
                record.id,
                paid_at=effective_now,
                webhook_signature_verified=webhook_signature_verified,
            )
            if updated is None:
                return BillingWebhookResponseDTO(
                    status="PAID",
                    transaction_id=record.id,
                    already_processed=True,
                )

            await self._user_repo.upgrade_user_to_premium(
                record.user_id,
                premium_monthly_limit=PREMIUM_MONTHLY_AI_QUOTA,
            )
            await self._uow.commit()

        return BillingWebhookResponseDTO(
            status="PAID",
            transaction_id=updated.id,
            already_processed=False,
        )

    async def execute_mock_confirm(
        self,
        *,
        transaction_id: UUID,
        expected_user_id: UUID,
        now: datetime | None = None,
    ) -> BillingWebhookResponseDTO:
        """Confirm a local_mock PENDING transaction in dev/test environments only."""
        effective_now = now or datetime.now(UTC)
        async with self._uow:
            record = await self._payment_repo.find_by_id_for_update(transaction_id)
            if record is None or record.user_id != expected_user_id:
                raise PaymentTransactionNotFoundError("Không tìm thấy giao dịch thanh toán.")

            if record.status == "PAID":
                return BillingWebhookResponseDTO(
                    status="PAID",
                    transaction_id=record.id,
                    already_processed=True,
                )

            if record.status != "PENDING":
                raise InvalidWebhookPayloadError(
                    f"Cannot settle payment transaction in status '{record.status}'."
                )

            updated = await self._payment_repo.mark_paid(
                record.id,
                paid_at=effective_now,
                webhook_signature_verified=True,
            )
            if updated is None:
                return BillingWebhookResponseDTO(
                    status="PAID",
                    transaction_id=record.id,
                    already_processed=True,
                )

            await self._user_repo.upgrade_user_to_premium(
                record.user_id,
                premium_monthly_limit=PREMIUM_MONTHLY_AI_QUOTA,
            )
            await self._uow.commit()

        return BillingWebhookResponseDTO(
            status="PAID",
            transaction_id=updated.id,
            already_processed=False,
        )
