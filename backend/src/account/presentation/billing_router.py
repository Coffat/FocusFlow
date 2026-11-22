import hashlib
import hmac
import json
import math
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.account.application.dtos.billing import (
    BillingConfigResponseDTO,
    BillingWebhookRequestDTO,
    BillingWebhookResponseDTO,
    CheckoutResponseDTO,
    CreateCheckoutRequestDTO,
    PaymentTransactionDTO,
)
from src.account.application.use_cases.billing import (
    BILLING_PLANS,
    CreateBillingCheckoutUseCase,
    ListBillingTransactionsUseCase,
    SettlePaymentTransactionUseCase,
)
from src.account.domain.exceptions.billing import (
    BillingUnavailableError,
    InvalidPaymentPlanError,
    InvalidWebhookPayloadError,
    PaymentTransactionNotFoundError,
)
from src.account.presentation.deps import (
    get_create_billing_checkout_use_case,
    get_current_learner_id,
    get_list_billing_transactions_use_case,
    get_settle_payment_transaction_use_case,
)
from src.shared_kernel.config import get_settings, resolve_billing_capabilities
from src.shared_kernel.infrastructure.security.rate_limiter import enforce_rate_limit

WEBHOOK_MAX_CLOCK_SKEW_SECONDS = 300

router = APIRouter(
    prefix="/api/v1/account/billing",
    tags=["Billing & Subscription (UC-04/05/27)"],
)


def _parse_webhook_timestamp(raw_timestamp: str | None) -> datetime | None:
    """Parse X-Webhook-Timestamp as Unix epoch seconds or timezone-aware ISO8601."""
    if not raw_timestamp:
        return None
    cleaned = raw_timestamp.strip()
    if not cleaned:
        return None

    # 1. Try Unix epoch seconds (int or float)
    try:
        epoch = float(cleaned)
    except ValueError:
        epoch = None

    if epoch is not None:
        if not math.isfinite(epoch):
            return None
        try:
            return datetime.fromtimestamp(epoch, tz=UTC)
        except (ValueError, OverflowError, OSError):
            return None

    # 2. Try timezone-aware ISO8601
    iso_candidate = f"{cleaned[:-1]}+00:00" if cleaned.endswith(("Z", "z")) else cleaned
    try:
        parsed = datetime.fromisoformat(iso_candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def _is_webhook_timestamp_fresh(parsed_ts: datetime, now: datetime | None = None) -> bool:
    """Return True iff parsed_ts is within ±WEBHOOK_MAX_CLOCK_SKEW_SECONDS of now."""
    effective_now = now or datetime.now(UTC)
    return abs((effective_now - parsed_ts).total_seconds()) <= WEBHOOK_MAX_CLOCK_SKEW_SECONDS


def _verify_webhook_hmac_signature(
    raw_body: bytes,
    raw_timestamp: str,
    provided_signature: str | None,
    webhook_secret: str,
) -> bool:
    """Verify HMAC-SHA256 over `f'{timestamp}.{raw_body}'` using dedicated payment_webhook_secret."""
    secret = webhook_secret.strip()
    if not secret or not provided_signature:
        return False
    cleaned_sig = provided_signature.strip()
    if cleaned_sig.lower().startswith("sha256="):
        cleaned_sig = cleaned_sig[7:].strip()
    if not cleaned_sig:
        return False

    signed_payload = f"{raw_timestamp.strip()}.".encode() + raw_body
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, cleaned_sig.lower())


@router.get(
    "/config",
    response_model=BillingConfigResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Get public server-owned billing release mode, capabilities, and plan catalog",
)
async def get_billing_config() -> BillingConfigResponseDTO:
    capabilities = resolve_billing_capabilities(get_settings())
    return BillingConfigResponseDTO(
        release_mode=capabilities.release_mode,
        checkout_enabled=capabilities.checkout_enabled,
        mock_confirm_enabled=capabilities.mock_confirm_enabled,
        provider=capabilities.provider,
        status_message=capabilities.status_message,
        plans=list(BILLING_PLANS),
    )


@router.post(
    "/checkout",
    response_model=CheckoutResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Create or reuse a PENDING subscription checkout session",
)
async def create_billing_checkout(
    request: CreateCheckoutRequestDTO,
    user_id: UUID = Depends(get_current_learner_id),
    use_case: CreateBillingCheckoutUseCase = Depends(get_create_billing_checkout_use_case),
) -> CheckoutResponseDTO:
    try:
        return await use_case.execute(user_id=user_id, request=request)
    except BillingUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=exc.message,
        ) from exc
    except InvalidPaymentPlanError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.message,
        ) from exc


@router.get(
    "/transactions",
    response_model=list[PaymentTransactionDTO],
    status_code=status.HTTP_200_OK,
    summary="List authenticated learner's billing transactions",
)
async def list_billing_transactions(
    user_id: UUID = Depends(get_current_learner_id),
    use_case: ListBillingTransactionsUseCase = Depends(get_list_billing_transactions_use_case),
) -> list[PaymentTransactionDTO]:
    return await use_case.execute(user_id=user_id)


@router.post(
    "/webhook",
    response_model=BillingWebhookResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Receive HMAC-SHA256 verified payment gateway webhook",
)
async def receive_billing_webhook(
    request: Request,
    use_case: SettlePaymentTransactionUseCase = Depends(get_settle_payment_transaction_use_case),
) -> BillingWebhookResponseDTO:
    await enforce_rate_limit(request, "billing_webhook_ip")
    webhook_secret = (get_settings().payment_webhook_secret or "").strip()
    if not webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment webhook signing secret is not configured",
        )

    raw_timestamp = request.headers.get("X-Webhook-Timestamp")
    parsed_timestamp = _parse_webhook_timestamp(raw_timestamp)
    if parsed_timestamp is None or raw_timestamp is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Webhook-Timestamp header",
        )
    if not _is_webhook_timestamp_fresh(parsed_timestamp):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Webhook timestamp outside allowed freshness window",
        )

    raw_body = await request.body()
    signature = request.headers.get("X-Webhook-Signature")
    if not _verify_webhook_hmac_signature(raw_body, raw_timestamp, signature, webhook_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing webhook signature",
        )

    try:
        parsed_json = json.loads(raw_body.decode("utf-8"))
        payload = BillingWebhookRequestDTO.model_validate(parsed_json)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook payload",
        ) from exc

    txn_ref = payload.transaction_ref or payload.provider_txn_id
    if payload.transaction_id is None and not txn_ref:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="transaction_id or provider_txn_id is required",
        )

    try:
        return await use_case.execute(
            transaction_id=payload.transaction_id,
            transaction_ref=txn_ref,
            event_type=payload.event_type,
            payment_status=payload.status,
            amount_vnd=payload.amount_vnd,
            currency=payload.currency,
            payload_user_id=payload.user_id,
            webhook_signature_verified=True,
        )
    except InvalidWebhookPayloadError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.message,
        ) from exc
    except PaymentTransactionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc


@router.post(
    "/mock-confirm/{transaction_id}",
    response_model=BillingWebhookResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Confirm a local_mock payment transaction in dev/test environments only",
)
async def mock_confirm_billing_transaction(
    transaction_id: UUID,
    user_id: UUID = Depends(get_current_learner_id),
    use_case: SettlePaymentTransactionUseCase = Depends(get_settle_payment_transaction_use_case),
) -> BillingWebhookResponseDTO:
    capabilities = resolve_billing_capabilities(get_settings())
    if not capabilities.mock_confirm_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Mock payment confirmation (local_mock) is forbidden in FREE_BETA, "
                "staging/production, and non-mock provider environments"
            ),
        )

    try:
        return await use_case.execute_mock_confirm(
            transaction_id=transaction_id,
            expected_user_id=user_id,
        )
    except InvalidWebhookPayloadError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.message,
        ) from exc
    except PaymentTransactionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
