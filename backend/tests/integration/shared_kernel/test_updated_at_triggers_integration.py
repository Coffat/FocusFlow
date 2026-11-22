from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import delete, text
from uuid6 import uuid7

from src.account.infrastructure.orm.learner_memory_orm import (
    LearnerConceptMasteryORM,
    LearnerMemoryItemORM,
)
from src.account.infrastructure.orm.user_orm import UserORM
from src.planning.infrastructure.orm.knowledge_orm import KnowledgeSourceORM
from src.planning.infrastructure.orm.planning_orm import GoalORM, LearningConceptORM
from src.shared_kernel.infrastructure.database.session import async_session_factory
from src.shared_kernel.infrastructure.workflow.models import WorkflowRunORM

NEWLY_TRIGGERED_TABLES = (
    "knowledge_sources",
    "learner_concept_masteries",
    "learner_memory_items",
    "learning_concepts",
    "workflow_runs",
)


@pytest.mark.asyncio
async def test_all_26_updated_at_tables_have_before_update_triggers() -> None:
    """Every public table with an `updated_at` column must have a BEFORE UPDATE trigger."""
    async with async_session_factory() as session:
        cols_res = await session.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND column_name = 'updated_at'
                ORDER BY table_name
                """
            )
        )
        tables_with_updated_at = {str(r[0]) for r in cols_res.fetchall()}

        trig_res = await session.execute(
            text(
                """
                SELECT event_object_table
                FROM information_schema.triggers
                WHERE trigger_schema = 'public'
                  AND event_manipulation = 'UPDATE'
                  AND action_timing = 'BEFORE'
                  AND action_statement LIKE '%fn_set_updated_at%'
                """
            )
        )
        triggered_tables = {str(r[0]) for r in trig_res.fetchall()}

    assert len(tables_with_updated_at) == 26
    assert "notifications" in triggered_tables
    missing = tables_with_updated_at - triggered_tables
    assert not missing, f"Tables missing BEFORE UPDATE updated_at trigger: {sorted(missing)}"
    for tbl in NEWLY_TRIGGERED_TABLES:
        assert tbl in triggered_tables


@pytest.mark.asyncio
async def test_five_new_updated_at_triggers_advance_timestamp_on_raw_sql_update() -> None:
    """Real SQL UPDATE on each of the 5 newly-triggered tables must advance `updated_at`."""
    user_id = uuid7()
    goal_id = uuid7()
    ks_id = uuid7()
    lcm_id = uuid7()
    lmi_id = uuid7()
    lc_key = f"lc_{uuid7().hex}"
    wf_id = uuid7()

    old_ts = datetime.now(UTC) - timedelta(hours=2)

    async with async_session_factory() as session:
        session.add(
            UserORM(
                id=user_id,
                email=f"trig_test_{user_id.hex}@focusflow.vn",
                password_hash="argon2id$mockhash",
                full_name="Trigger Test User",
                timezone="UTC",
                role="LEARNER",
                tier="FREE",
                is_locked=False,
            )
        )
        await session.flush()

        session.add(
            GoalORM(
                id=goal_id,
                user_id=user_id,
                title="Trigger Test Goal",
                status="ACTIVE",
                created_at=old_ts,
                updated_at=old_ts,
            )
        )
        await session.flush()

        session.add(
            KnowledgeSourceORM(
                id=ks_id,
                user_id=user_id,
                goal_id=goal_id,
                source_type="TXT",
                title="Initial KS",
                content_hash="a" * 64,
                ingestion_status="INDEXED",
                chunk_count=0,
                provenance_metadata={},
                created_at=old_ts,
                updated_at=old_ts,
            )
        )
        session.add(
            LearnerConceptMasteryORM(
                id=lcm_id,
                user_id=user_id,
                concept_key=f"concept_{lcm_id.hex}",
                mastery_score=Decimal("0.5000"),
                evidence_count=1,
                last_evidence_type="PROVE_MODE",
                updated_at=old_ts,
            )
        )
        session.add(
            LearnerMemoryItemORM(
                id=lmi_id,
                user_id=user_id,
                memory_key=f"mem_{lmi_id.hex}",
                value={"summary": "initial"},
                category="BEHAVIOR",
                epistemic_level="OBSERVED",
                confidence=0.8,
                sample_size=1,
                evidence=[],
                status="CONFIRMED",
                created_at=old_ts,
                updated_at=old_ts,
            )
        )
        session.add(
            LearningConceptORM(
                concept_id=lc_key,
                title="Initial Concept",
                summary="Summary for trigger test",
                domain="CS",
                created_at=old_ts,
                updated_at=old_ts,
            )
        )
        session.add(
            WorkflowRunORM(
                id=wf_id,
                user_id=user_id,
                goal_id=goal_id,
                workflow_type="PLAN_CREATION",
                current_step="INIT",
                status="RUNNING",
                context_snapshot={},
                started_at=old_ts,
                created_at=old_ts,
                updated_at=old_ts,
            )
        )
        await session.commit()

    await asyncio.sleep(0.05)

    try:
        updates: list[tuple[str, str, UUID | str]] = [
            (
                "knowledge_sources",
                "UPDATE public.knowledge_sources SET title = 'Updated KS' WHERE id = :id RETURNING updated_at",
                ks_id,
            ),
            (
                "learner_concept_masteries",
                "UPDATE public.learner_concept_masteries SET evidence_count = 2 WHERE id = :id RETURNING updated_at",
                lcm_id,
            ),
            (
                "learner_memory_items",
                "UPDATE public.learner_memory_items SET sample_size = 2 WHERE id = :id RETURNING updated_at",
                lmi_id,
            ),
            (
                "learning_concepts",
                "UPDATE public.learning_concepts SET title = 'Updated Concept' WHERE concept_id = :id RETURNING updated_at",
                lc_key,
            ),
            (
                "workflow_runs",
                "UPDATE public.workflow_runs SET current_step = 'DONE' WHERE id = :id RETURNING updated_at",
                wf_id,
            ),
        ]

        async with async_session_factory() as session:
            for table_name, sql_str, row_id in updates:
                res = await session.execute(text(sql_str), {"id": row_id})
                new_updated_at = res.scalar_one()
                assert new_updated_at > old_ts, (
                    f"Expected {table_name}.updated_at ({new_updated_at}) to advance past {old_ts}"
                )
            await session.commit()
    finally:
        async with async_session_factory() as session:
            await session.execute(
                delete(LearningConceptORM).where(LearningConceptORM.concept_id == lc_key)
            )
            await session.execute(delete(UserORM).where(UserORM.id == user_id))
            await session.commit()
