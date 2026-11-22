from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

PlanCode = Literal["PREMIUM_MONTHLY", "PREMIUM_YEARLY"]
BillingReleaseMode = Literal["FREE_BETA", "PAID_ENABLED"]


class BillingPlanDTO(BaseModel):
    """Server-owned subscription plan pricing and entitlement catalog."""

    plan_code: PlanCode
    name: str
    amount_vnd: int
    currency: str
    billing_cycle: Literal["MONTHLY", "YEARLY"]
    ai_monthly_limit: int
    max_active_roadmaps: int


class BillingConfigResponseDTO(BaseModel):
    """Public server-owned billing release mode and capability response."""

    release_mode: BillingReleaseMode
    checkout_enabled: bool
    mock_confirm_enabled: bool
    provider: str
    status_message: str
    plans: list[BillingPlanDTO]


class CreateCheckoutRequestDTO(BaseModel):
    """Request payload to initiate a subscription checkout session."""

    plan_code: PlanCode


class CheckoutResponseDTO(BaseModel):
    """Response returned when initiating or reusing an active PENDING checkout."""

    transaction_id: UUID
    transaction_ref: str
    plan_code: str
    amount_vnd: int
    status: str
    provider: str
    checkout_url: str
    qr_code_url: str
    expires_at: datetime
    is_mock_provider: bool


class PaymentTransactionDTO(BaseModel):
    """Historical or pending payment transaction item for the authenticated learner."""

    id: UUID
    transaction_ref: str
    plan_code: str
    amount_vnd: int
    currency: str
    status: str
    provider: str
    qr_code_url: str | None = None
    webhook_signature_verified: bool
    paid_at: datetime | None = None
    created_at: datetime


class BillingWebhookRequestDTO(BaseModel):
    """Incoming payment gateway webhook payload (verified via X-Webhook-Signature + X-Webhook-Timestamp)."""

    event_id: str | None = None
    event_type: str
    transaction_id: UUID | None = None
    provider_txn_id: str | None = None
    transaction_ref: str | None = None
    status: str
    amount_vnd: int
    currency: str
    user_id: UUID | None = None


class BillingWebhookResponseDTO(BaseModel):
    """Idempotent webhook settlement acknowledgement."""

    status: str
    transaction_id: UUID
    already_processed: bool
