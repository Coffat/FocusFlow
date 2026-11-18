import asyncio
import logging
from datetime import UTC, date, datetime

from sqlalchemy import select

from src.account.infrastructure.adapters.quota_facade_adapter import QuotaFacadeAdapter
from src.account.infrastructure.orm.user_orm import AIQuotaORM, AIUsageLogORM, UserORM
from src.planning.application.dtos.planning_dtos import (
    ClarificationAnswerItem,
    ClarificationQuestionsResponse,
    parse_clarification_context,
)
from src.planning.application.use_cases.clarification_use_cases import (
    GenerateClarificationQuestionsUseCase,
    SubmitClarificationAnswersUseCase,
)
from src.planning.application.use_cases.create_goal_and_roadmap import (
    CreateGoalAndRoadmapUseCase,
)
from src.planning.application.use_cases.milestone_use_cases import (
    ExecuteMilestoneGenerationUseCase,
    InitiateMilestoneGenerationUseCase,
)
from src.planning.infrastructure.repositories.knowledge_source_repository import (
    SqlAlchemyKnowledgeSourceRepository,
)
from src.planning.infrastructure.repositories.planning_repositories import (
    SqlAlchemyGoalRepository,
    SqlAlchemyMilestoneRepository,
    SqlAlchemyRoadmapRepository,
)
from src.planning.infrastructure.repositories.sqlalchemy_knowledge_base_repository import (
    SqlAlchemyKnowledgeBaseRepository,
)
from src.planning.infrastructure.sse import default_redis_sse_job_store
from src.shared_kernel.infrastructure.database.session import get_async_session
from src.shared_kernel.infrastructure.database.sqlalchemy_uow import (
    SqlAlchemyUnitOfWork,
)
from src.shared_kernel.infrastructure.external_ai.litellm_adapter import LiteLLMAdapter
from src.shared_kernel.infrastructure.workflow.repository import (
    SqlAlchemyWorkflowRepository,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("experiment")


async def run_experiment():
    print("=" * 80)
    print("THỰC NGHIỆM: NÂNG CẤP PHỎNG VẤN CHẨN ĐOÁN BƯỚC 2 & TỰ ĐỘNG SINH CỘT MỐC BƯỚC 3")
    print("=" * 80)

    now = datetime.now(UTC)

    async for session in get_async_session():
        # 1. Chuẩn bị User người học và hạn ngạch AI
        user_res = await session.execute(select(UserORM).limit(1))
        user = user_res.scalar_one_or_none()
        if not user:
            user = UserORM(
                email="learner_test_aws@focusflow.vn",
                full_name="AWS Learner",
                role="LEARNER",
                tier="FREE",
            )
            session.add(user)
            await session.flush()

        user_id = user.id
        print(f"\n[1] Người học thử nghiệm: user_id={user_id}, email={user.email}")

        # Đảm bảo hạn ngạch đủ lớn cho bài test
        quota_res = await session.execute(select(AIQuotaORM).where(AIQuotaORM.user_id == user_id))
        quota = quota_res.scalar_one_or_none()
        if not quota:
            quota = AIQuotaORM(
                user_id=user_id,
                monthly_limit=1000,
                used_calls=0,
                reserved_calls=0,
                free_credits_remaining=500,
                paid_credits_remaining=500,
                tokens_consumed=0,
            )
            session.add(quota)
        else:
            quota.free_credits_remaining = max(100, quota.free_credits_remaining)
            quota.reserved_calls = 0
        await session.commit()

        # Khởi tạo adapters & use cases
        uow = SqlAlchemyUnitOfWork(session)
        goal_repo = SqlAlchemyGoalRepository(session)
        roadmap_repo = SqlAlchemyRoadmapRepository(session)
        milestone_repo = SqlAlchemyMilestoneRepository(session)
        quota_facade = QuotaFacadeAdapter(session)
        llm_provider = LiteLLMAdapter()
        workflow_repo = SqlAlchemyWorkflowRepository(session)
        kb_repo = SqlAlchemyKnowledgeBaseRepository(session)
        ks_repo = SqlAlchemyKnowledgeSourceRepository(session)

        print(f"    - LLM Provider: {llm_provider.__class__.__name__}")
        print(f"    - Model Identifier: {llm_provider.model_identifier}")

        # 2. Tạo Goal & Roadmap Bước 1
        print("\n[2] Khởi tạo Mục tiêu học tập (Bước 1):")
        goal_title = "Luyện thi AWS Solutions Architect Associate (SAA-C03)"
        raw_desc = (
            "Mục tiêu thi đạt chứng chỉ AWS SAA-C03 trong 3 tháng. "
            "Đã có kiến thức cơ bản về Linux và mạng máy tính, cần tập trung vào các dịch vụ "
            "compute (EC2, ECS, Lambda), storage (S3, EFS), networking (VPC, Route53) và security (IAM, KMS)."
        )
        target_date = date(2027, 2, 28)

        create_uc = CreateGoalAndRoadmapUseCase(
            goal_repo=goal_repo,
            roadmap_repo=roadmap_repo,
            uow=uow,
        )
        created_res = await create_uc.execute(
            user_id=user_id,
            title=goal_title,
            description=raw_desc,
            prior_knowledge_level="BEGINNER",
            target_date=target_date,
            now=now,
        )
        created_goal = created_res.goal
        created_roadmap = created_res.roadmap
        print(f"    ✓ Đã tạo Goal ID: {created_goal.id}")
        print(f"    ✓ Đã tạo Roadmap ID: {created_roadmap.id}")
        print(f"    ✓ Tiêu đề: {created_goal.title}")

        # 3. Thực nghiệm a) Sinh câu hỏi chẩn đoán linh hoạt Bước 2
        print("\n[3] Thực nghiệm a) Sinh bộ câu hỏi phỏng vấn chẩn đoán Bước 2 qua AI:")
        gen_clar_uc = GenerateClarificationQuestionsUseCase(
            goal_repo=goal_repo,
            quota_facade=quota_facade,
            llm_provider=llm_provider,
            uow=uow,
            workflow_repo=workflow_repo,
        )
        clar_response: ClarificationQuestionsResponse = await gen_clar_uc.execute(
            user_id=user_id,
            goal_id=created_goal.id,
            now=now,
        )

        questions = clar_response.questions
        print(f"    ✓ Số lượng câu hỏi được sinh: {len(questions)} (Yêu cầu: 3 - 5 câu)")
        assert 3 <= len(questions) <= 5, f"Số câu hỏi phải từ 3 đến 5, thực tế: {len(questions)}"

        for i, q in enumerate(questions, 1):
            print(f"\n    --- Câu hỏi #{i} (ID: {q.id}) ---")
            print(f"        * Nội dung: {q.question}")
            print(f"        * Loại: {q.question_type}")
            print(f"        * Chiều chẩn đoán: {q.diagnostic_dimension}")
            print(f"        * Mục đích: {q.question_purpose}")
            print(f"        * Số options: {len(q.options)}")
            for o_idx, opt in enumerate(q.options, 1):
                print(f"          [{o_idx}] {opt}")

        # Kiểm tra sự hiện diện của câu hỏi trắc nghiệm và phương án linh hoạt
        choice_questions = [
            q for q in questions if q.question_type in ("single_choice", "multiple_choice")
        ]
        print(
            f"\n    ✓ Số câu hỏi trắc nghiệm (single/multiple choice): {len(choice_questions)}/{len(questions)}"
        )
        assert len(choice_questions) >= 1, "Phải có ít nhất 1 câu hỏi trắc nghiệm!"

        # 4. Thực nghiệm b) Giả lập submit câu trả lời phỏng vấn Bước 2
        print("\n[4] Thực nghiệm b) Giả lập submit câu trả lời phỏng vấn Bước 2:")
        answers_payload: list[ClarificationAnswerItem] = []
        for idx, q in enumerate(questions, 1):
            qid = q.question_id or q.id
            if q.question_type == "multiple_choice":
                # Chọn nhiều options (dạng list -> tự normalize thành chuỗi phân tách bằng phẩy)
                chosen = (
                    [q.options[0], q.options[min(1, len(q.options) - 1)]]
                    if q.options
                    else ["Compute", "Storage"]
                )
                answers_payload.append(
                    ClarificationAnswerItem(
                        question_id=qid,
                        question_text=q.question,
                        answer=chosen,  # type: ignore[arg-type]
                    )
                )
            elif q.question_type == "single_choice":
                # Chọn 1 option
                chosen = q.options[0] if q.options else "Đã tự học cú pháp cơ bản"
                answers_payload.append(
                    ClarificationAnswerItem(
                        question_id=qid,
                        question_text=q.question,
                        answer=chosen,
                    )
                )
            else:
                # Text input
                answers_payload.append(
                    ClarificationAnswerItem(
                        question_id=qid,
                        question_text=q.question,
                        answer="Đạt chứng chỉ AWS Solutions Architect Associate với điểm số trên 800 và xây dựng được kiến trúc Multi-Tier trên AWS.",
                    )
                )

        submit_uc = SubmitClarificationAnswersUseCase(
            goal_repo=goal_repo,
            uow=uow,
        )
        updated_goal = await submit_uc.execute(
            user_id=user_id,
            goal_id=created_goal.id,
            answers=answers_payload,
            now=now,
        )
        print("    ✓ Submit câu trả lời thành công.")
        clar_ctx = parse_clarification_context(updated_goal.clarification_context)
        print(f"    ✓ Trạng thái Clarification Context: {clar_ctx.status}")
        print(f"    ✓ Số câu trả lời đã lưu: {len(clar_ctx.answers)}")
        for a in clar_ctx.answers:
            print(f"        * [{a['question_id']}] -> {a['answer']}")

        # 5. Thực nghiệm c) Kích hoạt sinh Milestones Bước 3 với cấu hình gemini-3.5-flash
        print("\n[5] Thực nghiệm c) Kích hoạt sinh Milestones Bước 3 qua AI (gemini-3.5-flash):")
        executor = ExecuteMilestoneGenerationUseCase(
            goal_repo=goal_repo,
            roadmap_repo=roadmap_repo,
            milestone_repo=milestone_repo,
            quota_facade=quota_facade,
            llm_provider=llm_provider,
            sse_job_store=default_redis_sse_job_store,
            uow=uow,
            knowledge_base=kb_repo,
            knowledge_source_repo=ks_repo,
            workflow_repo=workflow_repo,
        )
        initiate_uc = InitiateMilestoneGenerationUseCase(
            roadmap_repo=roadmap_repo,
            quota_facade=quota_facade,
            sse_job_store=default_redis_sse_job_store,
            uow=uow,
            executor=executor,
        )

        ticket = await initiate_uc.execute(
            user_id=user_id,
            roadmap_id=created_roadmap.id,
            run_inline=True,
        )
        print(f"    ✓ Ticket sinh Milestones: job_id={ticket.job_id}, status={ticket.status}")

        # Lấy danh sách cột mốc đã sinh từ database
        milestones = await milestone_repo.list_by_roadmap_id(created_roadmap.id)
        print(f"    ✓ Tổng số Cột mốc (Milestones) đã sinh thành công: {len(milestones)}")
        assert len(milestones) >= 3, (
            f"Phải có ít nhất 3 cột mốc được sinh, thực tế: {len(milestones)}"
        )

        total_effort_minutes = 0
        for m in sorted(milestones, key=lambda x: x.sequence_order):
            effort = getattr(m, "estimated_effort_minutes", 0) or 0
            total_effort_minutes += effort
            print(f"\n    --- Cột mốc #{m.sequence_order}: {m.title} ---")
            print(f"        * Trạng thái: {m.status.value}")
            print(f"        * Mô tả: {m.description}")
            if hasattr(m, "learning_outcomes") and m.learning_outcomes:
                print(f"        * Chuẩn đầu ra: {', '.join(m.learning_outcomes)}")
            if hasattr(m, "completion_criteria") and m.completion_criteria:
                print(f"        * Tiêu chí hoàn thành: {m.completion_criteria}")

        # Kiểm tra AI Usage Log xem model_name có đúng là gemini-3.5-flash không
        log_res = await session.execute(
            select(AIUsageLogORM)
            .where(AIUsageLogORM.user_id == user_id)
            .order_by(AIUsageLogORM.created_at.desc())
            .limit(3)
        )
        recent_logs = log_res.scalars().all()
        print("\n[6] Kiểm tra AI Usage Logs (Ghi nhận Model Name & Token):")
        for log in recent_logs:
            print(
                f"    ✓ Action: {log.action_type} | Model: {log.model_name} | "
                f"Tokens: {log.total_tokens} (prompt={log.prompt_tokens}, completion={log.completion_tokens}) | "
                f"Status: {log.status}"
            )
            assert "gemini-3.5-flash" in log.model_name, (
                f"Model name phải là gemini-3.5-flash, thực tế: {log.model_name}"
            )

        break

    print("\n" + "=" * 80)
    print("HOÀN TẤT THỰC NGHIỆM THÀNH CÔNG: MỌI TIÊU CHÍ ĐỀU ĐẠT CHUẨN!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_experiment())
