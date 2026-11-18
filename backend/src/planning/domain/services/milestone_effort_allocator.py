from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Literal

from src.planning.domain.models.milestone import Milestone
from src.planning.domain.services.spatio_temporal_engine import SpatioTemporalRuleEngine
from src.planning.domain.services.validation_types import (
    AI_BLOCK_MIN_MINUTES,
    AvailabilityConfigurationDTO,
)

PreliminaryFeasibilityStatus = Literal[
    "FULL_SCOPE_FEASIBLE",
    "FIT_CAPACITY_REQUIRES_APPROVAL",
    "PRELIMINARY_UNSCHEDULABLE",
]
ScopeApprovalStatus = Literal[
    "NOT_REQUIRED",
    "PENDING_LEARNER_APPROVAL",
    "APPROVED_BY_LEARNER",
]

DEFAULT_ALPHA_BY_LEVEL: dict[str, float] = {
    "BEGINNER": 1.15,
    "INTERMEDIATE": 1.00,
    "ADVANCED": 0.85,
}

_PRACTICAL_WORK_RE = re.compile(
    r"(?:cài đặt|triển khai|xây dựng|viết|thiết lập|lập trình|tối ưu|profile|"
    r"benchmark|kiểm thử|\btest\b|docker|terraform|pipeline|driver|firmware|"
    r"grafana|prometheus|deploy|debug|implement|build|configure)",
    re.IGNORECASE,
)

_CAPSTONE_DELIVERABLE_RE = re.compile(
    r"(?:đồ án|dự án\s+(?:tốt nghiệp|tổng hợp|cuối|tích hợp)|tốt nghiệp|"
    r"capstone|end-to-end|tích hợp toàn diện|chaos\s*test|3-node)",
    re.IGNORECASE,
)


def _round_to_30(minutes: float) -> int:
    return max(30, int(round(minutes / 30.0)) * 30)


def _floor_to_30(minutes: float) -> int:
    return max(0, int(minutes // 30) * 30)


def _ceil_to_30(minutes: float) -> int:
    if minutes <= 0:
        return 0
    return int(math.ceil(minutes / 30.0)) * 30


def compute_availability_fingerprint(
    availability: AvailabilityConfigurationDTO | None,
) -> str | None:
    """Compute a stable SHA-256 fingerprint for an effective AvailabilityConfigurationDTO."""
    if availability is None:
        return None
    slots = sorted(
        (
            str(s.day_of_week).strip().lower(),
            (
                s.start_time.strftime("%H:%M")
                if hasattr(s.start_time, "strftime")
                else str(s.start_time).strip()
            ),
            (
                s.end_time.strftime("%H:%M")
                if hasattr(s.end_time, "strftime")
                else str(s.end_time).strip()
            ),
            int(s.end_day_offset or 0),
            bool(s.is_active),
        )
        for s in availability.availability_slots
    )
    canonical = {
        "mode": str(availability.mode).strip().upper(),
        "default_daily_quota_minutes": int(availability.default_daily_quota_minutes),
        "daily_quota_minutes": {
            str(k).strip().lower(): int(v)
            for k, v in sorted(
                availability.daily_quota_minutes.items(),
                key=lambda kv: str(kv[0]),
            )
        },
        "availability_slots": slots,
        "disabled_weekdays": sorted(str(d).strip().lower() for d in availability.disabled_weekdays),
    }
    digest = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}"


def compute_existing_tasks_fingerprint(existing_tasks: Sequence[Any]) -> str:
    """Compute a stable SHA-256 fingerprint for active existing tasks & calendar blocks."""
    items: list[tuple[str, str, str, str, int, str]] = []
    for ext in existing_tasks:
        if isinstance(ext, dict):
            tid = str(ext.get("task_id") or ext.get("id") or "")
            s_date = str(ext.get("scheduled_date") or "")
            s_start = str(ext.get("scheduled_start") or ext.get("planned_start_at") or "")
            s_end = str(ext.get("scheduled_end") or ext.get("planned_end_at") or "")
            mins = int(ext.get("estimated_minutes") or 0)
            status = str(ext.get("status") or "TODO").upper()
        else:
            tid = str(getattr(ext, "task_id", None) or getattr(ext, "id", "") or "")
            raw_d = getattr(ext, "scheduled_date", None)
            s_date = (
                raw_d.isoformat()
                if raw_d is not None and hasattr(raw_d, "isoformat")
                else str(raw_d or "")
            )
            raw_s = getattr(ext, "scheduled_start", None) or getattr(ext, "planned_start_at", None)
            s_start = (
                raw_s.isoformat()
                if raw_s is not None and hasattr(raw_s, "isoformat")
                else str(raw_s or "")
            )
            raw_e = getattr(ext, "scheduled_end", None) or getattr(ext, "planned_end_at", None)
            s_end = (
                raw_e.isoformat()
                if raw_e is not None and hasattr(raw_e, "isoformat")
                else str(raw_e or "")
            )
            mins = int(getattr(ext, "estimated_minutes", 0) or 0)
            status = str(getattr(ext, "status", "TODO") or "TODO").upper()
        if status in ("CANCELLED", "COMPLETED"):
            continue
        items.append((tid, s_date, s_start, s_end, mins, status))
    items.sort()
    digest = hashlib.sha256(json.dumps(items, ensure_ascii=False).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _extract_outcome_texts(raw_outcomes: Any) -> list[str]:
    texts: list[str] = []
    if not isinstance(raw_outcomes, (list, tuple)):
        return texts
    for item in raw_outcomes:
        if isinstance(item, dict):
            text = str(item.get("description") or item.get("text") or item.get("id") or "").strip()
        else:
            text = str(item).strip()
        if text:
            texts.append(text)
    return texts


def _distribute_30m_units(
    *,
    total_minutes: int,
    lower_bounds: Sequence[int],
    weights: Sequence[float],
) -> list[int]:
    """Distribute `total_minutes` across items in 30m increments >= `lower_bounds`."""
    n = len(lower_bounds)
    if n == 0:
        return []

    lbs = [_ceil_to_30(lb) if lb > 0 else 60 for lb in lower_bounds]
    lb_sum = sum(lbs)
    target = max(lb_sum, _floor_to_30(total_minutes) if total_minutes >= lb_sum else lb_sum)
    extra_units = max(0, (target - lb_sum) // 30)
    if extra_units == 0:
        return lbs

    safe_weights = [max(0.001, float(w)) for w in weights]
    weight_sum = sum(safe_weights)
    if weight_sum <= 0:
        safe_weights = [1.0] * n
        weight_sum = float(n)

    exact_shares = [(w / weight_sum) * extra_units for w in safe_weights]
    floored = [int(math.floor(s)) for s in exact_shares]
    rem = extra_units - sum(floored)
    remainders = sorted(
        range(n),
        key=lambda idx: (-(exact_shares[idx] - floored[idx]), -safe_weights[idx], idx),
    )
    for idx in remainders[:rem]:
        floored[idx] += 1

    return [lbs[i] + floored[i] * 30 for i in range(n)]


@dataclass(frozen=True, slots=True)
class MilestoneEffortBreakdown:
    """Three distinct deterministic effort quantities per milestone (all 30m increments)."""

    sequence_order: int
    milestone_id: str | None
    title: str
    llm_effort_minutes: int
    heuristic_baseline_minutes: int
    raw_heuristic_minutes: float
    estimated_effort_minutes: int
    minimum_defensible_effort_minutes: int
    normalized_planned_effort_minutes: int
    is_practical: bool
    is_capstone: bool
    outcome_count: int
    concept_count: int
    kept_in_scope: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence_order": self.sequence_order,
            "milestone_id": self.milestone_id,
            "title": self.title,
            "llm_effort_minutes": self.llm_effort_minutes,
            "heuristic_baseline_minutes": self.heuristic_baseline_minutes,
            "estimated_effort_minutes": self.estimated_effort_minutes,
            "minimum_defensible_effort_minutes": self.minimum_defensible_effort_minutes,
            "normalized_planned_effort_minutes": self.normalized_planned_effort_minutes,
            "is_practical": self.is_practical,
            "is_capstone": self.is_capstone,
            "outcome_count": self.outcome_count,
            "concept_count": self.concept_count,
            "kept_in_scope": self.kept_in_scope,
        }


@dataclass(frozen=True, slots=True)
class PreliminaryFeasibilityResult:
    """Versioned preliminary milestone feasibility & effort allocation payload."""

    status: PreliminaryFeasibilityStatus
    scope_proposal_version: int
    scope_proposal_hash: str
    requires_learner_approval: bool
    scope_approval_status: ScopeApprovalStatus
    approved_scope_version: int | None
    hard_packable_capacity_minutes: int | None
    soft_target_capacity_minutes: int | None
    llm_estimated_total_minutes: int
    estimated_total_minutes: int
    minimum_defensible_total_minutes: int
    normalized_planned_total_minutes: int
    kept_scope: tuple[dict[str, Any], ...]
    deferred_scope: tuple[dict[str, Any], ...]
    expected_outcomes: tuple[str, ...]
    feasibility_reasons: tuple[dict[str, Any], ...]
    adjustment_options: dict[str, Any]
    breakdowns: tuple[MilestoneEffortBreakdown, ...]
    target_date: str | None = None
    availability_fingerprint: str | None = None
    existing_tasks_fingerprint: str | None = None
    effective_start_date: str | None = None
    prior_knowledge_level: str = "BEGINNER"

    def to_metadata_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "scope_proposal_version": self.scope_proposal_version,
            "scope_proposal_hash": self.scope_proposal_hash,
            "requires_learner_approval": self.requires_learner_approval,
            "scope_approval_status": self.scope_approval_status,
            "approved_scope_version": self.approved_scope_version,
            "hard_packable_capacity_minutes": self.hard_packable_capacity_minutes,
            "soft_target_capacity_minutes": self.soft_target_capacity_minutes,
            "llm_estimated_total_minutes": self.llm_estimated_total_minutes,
            "estimated_total_minutes": self.estimated_total_minutes,
            "minimum_defensible_total_minutes": self.minimum_defensible_total_minutes,
            "normalized_planned_total_minutes": self.normalized_planned_total_minutes,
            "target_date": self.target_date,
            "availability_fingerprint": self.availability_fingerprint,
            "existing_tasks_fingerprint": self.existing_tasks_fingerprint,
            "effective_start_date": self.effective_start_date,
            "prior_knowledge_level": self.prior_knowledge_level,
            "kept_scope": [dict(item) for item in self.kept_scope],
            "deferred_scope": [dict(item) for item in self.deferred_scope],
            "expected_outcomes": list(self.expected_outcomes),
            "feasibility_reasons": [dict(r) for r in self.feasibility_reasons],
            "adjustment_options": dict(self.adjustment_options),
            "three_effort_breakdown": [b.to_dict() for b in self.breakdowns],
        }

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "scope_proposal_version": self.scope_proposal_version,
            "scope_approval_status": self.scope_approval_status,
            "requires_learner_approval": self.requires_learner_approval,
            "hard_packable_capacity_minutes": self.hard_packable_capacity_minutes,
            "soft_target_capacity_minutes": self.soft_target_capacity_minutes,
            "normalized_planned_total_minutes": self.normalized_planned_total_minutes,
            "kept_sequence_orders": [int(item["sequence_order"]) for item in self.kept_scope],
            "deferred_sequence_orders": [
                int(item["sequence_order"]) for item in self.deferred_scope
            ],
        }


class MilestoneEffortAllocator:
    """Pure domain service computing Hybrid 3-Effort Milestone allocations & Versioned Feasibility."""

    @staticmethod
    def _normalize_milestone_record(
        raw: dict[str, Any] | Milestone,
        *,
        fallback_seq: int,
    ) -> dict[str, Any]:
        if isinstance(raw, Milestone):
            return {
                "sequence_order": int(raw.sequence_order),
                "milestone_id": str(raw.id),
                "title": str(raw.title).strip(),
                "description": str(raw.description or "").strip(),
                "learning_outcomes": list(raw.learning_outcomes),
                "completion_criteria": str(raw.completion_criteria or "").strip(),
                "estimated_effort_minutes": int(raw.estimated_effort_minutes),
                "required_concepts": list(raw.required_concepts),
                "unverified_concepts": list(raw.unverified_concepts),
                "prerequisite_milestone_ids": [str(pid) for pid in raw.prerequisite_milestone_ids],
                "dependencies": [],
            }
        seq = int(raw.get("sequence_order") or fallback_seq)
        mid = raw.get("milestone_id") or raw.get("id")
        return {
            "sequence_order": seq,
            "milestone_id": str(mid) if mid is not None else None,
            "title": str(raw.get("title") or f"Cột mốc {seq}").strip(),
            "description": str(raw.get("description") or "").strip(),
            "learning_outcomes": _extract_outcome_texts(raw.get("learning_outcomes")),
            "completion_criteria": str(raw.get("completion_criteria") or "").strip(),
            "estimated_effort_minutes": max(15, int(raw.get("estimated_effort_minutes") or 60)),
            "required_concepts": [
                str(c).strip() for c in (raw.get("required_concepts") or []) if str(c).strip()
            ],
            "unverified_concepts": [
                str(c).strip() for c in (raw.get("unverified_concepts") or []) if str(c).strip()
            ],
            "prerequisite_milestone_ids": [
                str(pid) for pid in (raw.get("prerequisite_milestone_ids") or [])
            ],
            "dependencies": [
                int(dep)
                for dep in (raw.get("dependencies") or [])
                if isinstance(dep, int) or (isinstance(dep, str) and dep.isdigit())
            ],
        }

    @classmethod
    def _compute_baseline_heuristic(
        cls,
        item: dict[str, Any],
        *,
        alpha_level: float,
        b_outcome: float = 40.0,
        b_concept: float = 20.0,
        b_practical: float = 30.0,
        b_capstone: float = 60.0,
    ) -> tuple[float, int, bool, bool, int]:
        outcomes: list[str] = item["learning_outcomes"]
        outcome_workload = 0.0
        for outcome_text in outcomes:
            verbs = len(_PRACTICAL_WORK_RE.findall(outcome_text))
            complexity_bonus = min(
                40.0,
                max(0.0, (len(outcome_text) - 95) // 4) + max(0, verbs - 1) * 10.0,
            )
            outcome_workload += b_outcome + complexity_bonus

        concept_count = len(item["required_concepts"]) + len(item["unverified_concepts"])
        concept_workload = b_concept * min(6, concept_count)

        title = item["title"]
        desc = item["description"]
        crit = item["completion_criteria"]
        combined_text = f"{title} {desc} {crit}"
        practical_matches = len(_PRACTICAL_WORK_RE.findall(combined_text))
        is_practical = practical_matches > 0
        is_capstone = bool(_CAPSTONE_DELIVERABLE_RE.search(f"{title} {crit}"))

        practical_density = min(25.0, float(max(0, practical_matches - 1)) * 5.0)
        practical_and_capstone_load = (
            (b_practical if is_practical else 0.0)
            + practical_density
            + (b_capstone if is_capstone else 0.0)
        )

        m_floor = 90 if is_capstone else 60
        raw_h = alpha_level * (outcome_workload + concept_workload + practical_and_capstone_load)
        h_est = max(m_floor, _round_to_30(raw_h))
        return raw_h, h_est, is_practical, is_capstone, m_floor

    @staticmethod
    def _build_dependency_map(records: Sequence[dict[str, Any]]) -> dict[int, set[int]]:
        id_to_seq = {
            str(r["milestone_id"]): int(r["sequence_order"])
            for r in records
            if r.get("milestone_id")
        }
        seq_set = {int(r["sequence_order"]) for r in records}
        deps_map: dict[int, set[int]] = {}
        for r in records:
            seq = int(r["sequence_order"])
            deps: set[int] = {
                int(d) for d in r.get("dependencies", []) if int(d) in seq_set and int(d) != seq
            }
            for pid in r.get("prerequisite_milestone_ids", []):
                mapped = id_to_seq.get(str(pid))
                if mapped is not None and mapped != seq:
                    deps.add(mapped)
            deps_map[seq] = deps
        return deps_map

    @classmethod
    def _transitive_ancestors(cls, seq: int, deps_map: dict[int, set[int]]) -> set[int]:
        visited: set[int] = {seq}
        stack: list[int] = list(deps_map.get(seq, set()))
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            stack.extend(deps_map.get(cur, set()))
        return visited

    @staticmethod
    def _estimate_adjustment_options(
        *,
        hard_packable_capacity_minutes: int | None,
        soft_target_capacity_minutes: int | None,
        minimum_defensible_total_minutes: int,
        estimated_total_minutes: int,
        llm_estimated_total_minutes: int,
        start_date: date | None,
        target_date: date | None,
        availability: AvailabilityConfigurationDTO | None,
        existing_tasks: Sequence[Any] = (),
    ) -> dict[str, Any]:
        target_min_req = max(AI_BLOCK_MIN_MINUTES, minimum_defensible_total_minutes)
        target_max_req = max(target_min_req, estimated_total_minutes, llm_estimated_total_minutes)

        earliest_range: dict[str, str] | None = None
        if start_date is not None and availability is not None:
            ctx = SpatioTemporalRuleEngine._build_calendar_context(
                availability,
                existing_tasks=existing_tasks,
            )
            cum_cap = 0
            min_date_found: date | None = None
            max_date_found: date | None = None
            for offset in range(730):
                d = start_date + timedelta(days=offset)
                free_ivs, rem_cap, _ = SpatioTemporalRuleEngine._day_free_windows(
                    ctx,
                    d,
                    earliest_min=0,
                    used_today=ctx["existing_used"].get(d, 0),
                    occupied=ctx["existing_intervals"].get(d, ()),
                )
                usable = sum(e - s for s, e in free_ivs if (e - s) >= AI_BLOCK_MIN_MINUTES)
                cum_cap += min(rem_cap, usable)
                if min_date_found is None and cum_cap >= target_min_req:
                    min_date_found = d
                if max_date_found is None and cum_cap >= target_max_req:
                    max_date_found = d
                    break
            if min_date_found is not None:
                earliest_range = {
                    "min_date": min_date_found.isoformat(),
                    "max_date": (max_date_found or min_date_found).isoformat(),
                }
        elif (
            start_date is not None
            and target_date is not None
            and hard_packable_capacity_minutes is not None
            and hard_packable_capacity_minutes > 0
        ):
            span_days = max(1, (target_date - start_date).days + 1)
            avg_per_day = hard_packable_capacity_minutes / span_days
            if avg_per_day > 0:
                min_days = max(1, math.ceil(target_min_req / avg_per_day))
                max_days = max(min_days, math.ceil(target_max_req / avg_per_day))
                earliest_range = {
                    "min_date": (start_date + timedelta(days=min_days - 1)).isoformat(),
                    "max_date": (start_date + timedelta(days=max_days - 1)).isoformat(),
                }

        p_hard = hard_packable_capacity_minutes or 0
        deficit = max(0, target_min_req - p_hard)
        if deficit == 0 and soft_target_capacity_minutes is not None:
            deficit = max(0, estimated_total_minutes - soft_target_capacity_minutes)
        weeks = (
            max(1.0, ((target_date - start_date).days + 1) / 7.0)
            if (start_date is not None and target_date is not None and target_date >= start_date)
            else 4.0
        )
        add_weekly = _ceil_to_30(deficit / weeks) if deficit > 0 else 0
        if deficit > 0 and add_weekly == 0:
            add_weekly = 30

        return {
            "is_approximate": True,
            "estimated_earliest_target_date_range": earliest_range,
            "recommended_additional_weekly_minutes": add_weekly,
        }

    @staticmethod
    def _compute_proposal_hash(
        *,
        version: int,
        status: PreliminaryFeasibilityStatus,
        kept_scope: Sequence[dict[str, Any]],
        deferred_scope: Sequence[dict[str, Any]],
        hard_packable_capacity_minutes: int | None,
        target_date: date | str | None = None,
        availability_fingerprint: str | None = None,
        existing_tasks_fingerprint: str | None = None,
        milestone_dependencies: Sequence[Any] = (),
    ) -> str:
        target_date_iso = (
            target_date.isoformat()
            if isinstance(target_date, date)
            else (str(target_date).strip() if target_date else None)
        )
        canonical = {
            "scope_proposal_version": version,
            "status": status,
            "hard_packable_capacity_minutes": hard_packable_capacity_minutes,
            "target_date": target_date_iso,
            "availability_fingerprint": availability_fingerprint,
            "existing_tasks_fingerprint": existing_tasks_fingerprint,
            "milestone_dependencies": [str(dep) for dep in milestone_dependencies],
            "kept_scope": [
                {
                    "sequence_order": int(item["sequence_order"]),
                    "milestone_id": (
                        str(item["milestone_id"]) if item.get("milestone_id") is not None else None
                    ),
                    "title": str(item["title"]),
                    "completion_criteria": str(item.get("completion_criteria") or ""),
                    "normalized_planned_effort_minutes": int(
                        item["normalized_planned_effort_minutes"]
                    ),
                    "expected_outcomes": list(item.get("expected_outcomes", [])),
                    "dependencies": sorted(
                        int(d)
                        for d in (item.get("dependencies") or [])
                        if isinstance(d, int) or (isinstance(d, str) and d.isdigit())
                    ),
                    "prerequisite_milestone_ids": sorted(
                        str(pid) for pid in (item.get("prerequisite_milestone_ids") or []) if pid
                    ),
                }
                for item in kept_scope
            ],
            "deferred_scope": [
                {
                    "sequence_order": int(item["sequence_order"]),
                    "milestone_id": (
                        str(item["milestone_id"]) if item.get("milestone_id") is not None else None
                    ),
                    "title": str(item["title"]),
                    "completion_criteria": str(item.get("completion_criteria") or ""),
                    "dependencies": sorted(
                        int(d)
                        for d in (item.get("dependencies") or [])
                        if isinstance(d, int) or (isinstance(d, str) and d.isdigit())
                    ),
                    "prerequisite_milestone_ids": sorted(
                        str(pid) for pid in (item.get("prerequisite_milestone_ids") or []) if pid
                    ),
                }
                for item in deferred_scope
            ],
        }
        digest = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        return f"sha256:{digest}"

    @classmethod
    def allocate(
        cls,
        milestones: Sequence[dict[str, Any] | Milestone],
        *,
        hard_packable_capacity_minutes: int | None,
        prior_knowledge_level: str = "BEGINNER",
        target_utilization: float = 0.85,
        gamma_min: float = 0.65,
        alpha_by_level: Mapping[str, float] | None = None,
        previous_scope_proposal_version: int = 0,
        start_date: date | None = None,
        target_date: date | None = None,
        availability: AvailabilityConfigurationDTO | None = None,
        existing_tasks: Sequence[Any] = (),
    ) -> PreliminaryFeasibilityResult:
        """Compute 3-effort breakdown, preliminary feasibility zone, and versioned scope proposal."""
        if not milestones:
            raise ValueError("MilestoneEffortAllocator requires at least one milestone.")

        normalized_records = sorted(
            (
                cls._normalize_milestone_record(item, fallback_seq=idx)
                for idx, item in enumerate(milestones, start=1)
            ),
            key=lambda r: int(r["sequence_order"]),
        )
        alphas = dict(DEFAULT_ALPHA_BY_LEVEL)
        if alpha_by_level is not None:
            alphas.update({str(k).upper(): float(v) for k, v in alpha_by_level.items()})
        alpha_level = alphas.get(str(prior_knowledge_level or "INTERMEDIATE").upper(), 1.00)

        llm_efforts: list[int] = []
        raw_heuristics: list[float] = []
        h_ests: list[int] = []
        m_floors: list[int] = []
        practical_flags: list[bool] = []
        capstone_flags: list[bool] = []

        for rec in normalized_records:
            llm_efforts.append(int(rec["estimated_effort_minutes"]))
            raw_h, h_est, is_prac, is_cap, m_floor = cls._compute_baseline_heuristic(
                rec,
                alpha_level=alpha_level,
            )
            raw_heuristics.append(raw_h)
            h_ests.append(h_est)
            m_floors.append(m_floor)
            practical_flags.append(is_prac)
            capstone_flags.append(is_cap)

        n = len(normalized_records)
        all_efforts_equal = n > 1 and len(set(llm_efforts)) == 1
        sum_llm = sum(llm_efforts)

        if all_efforts_equal and len({round(h, 4) for h in raw_heuristics}) > 1:
            e_ests = _distribute_30m_units(
                total_minutes=_round_to_30(sum_llm),
                lower_bounds=m_floors,
                weights=raw_heuristics,
            )
        else:
            e_ests = [
                max(m_floors[i], _round_to_30(0.60 * llm_efforts[i] + 0.40 * h_ests[i]))
                for i in range(n)
            ]

        e_mins = [
            max(
                m_floors[i],
                _round_to_30(
                    max(
                        float(m_floors[i]), min(float(llm_efforts[i]), float(h_ests[i])) * gamma_min
                    )
                ),
            )
            for i in range(n)
        ]

        sum_est = sum(e_ests)
        sum_min = sum(e_mins)
        p_hard = hard_packable_capacity_minutes
        b_soft = (
            _floor_to_30(p_hard * float(target_utilization))
            if p_hard is not None and p_hard > 0
            else (0 if p_hard == 0 else None)
        )

        deps_map = cls._build_dependency_map(normalized_records)
        kept_seqs: set[int] = {int(r["sequence_order"]) for r in normalized_records}
        status: PreliminaryFeasibilityStatus = "FULL_SCOPE_FEASIBLE"
        requires_approval = False
        approval_status: ScopeApprovalStatus = "NOT_REQUIRED"
        proposal_version = max(0, int(previous_scope_proposal_version))
        e_plans: list[int]
        reasons: list[dict[str, Any]] = []
        adjustment_options: dict[str, Any] = {
            "is_approximate": True,
            "estimated_earliest_target_date_range": None,
            "recommended_additional_weekly_minutes": 0,
        }

        sum_m_floors = sum(m_floors)
        if p_hard is None:
            e_plans = list(e_ests)
        elif p_hard < AI_BLOCK_MIN_MINUTES or e_mins[0] > p_hard:
            # Case 3: Even M1 cannot fit into P_hard (E_min,1 > P_hard or P_hard < 30m)
            status = "PRELIMINARY_UNSCHEDULABLE"
            kept_seqs = set()
            e_plans = [0] * n
            reasons.append(
                {
                    "code": "PRELIMINARY_UNSCHEDULABLE",
                    "hard_packable_capacity_minutes": p_hard,
                    "soft_target_capacity_minutes": b_soft,
                    "first_milestone_minimum_minutes": e_mins[0],
                    "first_milestone_llm_minutes": llm_efforts[0],
                    "minimum_defensible_total_minutes": sum_min,
                    "llm_estimated_total_minutes": sum_llm,
                    "message": (
                        f"Quỹ thời gian khả dụng ({p_hard} phút) không đủ cho cột mốc nền tảng đầu tiên "
                        f"(tối thiểu {e_mins[0]} phút)."
                    ),
                }
            )
            adjustment_options = cls._estimate_adjustment_options(
                hard_packable_capacity_minutes=p_hard,
                soft_target_capacity_minutes=b_soft,
                minimum_defensible_total_minutes=sum_min,
                estimated_total_minutes=sum_est,
                llm_estimated_total_minutes=sum_llm,
                start_date=start_date,
                target_date=target_date,
                availability=availability,
                existing_tasks=existing_tasks,
            )
        elif b_soft is not None and sum_est <= b_soft and sum_est <= p_hard:
            # Case 1A: Concise / comfortable fit <= 85% soft target -> NEVER inflate!
            status = "FULL_SCOPE_FEASIBLE"
            e_plans = list(e_ests)
        elif sum_m_floors <= p_hard and (
            sum_est <= p_hard or sum_min <= p_hard or sum_llm <= p_hard
        ):
            # Case 1B (Decision 1 & 2): FULL_SCOPE fits hard capacity while honoring m_floors.
            # Never lower below m_floors or push sum(e_plans) > p_hard.
            status = "FULL_SCOPE_FEASIBLE"
            usable_hard = _floor_to_30(p_hard)
            if sum_min <= p_hard:
                lbs = list(e_mins)
                soft_floor_target = max(b_soft or 0, sum_min)
                target_total = min(usable_hard, sum_est, soft_floor_target)
            else:
                # sum_llm <= p_hard < sum_min while sum(m_floors) <= p_hard
                lbs = list(m_floors)
                target_total = min(usable_hard, max(sum_m_floors, _floor_to_30(sum_llm)))
            # Blend subtle raw heuristic tie-breaker so proportional scaling preserves differentiation
            weights = [
                max(1.0, float(e_ests[i] - lbs[i]) + 0.05 * raw_heuristics[i]) for i in range(n)
            ]
            e_plans = _distribute_30m_units(
                total_minutes=target_total,
                lower_bounds=lbs,
                weights=weights,
            )
        else:
            # Case 2 (Decision 1 & 2): Full scope cannot fit (either sum(m_floors) > P_hard,
            # or BOTH sum(E_llm) > P_hard AND sum(E_min) > P_hard) while E_min,1 <= P_hard.
            status = "FIT_CAPACITY_REQUIRES_APPROVAL"
            requires_approval = True
            approval_status = "PENDING_LEARNER_APPROVAL"
            proposal_version += 1

            seq_to_idx = {
                int(rec["sequence_order"]): idx for idx, rec in enumerate(normalized_records)
            }
            kept_seqs = set()
            soft_budget = b_soft if (b_soft is not None and b_soft > 0) else p_hard
            for rec in normalized_records:
                seq = int(rec["sequence_order"])
                closure = kept_seqs | cls._transitive_ancestors(seq, deps_map)
                closure_min = sum(e_mins[seq_to_idx[s]] for s in closure)
                active_limit = soft_budget if kept_seqs else p_hard
                if closure_min <= active_limit:
                    kept_seqs = closure

            # Safety guard: if even M1 closure exceeded soft_budget but M1 fits P_hard
            if not kept_seqs and e_mins[0] <= p_hard:
                kept_seqs = cls._transitive_ancestors(
                    int(normalized_records[0]["sequence_order"]), deps_map
                )
                if sum(e_mins[seq_to_idx[s]] for s in kept_seqs) > p_hard:
                    kept_seqs = {int(normalized_records[0]["sequence_order"])}

            kept_indices = [
                i
                for i, rec in enumerate(normalized_records)
                if int(rec["sequence_order"]) in kept_seqs
            ]
            if kept_indices:
                kept_min_sum = sum(e_mins[i] for i in kept_indices)
                kept_est_sum = sum(e_ests[i] for i in kept_indices)
                usable_hard = _floor_to_30(p_hard)
                if kept_est_sum <= (b_soft or p_hard) and kept_est_sum <= p_hard:
                    kept_plans = [e_ests[i] for i in kept_indices]
                else:
                    kept_target = min(usable_hard, kept_est_sum, max(b_soft or 0, kept_min_sum))
                    kept_plans = _distribute_30m_units(
                        total_minutes=kept_target,
                        lower_bounds=[e_mins[i] for i in kept_indices],
                        weights=[
                            max(1.0, float(e_ests[i] - e_mins[i]) + 0.05 * raw_heuristics[i])
                            for i in kept_indices
                        ],
                    )
                plan_by_idx = dict(zip(kept_indices, kept_plans, strict=True))
                e_plans = [plan_by_idx[i] if i in plan_by_idx else e_ests[i] for i in range(n)]
            else:
                e_plans = list(e_ests)

            reasons.append(
                {
                    "code": "FIT_CAPACITY_REQUIRED",
                    "hard_packable_capacity_minutes": p_hard,
                    "soft_target_capacity_minutes": b_soft,
                    "minimum_defensible_total_minutes": sum_min,
                    "llm_estimated_total_minutes": sum_llm,
                    "estimated_total_minutes": sum_est,
                    "message": (
                        f"Tổng thời lượng tối thiểu khả thi ({sum_min} phút) và ước tính AI ({sum_llm} phút) "
                        f"đều vượt quá quỹ thời gian đóng gói cứng ({p_hard} phút). Cần xác nhận thu gọn phạm vi."
                    ),
                }
            )
            adjustment_options = cls._estimate_adjustment_options(
                hard_packable_capacity_minutes=p_hard,
                soft_target_capacity_minutes=b_soft,
                minimum_defensible_total_minutes=sum_min,
                estimated_total_minutes=sum_est,
                llm_estimated_total_minutes=sum_llm,
                start_date=start_date,
                target_date=target_date,
                availability=availability,
                existing_tasks=existing_tasks,
            )

        breakdowns: list[MilestoneEffortBreakdown] = []
        kept_scope: list[dict[str, Any]] = []
        deferred_scope: list[dict[str, Any]] = []
        expected_outcomes: list[str] = []

        for i, rec in enumerate(normalized_records):
            seq = int(rec["sequence_order"])
            is_kept = seq in kept_seqs
            bd = MilestoneEffortBreakdown(
                sequence_order=seq,
                milestone_id=rec["milestone_id"],
                title=rec["title"],
                llm_effort_minutes=llm_efforts[i],
                heuristic_baseline_minutes=h_ests[i],
                raw_heuristic_minutes=round(raw_heuristics[i], 2),
                estimated_effort_minutes=e_ests[i],
                minimum_defensible_effort_minutes=e_mins[i],
                normalized_planned_effort_minutes=e_plans[i],
                is_practical=practical_flags[i],
                is_capstone=capstone_flags[i],
                outcome_count=len(rec["learning_outcomes"]),
                concept_count=len(rec["required_concepts"]) + len(rec["unverified_concepts"]),
                kept_in_scope=is_kept,
            )
            breakdowns.append(bd)

            formatted_outcomes = [
                f"M{seq}-O{o_idx}: {o_txt}" if not o_txt.startswith(f"M{seq}-O") else o_txt
                for o_idx, o_txt in enumerate(rec["learning_outcomes"], start=1)
            ]
            if is_kept:
                kept_scope.append(
                    {
                        "sequence_order": seq,
                        "milestone_id": rec["milestone_id"],
                        "title": rec["title"],
                        "completion_criteria": rec["completion_criteria"],
                        "estimated_effort_minutes": e_ests[i],
                        "minimum_defensible_effort_minutes": e_mins[i],
                        "normalized_planned_effort_minutes": e_plans[i],
                        "expected_outcomes": formatted_outcomes,
                        "dependencies": sorted(deps_map.get(seq, set())),
                        "prerequisite_milestone_ids": sorted(
                            str(pid) for pid in rec.get("prerequisite_milestone_ids", []) if pid
                        ),
                    }
                )
                expected_outcomes.extend(formatted_outcomes)
            else:
                deferred_scope.append(
                    {
                        "sequence_order": seq,
                        "milestone_id": rec["milestone_id"],
                        "title": rec["title"],
                        "completion_criteria": rec["completion_criteria"],
                        "estimated_effort_minutes": e_ests[i],
                        "minimum_defensible_effort_minutes": e_mins[i],
                        "learning_outcomes": formatted_outcomes,
                        "dependencies": sorted(deps_map.get(seq, set())),
                        "prerequisite_milestone_ids": sorted(
                            str(pid) for pid in rec.get("prerequisite_milestone_ids", []) if pid
                        ),
                    }
                )

        avail_fp = compute_availability_fingerprint(availability)
        existing_fp = compute_existing_tasks_fingerprint(existing_tasks)
        target_date_iso = target_date.isoformat() if target_date is not None else None
        effective_start_iso = start_date.isoformat() if start_date is not None else None

        proposal_hash = cls._compute_proposal_hash(
            version=proposal_version,
            status=status,
            kept_scope=kept_scope,
            deferred_scope=deferred_scope,
            hard_packable_capacity_minutes=p_hard,
            target_date=target_date_iso,
            availability_fingerprint=avail_fp,
            existing_tasks_fingerprint=existing_fp,
        )
        planned_kept_total = sum(
            b.normalized_planned_effort_minutes for b in breakdowns if b.kept_in_scope
        )
        if status == "FIT_CAPACITY_REQUIRES_APPROVAL":
            assert len(kept_scope) >= 1, "FIT_CAPACITY_REQUIRES_APPROVAL must keep >= 1 milestone"
            if p_hard is not None:
                assert planned_kept_total <= p_hard
        elif status == "FULL_SCOPE_FEASIBLE" and p_hard is not None:
            assert planned_kept_total <= p_hard
            assert all(e_plans[i] >= m_floors[i] for i in range(n))

        return PreliminaryFeasibilityResult(
            status=status,
            scope_proposal_version=proposal_version,
            scope_proposal_hash=proposal_hash,
            requires_learner_approval=requires_approval,
            scope_approval_status=approval_status,
            approved_scope_version=None,
            hard_packable_capacity_minutes=p_hard,
            soft_target_capacity_minutes=b_soft,
            llm_estimated_total_minutes=sum_llm,
            estimated_total_minutes=sum_est,
            minimum_defensible_total_minutes=sum_min,
            normalized_planned_total_minutes=planned_kept_total,
            kept_scope=tuple(kept_scope),
            deferred_scope=tuple(deferred_scope),
            expected_outcomes=tuple(expected_outcomes),
            feasibility_reasons=tuple(reasons),
            adjustment_options=adjustment_options,
            breakdowns=tuple(breakdowns),
            target_date=target_date_iso,
            availability_fingerprint=avail_fp,
            existing_tasks_fingerprint=existing_fp,
            effective_start_date=effective_start_iso,
            prior_knowledge_level=str(prior_knowledge_level or "BEGINNER").upper(),
        )
