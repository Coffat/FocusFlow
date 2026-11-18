from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from uuid6 import uuid7

from src.account.domain.services.ai_cost_accounting_service import (
    extract_upstream_model_from_response,
    parse_usage_log_metadata,
)
from src.account.infrastructure.adapters.quota_facade_adapter import QuotaFacadeAdapter
from src.account.infrastructure.orm.user_orm import (
    AIQuotaORM,
    AIQuotaReservationORM,
    AIUsageLogORM,
)
from src.shared_kernel.application.harness.execution_manager import (
    AIExecutionManager,
)
from src.shared_kernel.application.llm_port import (
    LLMGenerationResult,
    LLMProviderPort,
    SchemaMismatchError,
)


class MockDbQueryResult:
    def __init__(self, item: Any) -> None:
        self._item = item

    def scalar_one_or_none(self) -> Any | None:
        return self._item

    def scalar_one(self) -> Any:
        return self._item


class MockQuotaAsyncSession:
    def __init__(
        self, reservation: AIQuotaReservationORM | None = None, quota: AIQuotaORM | None = None
    ) -> None:
        self.reservation = reservation
        self.quota = quota
        self.added: list[Any] = []

    def add(self, item: Any) -> None:
        self.added.append(item)

    async def flush(self) -> None:
        pass

    async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> MockDbQueryResult:
        stmt_str = str(stmt).upper()
        if "AI_QUOTA_RESERVATIONS" in stmt_str and self.reservation is not None:
            return MockDbQueryResult(self.reservation)
        if "AI_QUOTAS" in stmt_str and self.quota is not None:
            return MockDbQueryResult(self.quota)
        return MockDbQueryResult(None)


# ---------------------------------------------------------------------------
# 1. TIMEOUT WITHOUT USAGE MARKED UNKNOWN (DEF-17 Issue 1)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_timeout_without_usage_marked_unknown() -> None:
    """Verify socket timeout without token telemetry is recorded as UNKNOWN, not zero cost."""
    user_id = uuid7()
    session = MockQuotaAsyncSession()
    adapter = QuotaFacadeAdapter(session=session)  # type: ignore[arg-type]

    # Provider times out before receiving headers
    mock_provider = MagicMock(spec=LLMProviderPort)

    async def _timeout_gen(**kwargs: Any) -> None:
        raise TimeoutError("Socket timeout before headers received")

    mock_provider.generate_structured = AsyncMock(side_effect=_timeout_gen)

    manager = AIExecutionManager(
        provider=mock_provider,
        quota=adapter,
        timeout_seconds=0.05,
        max_retries=0,
    )

    with pytest.raises(TimeoutError):
        await manager.execute(
            user_id=user_id,
            operation_type="TASK_DECOMPOSITION",
            system_prompt="sys",
            user_prompt="user",
            response_schema={"type": "object"},
            thinking_level="HIGH",
            step_name="TASK_DECOMPOSER_M1",
        )

    usage_logs = [item for item in session.added if isinstance(item, AIUsageLogORM)]
    assert len(usage_logs) == 1
    log = usage_logs[0]

    assert log.status == "TIMEOUT"
    assert log.prompt_tokens == 0
    assert log.completion_tokens == 0
    assert log.total_tokens == 0
    assert log.estimated_cost_usd == Decimal("0.000000")

    assert isinstance(log.audit_metadata, dict)
    meta = parse_usage_log_metadata(log.audit_metadata or log.error_message)
    assert meta["usage_completeness"] == "UNKNOWN"
    assert meta["usage_source"] == "UNKNOWN"
    assert meta["cost_verification_status"] == "UNVERIFIED"
    assert "TimeoutError" in str(log.error_code)


# ---------------------------------------------------------------------------
# 2. PARTIAL USAGE RECORDED INDEPENDENTLY OF QUOTA SETTLEMENT (DEF-17 Issue 2 & 3)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_partial_usage_recorded_independently_of_quota_settlement() -> None:
    """Verify failed attempt with partial tokens is persisted into ai_usage_logs even when quota is released."""
    user_id = uuid7()
    quota_id = uuid7()
    res_id = uuid7()

    quota = AIQuotaORM(
        id=quota_id,
        user_id=user_id,
        free_credits_remaining=3,
        paid_credits_remaining=0,
        reserved_calls=1,
        used_calls=0,
        tokens_consumed=0,
    )
    reservation = AIQuotaReservationORM(
        id=res_id,
        quota_id=quota_id,
        user_id=user_id,
        operation_type="ROADMAP_GEN",
        status="RESERVED",
        tokens_reserved=1,
    )

    session = MockQuotaAsyncSession(reservation=reservation, quota=quota)
    adapter = QuotaFacadeAdapter(session=session)  # type: ignore[arg-type]

    # Provider generates tokens but fails schema validation
    mock_provider = MagicMock(spec=LLMProviderPort)

    async def _schema_fail(**kwargs: Any) -> None:
        raise SchemaMismatchError(
            "Schema mismatch: missing field 'required_tasks'",
            prompt_tokens=3200,
            output_tokens=850,
            thinking_tokens=150,
            model_id="gemini-3.8-flash",
        )

    mock_provider.generate_structured = AsyncMock(side_effect=_schema_fail)

    manager = AIExecutionManager(
        provider=mock_provider,
        quota=adapter,
        timeout_seconds=0.1,
        max_retries=0,
    )

    with pytest.raises(SchemaMismatchError):
        await manager.execute(
            user_id=user_id,
            operation_type="ROADMAP_GENERATION",
            system_prompt="sys",
            user_prompt="user",
            response_schema={"type": "object"},
            thinking_level="HIGH",
            existing_reservation_id=res_id,
            release_on_failure=True,
        )

    # 1. User quota reservation was RELEASED (refunded)
    assert reservation.status == "RELEASED"

    # 2. But provider usage WAS RECORDED in ai_usage_logs
    usage_logs = [item for item in session.added if isinstance(item, AIUsageLogORM)]
    assert len(usage_logs) >= 1
    log = usage_logs[-1]
    assert log.status == "FAILED"
    assert log.prompt_tokens == 3200
    assert log.completion_tokens == 850
    assert log.total_tokens == 4050

    # Expected: (3200 * 0.75 + 850 * 3.75) / 1,000,000 = (2400 + 3187.5) / 1,000,000 = 0.0055875 USD
    assert log.estimated_cost_usd == Decimal("0.0055875")

    assert isinstance(log.audit_metadata, dict)
    meta = parse_usage_log_metadata(log.audit_metadata or log.error_message)
    assert meta["usage_completeness"] == "PARTIAL"
    assert meta["usage_source"] == "GATEWAY_TELEMETRY"
    assert meta["thinking_tokens"] == 150


# ---------------------------------------------------------------------------
# 3. SUCCESSFUL REQUEST WITH EXACT THINKING TOKENS INCLUDED ONCE (DEF-17 Issue 6)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_successful_request_with_exact_thinking_tokens_included_once() -> None:
    """Verify thinking tokens are counted as billable completion tokens exactly once."""
    user_id = uuid7()
    session = MockQuotaAsyncSession()
    adapter = QuotaFacadeAdapter(session=session)  # type: ignore[arg-type]

    # Response with 500 prompt tokens, 200 candidates tokens, 300 thinking tokens -> 500 total completion tokens
    mock_provider = MagicMock(spec=LLMProviderPort)
    mock_provider.generate_structured = AsyncMock(
        return_value=LLMGenerationResult(
            payload={"status": "success"},
            prompt_tokens=500,
            output_tokens=500,  # includes candidates (200) + thinking (300)
            thinking_tokens=300,
            model_id="gemini-3.8-flash",
        )
    )

    manager = AIExecutionManager(
        provider=mock_provider,
        quota=adapter,
        timeout_seconds=5.0,
        max_retries=0,
        manage_quota=False,
    )

    res = await manager.execute(
        user_id=user_id,
        operation_type="SCHEDULE_PROPOSAL",
        system_prompt="sys",
        user_prompt="user",
        response_schema={"type": "object"},
        thinking_level="HIGH",
        step_name="SCHEDULE_OPTIMIZER",
    )

    assert res.value == {"status": "success"}

    usage_logs = [item for item in session.added if isinstance(item, AIUsageLogORM)]
    assert len(usage_logs) == 1
    log = usage_logs[0]

    assert log.status == "SUCCESS"
    assert log.prompt_tokens == 500
    assert log.completion_tokens == 500
    assert log.total_tokens == 1000

    # Billable output tokens = 500 (thinking tokens included once at output price $3.75/M)
    # (500 * 0.75 + 500 * 3.75) / 1,000,000 = (375 + 1875) / 1,000,000 = 2250 / 1,000,000 = 0.002250 USD
    assert log.estimated_cost_usd == Decimal("0.002250")

    assert isinstance(log.audit_metadata, dict)
    meta = parse_usage_log_metadata(log.audit_metadata or log.error_message)
    assert meta["usage_completeness"] == "COMPLETE"
    assert meta["thinking_tokens"] == 300
    assert meta["pricing_version"] == "2026-Q1-STANDARD"


# ---------------------------------------------------------------------------
# 4. CONCURRENT RETRIES AND PER-ATTEMPT LOGGING (DEF-17 Issue 3)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_concurrent_retries_and_per_attempt_logging() -> None:
    """Verify attempt 1 failure and attempt 2 success are each recorded with distinct attempt numbers."""
    user_id = uuid7()
    session = MockQuotaAsyncSession()
    adapter = QuotaFacadeAdapter(session=session)  # type: ignore[arg-type]

    call_count = 0
    mock_provider = MagicMock(spec=LLMProviderPort)

    async def _flaky_gen(**kwargs: Any) -> LLMGenerationResult:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("500 INTERNAL: stream interrupted")
        return LLMGenerationResult(
            payload={"ok": True},
            prompt_tokens=1050,
            output_tokens=400,
            thinking_tokens=100,
            model_id="gemini-3.8-flash",
        )

    mock_provider.generate_structured = AsyncMock(side_effect=_flaky_gen)

    manager = AIExecutionManager(
        provider=mock_provider,
        quota=adapter,
        timeout_seconds=5.0,
        max_retries=1,
        manage_quota=False,
    )

    result = await manager.execute(
        user_id=user_id,
        operation_type="ROADMAP_GENERATION",
        system_prompt="sys",
        user_prompt="user",
        response_schema={"type": "object"},
        thinking_level="MEDIUM",
        step_name="RETRY_STAGE",
    )

    assert result.value == {"ok": True}

    usage_logs = [item for item in session.added if isinstance(item, AIUsageLogORM)]
    # Both attempt 1 (failed) and attempt 2 (success) must be in the ledger
    assert len(usage_logs) == 2

    # Attempt 1: Failed
    log1 = usage_logs[0]
    assert log1.status == "FAILED"
    assert isinstance(log1.audit_metadata, dict)
    meta1 = parse_usage_log_metadata(log1.audit_metadata or log1.error_message)
    assert meta1["attempt_no"] == 1
    assert meta1["usage_completeness"] == "UNKNOWN"

    # Attempt 2: Success
    log2 = usage_logs[1]
    assert log2.status == "SUCCESS"
    assert isinstance(log2.audit_metadata, dict)
    meta2 = parse_usage_log_metadata(log2.audit_metadata or log2.error_message)
    assert meta2["attempt_no"] == 2
    assert meta2["usage_completeness"] == "COMPLETE"


# ---------------------------------------------------------------------------
# 5. DUPLICATE REQUEST IDS & IDEMPOTENCY (DEF-17 Issue 3)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_duplicate_request_idempotency() -> None:
    """Verify duplicate usage logging calls with same idempotency key do not create duplicate rows."""
    user_id = uuid7()
    session = MockQuotaAsyncSession()
    adapter = QuotaFacadeAdapter(session=session)  # type: ignore[arg-type]

    idempotency_key = f"res-test-idempotency:{uuid7()}:attempt-1"

    # Call 1
    log1 = await adapter.record_attempt_usage(
        user_id=user_id,
        action_type="ROADMAP_GENERATION",
        requested_model="gemini-3.8-flash",
        prompt_tokens=1000,
        completion_tokens=500,
        status="SUCCESS",
        idempotency_key=idempotency_key,
    )
    assert log1 is not None

    # Call 2 with identical idempotency_key
    log2 = await adapter.record_attempt_usage(
        user_id=user_id,
        action_type="ROADMAP_GENERATION",
        requested_model="gemini-3.8-flash",
        prompt_tokens=1000,
        completion_tokens=500,
        status="SUCCESS",
        idempotency_key=idempotency_key,
    )
    # Deduplicated, returns None
    assert log2 is None

    usage_logs = [item for item in session.added if isinstance(item, AIUsageLogORM)]
    assert len(usage_logs) == 1


# ---------------------------------------------------------------------------
# 6. RESUMED CHECKPOINTS RECORD ZERO COST WITH CACHED SOURCE (DEF-17 Issue 3)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_resumed_checkpoint_records_zero_cost_with_cached_source() -> None:
    """Verify cached checkpoint entry records 0 tokens, $0.00 cost, and usage_source=CACHE."""
    user_id = uuid7()
    session = MockQuotaAsyncSession()
    adapter = QuotaFacadeAdapter(session=session)  # type: ignore[arg-type]

    log = await adapter.record_attempt_usage(
        user_id=user_id,
        action_type="MILESTONE_BREAKDOWN",
        requested_model="gemini-3.8-flash",
        prompt_tokens=0,
        completion_tokens=0,
        thinking_tokens=0,
        status="SUCCESS",
        usage_completeness="COMPLETE",
        usage_source="CACHE",
        idempotency_key="checkpoint:sha256-hash-m1",
    )
    assert log is not None
    assert log.prompt_tokens == 0
    assert log.completion_tokens == 0
    assert log.total_tokens == 0
    assert log.estimated_cost_usd == Decimal("0.000000")

    assert isinstance(log.audit_metadata, dict)
    meta = parse_usage_log_metadata(log.audit_metadata or log.error_message)
    assert meta["usage_source"] == "CACHE"
    assert meta["usage_completeness"] == "COMPLETE"
    assert meta["cost_verification_status"] == "UNVERIFIED"


# ---------------------------------------------------------------------------
# 7. RESOLVED MODEL FROM GATEWAY HEADERS VS ALIAS SUFFIX (DEF-17 Issue 4)
# ---------------------------------------------------------------------------
def test_resolved_model_from_gateway_headers_vs_alias_suffix() -> None:
    """Verify upstream model is resolved from x-upstream-model header rather than stripping alias."""

    # Case A: Live CofHub proxy response with headers
    class MockSdkHttpResponse:
        def __init__(self, headers: dict[str, str]) -> None:
            self.headers = headers

    class MockCofHubResponse:
        def __init__(self, headers: dict[str, str], model_version: str | None = None) -> None:
            self.sdk_http_response = MockSdkHttpResponse(headers)
            self.model_version = model_version

    resp_cofhub = MockCofHubResponse(
        headers={
            "x-mapped-model": "gemini-3.8-flash-high",
            "x-upstream-model": "gemini-3.8-flash-high",
        }
    )

    verified, effective = extract_upstream_model_from_response(
        resp_cofhub, default_model="gemini-3.8-flash"
    )
    assert verified == "gemini-3.8-flash-high"
    assert effective == "gemini-3.8-flash-high"

    # Case B: Response without CofHub headers fallback to model_version
    resp_direct = MockCofHubResponse(headers={}, model_version="gemini-3.8-flash-001")
    verified_dir, effective_dir = extract_upstream_model_from_response(
        resp_direct, default_model="gemini-3.8-flash"
    )
    assert verified_dir == "gemini-3.8-flash-001"
    assert effective_dir == "gemini-3.8-flash-001"

    # Case C: No response / None headers
    verified_none, effective_none = extract_upstream_model_from_response(
        None, default_model="gemini-3.8-flash"
    )
    assert verified_none is None
    assert effective_none == "gemini-3.8-flash"


# ---------------------------------------------------------------------------
# 8. CRITICS AND JUDGE USAGE RECORDED WITH MANAGE_QUOTA=FALSE (DEF-17 Issue 2 & 3)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_critics_and_judge_usage_recorded_with_manage_quota_false() -> None:
    """Verify system quality gates (manage_quota=False) still write provider token usage to ai_usage_logs."""
    user_id = uuid7()
    session = MockQuotaAsyncSession()
    adapter = QuotaFacadeAdapter(session=session)  # type: ignore[arg-type]

    mock_provider = MagicMock(spec=LLMProviderPort)
    mock_provider.generate_structured = AsyncMock(
        return_value=LLMGenerationResult(
            payload={"status": "PASSED", "score": 90},
            prompt_tokens=1500,
            output_tokens=300,
            thinking_tokens=100,
            model_id="gemini-3.8-flash",
        )
    )

    # Judge execution with manage_quota=False
    judge_mgr = AIExecutionManager(
        provider=mock_provider,
        quota=adapter,
        timeout_seconds=5.0,
        max_retries=0,
        manage_quota=False,
    )

    await judge_mgr.execute(
        user_id=user_id,
        operation_type="VALIDATION_JUDGE",
        system_prompt="sys",
        user_prompt="user",
        response_schema={"type": "object"},
        thinking_level="HIGH",
        step_name="TIER3_PEDAGOGICAL_JUDGE",
    )

    usage_logs = [item for item in session.added if isinstance(item, AIUsageLogORM)]
    assert len(usage_logs) == 1
    log = usage_logs[0]

    assert log.action_type == "AI_REVIEW_MILESTONE"
    assert log.status == "SUCCESS"
    assert log.prompt_tokens == 1500
    assert log.completion_tokens == 300
    assert log.total_tokens == 1800

    # (1500 * 0.75 + 300 * 3.75) / 1,000,000 = (1125 + 1125) / 1,000,000 = 0.002250 USD
    assert log.estimated_cost_usd == Decimal("0.002250")
