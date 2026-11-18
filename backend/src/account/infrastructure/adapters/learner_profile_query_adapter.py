import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from src.account.infrastructure.orm.learner_memory_orm import (
    LearnerConceptMasteryORM,
    LearnerMemoryItemORM,
)
from src.account.infrastructure.orm.user_orm import LearnerProfileORM
from src.account.public_api import (
    ConceptMasterySnapshotDTO,
    LearnerMemoryItemSnapshotDTO,
    LearnerMemoryQueryPort,
    LearnerProfileDTO,
    LearnerProfileQueryPort,
)


class LearnerProfileQueryAdapter(LearnerProfileQueryPort, LearnerMemoryQueryPort):
    """Cross-context adapter for Zimmerman SRL Learner Profile, Memory & Mastery (ADR-010).

    Returns persisted profile or cold-start defaults (opt_session_minutes=45,
    estimation_bias_beta=1.0, peak_productivity_slots={}) when no record exists.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_learner_profile(self, user_id: UUID) -> LearnerProfileDTO:
        stmt = select(LearnerProfileORM).where(LearnerProfileORM.user_id == user_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return LearnerProfileDTO(
                user_id=user_id,
                opt_session_minutes=45,
                estimation_bias_beta=1.0,
                peak_productivity_slots={},
                is_cold_start=True,
            )

        raw_slots = row.peak_productivity_slots
        if isinstance(raw_slots, dict):
            slots_dict: dict[str, Any] = dict(raw_slots)
        elif isinstance(raw_slots, list):
            slots_dict = {"preferred_periods": list(raw_slots)}
        else:
            slots_dict = {}

        return LearnerProfileDTO(
            user_id=row.user_id,
            opt_session_minutes=int(row.optimal_focus_duration_mins),
            estimation_bias_beta=float(row.estimation_bias_factor),
            peak_productivity_slots=slots_dict,
            is_cold_start=bool(row.is_cold_start),
        )

    async def list_active_memory_items(
        self,
        user_id: UUID,
        limit: int = 20,
    ) -> list[LearnerMemoryItemSnapshotDTO]:
        stmt = (
            select(LearnerMemoryItemORM)
            .where(
                LearnerMemoryItemORM.user_id == user_id,
                LearnerMemoryItemORM.status != "REJECTED",
            )
            .order_by(
                LearnerMemoryItemORM.confidence.desc(),
                LearnerMemoryItemORM.updated_at.desc(),
            )
            .limit(max(1, limit))
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        items: list[LearnerMemoryItemSnapshotDTO] = []
        for row in rows:
            val = row.value
            if isinstance(val, dict):
                val_str = str(
                    val.get("summary") or val.get("value") or json.dumps(val, ensure_ascii=False)
                )
                source_wf = str(val.get("source_workflow") or row.epistemic_level)
            else:
                val_str = str(val)
                source_wf = row.epistemic_level
            items.append(
                LearnerMemoryItemSnapshotDTO(
                    id=row.id,
                    user_id=row.user_id,
                    category=row.category,
                    memory_key=row.memory_key,
                    memory_value=val_str,
                    confidence=float(row.confidence),
                    source_workflow=source_wf,
                    status=row.status,
                )
            )
        return items

    async def list_concept_masteries(
        self,
        user_id: UUID,
        concept_ids: list[str] | None = None,
    ) -> list[ConceptMasterySnapshotDTO]:
        stmt = select(LearnerConceptMasteryORM).where(LearnerConceptMasteryORM.user_id == user_id)
        if concept_ids:
            stmt = stmt.where(LearnerConceptMasteryORM.concept_key.in_(concept_ids))
        stmt = stmt.order_by(LearnerConceptMasteryORM.updated_at.desc())
        rows = list((await self._session.execute(stmt)).scalars().all())
        results: list[ConceptMasterySnapshotDTO] = []
        for row in rows:
            score = float(row.mastery_score)
            status_str = (
                "MASTERED"
                if score >= 0.8
                else ("DEVELOPING" if score >= 0.5 else "NEEDS_REINFORCEMENT")
            )
            results.append(
                ConceptMasterySnapshotDTO(
                    user_id=row.user_id,
                    concept_id=row.concept_key,
                    mastery_score=score,
                    status=status_str,
                    evidence_count=int(row.evidence_count),
                )
            )
        return results

    async def upsert_memory_and_mastery_feedback(
        self,
        user_id: UUID,
        *,
        memories: list[dict[str, Any]] | None = None,
        masteries: list[dict[str, Any]] | None = None,
    ) -> None:
        now = datetime.now(UTC)
        for mem in memories or []:
            key = str(mem.get("memory_key") or "").strip()[:160]
            if not key:
                continue
            existing = (
                await self._session.execute(
                    select(LearnerMemoryItemORM).where(
                        LearnerMemoryItemORM.user_id == user_id,
                        LearnerMemoryItemORM.memory_key == key,
                    )
                )
            ).scalar_one_or_none()
            if existing is not None and existing.status == "REJECTED":
                continue

            raw_cat = str(mem.get("category") or "BEHAVIOR").upper()
            category = (
                raw_cat
                if raw_cat in {"PREFERENCE", "BEHAVIOR", "KNOWLEDGE", "INTERACTION"}
                else "BEHAVIOR"
            )
            raw_ep = str(mem.get("epistemic_level") or "OBSERVED").upper()
            epistemic_level = (
                raw_ep if raw_ep in {"EXPLICIT", "OBSERVED", "INFERRED"} else "OBSERVED"
            )
            conf = max(0.0, min(1.0, float(mem.get("confidence", 0.75))))
            val_payload = mem.get("value")
            if not isinstance(val_payload, dict):
                val_payload = {
                    "summary": str(mem.get("memory_value") or val_payload or ""),
                    "source_workflow": str(mem.get("source_workflow") or "EVALUATION"),
                }
            ev_list = list(mem.get("evidence") or [])
            if existing is None:
                row = LearnerMemoryItemORM(
                    id=uuid7(),
                    user_id=user_id,
                    memory_key=key,
                    value=val_payload,
                    category=category,
                    epistemic_level=epistemic_level,
                    confidence=conf,
                    sample_size=max(1, int(mem.get("sample_size", 1))),
                    evidence=ev_list,
                    observation_started_at=now,
                    observation_ended_at=now,
                    status=str(mem.get("status") or "PENDING").upper(),
                    created_at=now,
                    updated_at=now,
                )
                self._session.add(row)
            else:
                existing.value = val_payload
                existing.category = category
                existing.confidence = conf
                existing.sample_size = int(existing.sample_size) + 1
                existing.evidence = [*list(existing.evidence or []), *ev_list][-20:]
                existing.observation_ended_at = now
                existing.updated_at = now

        for mast in masteries or []:
            concept_key = str(mast.get("concept_key") or mast.get("concept_id") or "").strip()[:160]
            if not concept_key:
                continue
            score = max(0.0, min(1.0, float(mast.get("mastery_score", 0.5))))
            raw_ev_type = str(mast.get("last_evidence_type") or "PROVE_MODE").upper()
            ev_type = (
                raw_ev_type if raw_ev_type in {"PROVE_MODE", "EVIDENCED_TAKEAWAY"} else "PROVE_MODE"
            )
            existing_m = (
                await self._session.execute(
                    select(LearnerConceptMasteryORM).where(
                        LearnerConceptMasteryORM.user_id == user_id,
                        LearnerConceptMasteryORM.concept_key == concept_key,
                    )
                )
            ).scalar_one_or_none()
            if existing_m is None:
                self._session.add(
                    LearnerConceptMasteryORM(
                        id=uuid7(),
                        user_id=user_id,
                        concept_key=concept_key,
                        mastery_score=Decimal(f"{score:.4f}"),
                        evidence_count=max(1, int(mast.get("evidence_count", 1))),
                        last_evidence_type=ev_type,
                        updated_at=now,
                    )
                )
            else:
                blended = (float(existing_m.mastery_score) * 0.4) + (score * 0.6)
                existing_m.mastery_score = Decimal(f"{max(0.0, min(1.0, blended)):.4f}")
                existing_m.evidence_count = int(existing_m.evidence_count) + 1
                existing_m.last_evidence_type = ev_type
                existing_m.updated_at = now

        await self._session.flush()

    async def get_by_user_id(self, user_id: UUID) -> LearnerProfileDTO:
        """Alias for get_learner_profile."""
        return await self.get_learner_profile(user_id)

    async def get_profile(self, user_id: UUID) -> LearnerProfileDTO:
        """Alias for get_learner_profile."""
        return await self.get_learner_profile(user_id)


SqlAlchemyLearnerProfileQueryAdapter = LearnerProfileQueryAdapter
