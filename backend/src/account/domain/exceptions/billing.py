from src.shared_kernel.domain.exceptions import DomainError


class BillingUnavailableError(DomainError):
    """Raised when payment gateway is unavailable or unconfigured (fail-closed -> HTTP 503)."""

    def __init__(
        self, message: str = "Cổng thanh toán hiện chưa sẵn sàng trong môi trường này."
    ) -> None:
        super().__init__(message=message, code="BILLING_UNAVAILABLE")


class BillingForbiddenError(DomainError):
    """Raised when a dev/mock billing operation is attempted outside dev/test environments."""

    def __init__(
        self, message: str = "Thao tác xác nhận thanh toán giả lập không được phép."
    ) -> None:
        super().__init__(message=message, code="BILLING_FORBIDDEN")


class PaymentTransactionNotFoundError(DomainError):
    """Raised when a payment transaction cannot be found or does not belong to the user."""

    def __init__(self, message: str = "Không tìm thấy giao dịch thanh toán.") -> None:
        super().__init__(message=message, code="PAYMENT_TRANSACTION_NOT_FOUND")


class InvalidPaymentPlanError(DomainError):
    """Raised when an unknown subscription plan_code is requested."""

    def __init__(self, message: str = "Gói đăng ký không hợp lệ.") -> None:
        super().__init__(message=message, code="INVALID_PAYMENT_PLAN")


class InvalidWebhookPayloadError(DomainError):
    """Raised when a signed billing webhook fails business event, amount, currency, or ownership validation."""

    def __init__(self, message: str = "Payload webhook thanh toán không hợp lệ.") -> None:
        super().__init__(message=message, code="INVALID_WEBHOOK_PAYLOAD")
