import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Literal

from src.shared_kernel.application.llm_port import extract_upstream_model_from_response
from src.shared_kernel.domain.base import utc_now

__all__ = [
    "CostAccountingResult",
    "GEMINI_3_8_FLASH_STANDARD_SCHEDULE",
    "LEGACY_SCHEDULE",
    "ONE_MILLION_TOKENS",
    "PricingSchedule",
    "build_usage_log_metadata",
    "build_usage_log_metadata_dict",
    "calculate_cost_accounting",
    "calculate_estimated_cost_usd",
    "extract_upstream_model_from_response",
    "get_pricing_schedule",
    "parse_usage_log_metadata",
    "resolve_canonical_gateway_model",
    "summarize_cost_accounting_logs",
]

_MODEL_SUFFIXES: tuple[str, ...] = (
    "-low",
    "-medium",
    "-high",
    "-thinking",
    "-preview",
    "-latest",
)

ONE_MILLION_TOKENS: Decimal = Decimal("1000000")


def resolve_canonical_gateway_model(model_name: str | None) -> str:
    """Resolve a raw or suffixed gateway model name into its canonical identifier.

    Strips provider prefixes (e.g., 'models/') and suffixes like
    -low, -medium, -high, -thinking, -preview, -latest.
    Maps gemini-3.8-flash-low, gemini-3.8-flash-medium, gemini-3.8-flash-high to gemini-3.8-flash.
    """
    if not model_name:
        return "gemini-3.8-flash"

    cleaned = model_name.strip().lower()
    if not cleaned:
        return "gemini-3.8-flash"

    if cleaned.startswith("models/"):
        cleaned = cleaned[len("models/") :]

    changed = True
    while changed:
        changed = False
        for suffix in _MODEL_SUFFIXES:
            if cleaned.endswith(suffix):
                cleaned = cleaned[: -len(suffix)]
                changed = True
                break

    return cleaned or "gemini-3.8-flash"


@dataclass(frozen=True)
class PricingSchedule:
    """Pricing schedule descriptor for model token consumption."""

    version: str
    effective_start_date: date
    effective_end_date: date
    input_price_per_million: Decimal
    output_price_per_million: Decimal
    gateway_cost_status: Literal["VERIFIED", "UNVERIFIED"] = "UNVERIFIED"
    verification_notes: str = ""


# Pricing Schedule Registry
LEGACY_SCHEDULE = PricingSchedule(
    version="2025-LEGACY",
    effective_start_date=date(2025, 1, 1),
    effective_end_date=date(2025, 12, 31),
    input_price_per_million=Decimal("0.075"),
    output_price_per_million=Decimal("0.300"),
    gateway_cost_status="UNVERIFIED",
    verification_notes="Legacy reference schedule (effective through 2025-12-31).",
)

GEMINI_3_8_FLASH_STANDARD_SCHEDULE = PricingSchedule(
    version="2026-Q1-STANDARD",
    effective_start_date=date(2026, 1, 1),
    effective_end_date=date(2026, 12, 31),
    input_price_per_million=Decimal("0.75"),
    output_price_per_million=Decimal("3.75"),
    gateway_cost_status="UNVERIFIED",
    verification_notes="CofHub does not expose automated verified pricing; provider list rates applied.",
)

_LEGACY_MODELS: frozenset[str] = frozenset(
    {
        "gemini-2.5-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-2.0-flash",
    }
)


def get_pricing_schedule(canonical_model: str, as_of_date: date) -> PricingSchedule:
    """Resolve active pricing schedule based on model and effective date."""
    # Legacy schedule fallback when as_of_date <= 2025-12-31 or model is legacy
    if (
        as_of_date <= date(2025, 12, 31)
        or canonical_model in _LEGACY_MODELS
        or canonical_model.startswith(("gemini-2.5", "gemini-1.5"))
    ):
        return LEGACY_SCHEDULE

    if canonical_model == "gemini-3.8-flash" or canonical_model.startswith("gemini-3.8"):
        return GEMINI_3_8_FLASH_STANDARD_SCHEDULE

    return GEMINI_3_8_FLASH_STANDARD_SCHEDULE


@dataclass(frozen=True)
class CostAccountingResult:
    """Audit result for AI cost accounting."""

    model_name: str
    canonical_model: str
    pricing_version: str
    effective_date: date
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_provider_cost_usd: Decimal
    actual_gateway_cost_usd: Decimal | None
    gateway_cost_status: Literal["VERIFIED", "UNVERIFIED"]
    verification_notes: str
    thinking_tokens: int = 0
    resolved_model: str | None = None
    usage_completeness: Literal["COMPLETE", "PARTIAL", "UNKNOWN"] = "COMPLETE"
    usage_source: Literal["GATEWAY_TELEMETRY", "CACHE", "ESTIMATED", "UNKNOWN"] = (
        "GATEWAY_TELEMETRY"
    )


def calculate_cost_accounting(
    prompt_tokens: int,
    completion_tokens: int,
    model_name: str = "gemini-3.8-flash",
    as_of_date: date | None = None,
    thinking_tokens: int = 0,
    resolved_model: str | None = None,
    usage_completeness: Literal["COMPLETE", "PARTIAL", "UNKNOWN"] = "COMPLETE",
    usage_source: Literal["GATEWAY_TELEMETRY", "CACHE", "ESTIMATED", "UNKNOWN"] = (
        "GATEWAY_TELEMETRY"
    ),
) -> CostAccountingResult:
    """Calculate detailed AI cost accounting result for given tokens and model.

    Ensures thinking tokens are included exactly once according to provider semantics.
    If usage_completeness is UNKNOWN, estimated cost is $0.00 but marked UNKNOWN so it is
    never misrepresented as free/zero compute.
    """
    raw_model = (model_name or "gemini-3.8-flash").strip()
    effective_model = resolved_model if resolved_model else raw_model
    canonical = resolve_canonical_gateway_model(effective_model)
    target_date = as_of_date if as_of_date is not None else utc_now().date()

    schedule = get_pricing_schedule(canonical, target_date)

    p_tok = max(0, int(prompt_tokens))
    c_tok = max(0, int(completion_tokens))
    t_tok = max(0, int(thinking_tokens))
    tot_tok = p_tok + c_tok

    if usage_completeness == "UNKNOWN":
        estimated_cost = Decimal("0.000000")
        notes = "MISSING_TELEMETRY: Telemetry was not returned (e.g. timeout before headers)."
    elif usage_source == "CACHE":
        estimated_cost = Decimal("0.000000")
        notes = "CACHED_CHECKPOINT: Sourced from deterministic checkpoint; 0 provider cost."
    else:
        # Provider semantics: output price applies to billable completion tokens (including thinking)
        estimated_cost = (
            Decimal(p_tok) * schedule.input_price_per_million
            + Decimal(c_tok) * schedule.output_price_per_million
        ) / ONE_MILLION_TOKENS
        notes = schedule.verification_notes

    return CostAccountingResult(
        model_name=raw_model,
        canonical_model=canonical,
        pricing_version=schedule.version,
        effective_date=target_date,
        prompt_tokens=p_tok,
        completion_tokens=c_tok,
        total_tokens=tot_tok,
        estimated_provider_cost_usd=estimated_cost,
        actual_gateway_cost_usd=None,
        gateway_cost_status=schedule.gateway_cost_status,
        verification_notes=notes,
        thinking_tokens=t_tok,
        resolved_model=resolved_model,
        usage_completeness=usage_completeness,
        usage_source=usage_source,
    )


def calculate_estimated_cost_usd(
    prompt_tokens: int,
    completion_tokens: int,
    model_name: str = "gemini-3.8-flash",
    as_of_date: date | None = None,
    thinking_tokens: int = 0,
    resolved_model: str | None = None,
) -> Decimal:
    """Calculate token cost in USD for the resolved canonical model and schedule."""
    result = calculate_cost_accounting(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        model_name=model_name,
        as_of_date=as_of_date,
        thinking_tokens=thinking_tokens,
        resolved_model=resolved_model,
    )
    return result.estimated_provider_cost_usd


def build_usage_log_metadata_dict(
    *,
    requested_model: str,
    resolved_model: str | None = None,
    pricing_version: str = "2026-Q1-STANDARD",
    usage_source: str = "GATEWAY_TELEMETRY",
    usage_completeness: str = "COMPLETE",
    cost_verification_status: str = "UNVERIFIED",
    thinking_tokens: int = 0,
    attempt_no: int = 1,
    idempotency_key: str | None = None,
    reservation_id: str | None = None,
    error_detail: str | None = None,
) -> dict[str, Any]:
    """Build structured usage and accounting audit metadata dictionary for JSONB storage."""
    payload: dict[str, Any] = {
        "requested_model": requested_model,
        "resolved_model": resolved_model,
        "pricing_version": pricing_version,
        "usage_source": usage_source,
        "usage_completeness": usage_completeness,
        "cost_verification_status": cost_verification_status,
        "thinking_tokens": thinking_tokens,
        "attempt_no": attempt_no,
        "idempotency_key": idempotency_key,
        "reservation_id": reservation_id,
    }
    if error_detail:
        payload["error"] = error_detail
    return payload


def build_usage_log_metadata(
    *,
    requested_model: str,
    resolved_model: str | None = None,
    pricing_version: str = "2026-Q1-STANDARD",
    usage_source: str = "GATEWAY_TELEMETRY",
    usage_completeness: str = "COMPLETE",
    cost_verification_status: str = "UNVERIFIED",
    thinking_tokens: int = 0,
    attempt_no: int = 1,
    idempotency_key: str | None = None,
    reservation_id: str | None = None,
    error_detail: str | None = None,
) -> str:
    """Serialize structured usage and accounting audit metadata for backward-compatible text storage."""
    payload = build_usage_log_metadata_dict(
        requested_model=requested_model,
        resolved_model=resolved_model,
        pricing_version=pricing_version,
        usage_source=usage_source,
        usage_completeness=usage_completeness,
        cost_verification_status=cost_verification_status,
        thinking_tokens=thinking_tokens,
        attempt_no=attempt_no,
        idempotency_key=idempotency_key,
        reservation_id=reservation_id,
        error_detail=error_detail,
    )
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def parse_usage_log_metadata(raw_value: dict[str, Any] | str | None) -> dict[str, Any]:
    """Parse structured usage metadata from JSONB audit_metadata or legacy error_message text."""
    if raw_value is None:
        return {}
    if isinstance(raw_value, dict):
        return dict(raw_value)
    cleaned = raw_value.strip()
    if cleaned.startswith("{") and cleaned.endswith("}"):
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return {"error": cleaned}


@dataclass(frozen=True)
class CostSummaryReport:
    """Aggregated cost & telemetry completeness report across AI usage records."""

    total_attempts: int
    complete_attempts: int
    partial_attempts: int
    unknown_usage_attempts: int
    cached_attempts: int
    observed_prompt_tokens: int
    observed_completion_tokens: int
    observed_thinking_tokens: int
    observed_total_tokens: int
    observed_estimated_provider_cost_usd: Decimal
    actual_gateway_cost_usd: Decimal | None
    gateway_cost_status: Literal["VERIFIED", "UNVERIFIED"]
    cost_completeness_status: Literal["COMPLETE", "INCOMPLETE_LOWER_BOUND"]
    cost_per_successful_run_usd: Decimal | None = None
    successful_runs_count: int = 0


def summarize_cost_accounting_logs(
    records: Sequence[Any],
    *,
    successful_runs_count: int = 0,
) -> CostSummaryReport:
    """Aggregate usage logs without ever conflating UNKNOWN telemetry with $0 compute.

    Reads `audit_metadata` (dict) or falls back to `error_message` metadata on ORM/DTO records.
    Records marked `usage_completeness == 'UNKNOWN'` are excluded from complete-telemetry counts,
    increment `unknown_usage_attempts`, and force `cost_completeness_status = 'INCOMPLETE_LOWER_BOUND'`.
    """
    total_attempts = 0
    complete_attempts = 0
    partial_attempts = 0
    unknown_attempts = 0
    cached_attempts = 0
    obs_prompt = 0
    obs_completion = 0
    obs_thinking = 0
    obs_cost = Decimal("0")

    for rec in records:
        total_attempts += 1
        raw_meta = (
            rec.get("audit_metadata")
            if isinstance(rec, dict)
            else getattr(rec, "audit_metadata", None)
        )
        raw_err = (
            rec.get("error_message")
            if isinstance(rec, dict)
            else getattr(rec, "error_message", None)
        )
        meta = parse_usage_log_metadata(raw_meta if raw_meta is not None else raw_err)

        status_val = str(
            rec.get("status") if isinstance(rec, dict) else getattr(rec, "status", "SUCCESS")
        ).upper()
        p_tok = int(
            (
                rec.get("prompt_tokens")
                if isinstance(rec, dict)
                else getattr(rec, "prompt_tokens", 0)
            )
            or 0
        )
        c_tok = int(
            (
                rec.get("completion_tokens")
                if isinstance(rec, dict)
                else getattr(rec, "completion_tokens", 0)
            )
            or 0
        )
        t_tok = int(meta.get("thinking_tokens", 0) or 0)
        usage_source = str(meta.get("usage_source") or "GATEWAY_TELEMETRY").upper()
        default_completeness = (
            "UNKNOWN"
            if (
                status_val in ("TIMEOUT", "FAILED")
                and p_tok == 0
                and c_tok == 0
                and usage_source != "CACHE"
            )
            else "COMPLETE"
        )
        completeness = str(meta.get("usage_completeness") or default_completeness).upper()

        if usage_source == "CACHE":
            cached_attempts += 1
        if completeness == "UNKNOWN":
            unknown_attempts += 1
            continue
        if completeness == "PARTIAL":
            partial_attempts += 1
        else:
            complete_attempts += 1

        obs_prompt += max(0, p_tok)
        obs_completion += max(0, c_tok)
        obs_thinking += max(0, t_tok)

        raw_cost = (
            rec.get("estimated_cost_usd")
            if isinstance(rec, dict)
            else getattr(rec, "estimated_cost_usd", None)
        )
        if raw_cost is not None:
            obs_cost += Decimal(str(raw_cost))
        else:
            obs_cost += calculate_estimated_cost_usd(
                prompt_tokens=p_tok,
                completion_tokens=c_tok,
                model_name=str(
                    rec.get("model_name")
                    if isinstance(rec, dict)
                    else getattr(rec, "model_name", "gemini-3.8-flash")
                ),
                resolved_model=meta.get("resolved_model"),
            )

    completeness_status: Literal["COMPLETE", "INCOMPLETE_LOWER_BOUND"] = (
        "INCOMPLETE_LOWER_BOUND" if unknown_attempts > 0 else "COMPLETE"
    )
    per_success: Decimal | None = None
    if successful_runs_count > 0:
        per_success = (obs_cost / Decimal(successful_runs_count)).quantize(Decimal("0.000001"))

    return CostSummaryReport(
        total_attempts=total_attempts,
        complete_attempts=complete_attempts,
        partial_attempts=partial_attempts,
        unknown_usage_attempts=unknown_attempts,
        cached_attempts=cached_attempts,
        observed_prompt_tokens=obs_prompt,
        observed_completion_tokens=obs_completion,
        observed_thinking_tokens=obs_thinking,
        observed_total_tokens=obs_prompt + obs_completion,
        observed_estimated_provider_cost_usd=obs_cost.quantize(Decimal("0.000001")),
        actual_gateway_cost_usd=None,
        gateway_cost_status="UNVERIFIED",
        cost_completeness_status=completeness_status,
        cost_per_successful_run_usd=per_success,
        successful_runs_count=successful_runs_count,
    )
