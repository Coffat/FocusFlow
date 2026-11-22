import urllib.parse
from uuid import UUID

from src.account.application.ports.payment_ports import (
    PaymentCheckoutPayloadDTO,
    PaymentProviderPort,
)
from src.account.domain.exceptions.billing import BillingUnavailableError
from src.shared_kernel.config import Settings, resolve_billing_capabilities


def is_local_mock_billing_allowed(settings: Settings) -> bool:
    """Return True ONLY when PAID_ENABLED + local_mock inside dev/test/local environments."""
    capabilities = resolve_billing_capabilities(settings)
    return capabilities.mock_confirm_enabled and capabilities.provider == "local_mock"


class LocalMockPaymentAdapter(PaymentProviderPort):
    """Fail-closed PaymentProviderPort adapter for FocusFlow billing readiness (FE-API-05).

    Mock vs. Live Boundary:
    - In FREE_BETA: fails closed across all environments with `BillingUnavailableError` (HTTP 503).
    - In PAID_ENABLED + dev/test/local with `PAYMENT_PROVIDER=local_mock`: returns deterministic
      VietQR/checkout URL pointing to `{frontend_base}/pricing?mock_tx={transaction_id}`.
    - In staging/production, or when an unimplemented live provider (e.g., `sepay`, `payos`,
      `vnpay`) is selected: fails closed with `BillingUnavailableError` (HTTP 503).
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create_checkout(
        self,
        *,
        transaction_id: UUID,
        transaction_ref: str,
        plan_code: str,
        amount_vnd: int,
    ) -> PaymentCheckoutPayloadDTO:
        capabilities = resolve_billing_capabilities(self._settings)
        if not (capabilities.checkout_enabled and capabilities.provider == "local_mock"):
            raise BillingUnavailableError(
                capabilities.unavailable_reason
                or "Cổng thanh toán hiện chưa sẵn sàng trong môi trường này."
            )

        frontend_base = (self._settings.frontend_url or "http://localhost:3000").rstrip("/")
        safe_ref = urllib.parse.quote(transaction_ref)
        checkout_url = f"{frontend_base}/pricing?mock_tx={transaction_id}"
        qr_code_url = (
            f"https://img.vietqr.io/image/970422-FOCUSFLOWMOCK-compact2.png"
            f"?amount={amount_vnd}&addInfo={safe_ref}"
        )
        return PaymentCheckoutPayloadDTO(
            provider="MOCK",
            checkout_url=checkout_url,
            qr_code_url=qr_code_url,
            is_mock_provider=True,
        )
