from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.evaluation.application.dtos.dashboard_dtos import (
    DashboardSummaryResponseDTO,
)
from src.evaluation.application.dtos.intelligence import (
    GenerateProofResponseDTO,
    GenerateWeeklyReviewRequestDTO,
    MilestoneProofResponseDTO,
    SubmitProofRequestDTO,
    WeeklyReviewResponseDTO,
)
from src.evaluation.application.use_cases.dashboard_summary import (
    GetDashboardSummaryUseCase,
)
from src.evaluation.application.use_cases.intelligence import (
    EvaluationResourceNotFoundError,
    GenerateMilestoneProofUseCase,
    GenerateWeeklyReviewUseCase,
    GetLatestWeeklyReviewUseCase,
    SubmitMilestoneProofUseCase,
)
from src.evaluation.presentation.deps import (
    get_current_evaluation_learner_id,
    get_dashboard_summary_use_case,
    get_generate_proof_use_case,
    get_generate_weekly_review_use_case,
    get_latest_weekly_review_use_case,
    get_submit_proof_use_case,
)

router = APIRouter(prefix="/api/v1/evaluation", tags=["Evaluation & Analytics"])


@router.get("/status")
async def get_evaluation_context_status() -> dict[str, str]:
    """Bounded Context 4 health/status endpoint (UC-14..UC-17, UC-19)."""
    return {"context": "evaluation", "status": "ready"}


@router.get("/dashboard-summary", response_model=DashboardSummaryResponseDTO)
async def get_dashboard_summary(
    user_id: UUID = Depends(get_current_evaluation_learner_id),
    use_case: GetDashboardSummaryUseCase = Depends(get_dashboard_summary_use_case),
) -> DashboardSummaryResponseDTO:
    """Trả về tổng quan bảng điều khiển Dashboard cá nhân hóa của người học."""
    return await use_case.execute(user_id)


@router.post(
    "/milestones/{milestone_id}/proofs/generate-jobs",
    response_model=GenerateProofResponseDTO,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_milestone_proof(
    milestone_id: UUID,
    user_id: UUID = Depends(get_current_evaluation_learner_id),
    use_case: GenerateMilestoneProofUseCase = Depends(get_generate_proof_use_case),
) -> GenerateProofResponseDTO:
    try:
        return await use_case.execute(user_id, milestone_id)
    except EvaluationResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Milestone not found") from exc


@router.post(
    "/milestones/{milestone_id}/proofs/{proof_id}/submit",
    response_model=MilestoneProofResponseDTO,
)
async def submit_milestone_proof(
    milestone_id: UUID,
    proof_id: UUID,
    request: SubmitProofRequestDTO,
    user_id: UUID = Depends(get_current_evaluation_learner_id),
    use_case: SubmitMilestoneProofUseCase = Depends(get_submit_proof_use_case),
) -> MilestoneProofResponseDTO:
    try:
        return await use_case.execute(user_id, milestone_id, proof_id, request)
    except EvaluationResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Proof not found") from exc


@router.post(
    "/weekly-reviews/generate-jobs",
    response_model=WeeklyReviewResponseDTO,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_weekly_review(
    request: GenerateWeeklyReviewRequestDTO,
    user_id: UUID = Depends(get_current_evaluation_learner_id),
    use_case: GenerateWeeklyReviewUseCase = Depends(get_generate_weekly_review_use_case),
) -> WeeklyReviewResponseDTO:
    try:
        return await use_case.execute(user_id, request)
    except EvaluationResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Roadmap not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/weekly-reviews/latest", response_model=WeeklyReviewResponseDTO)
async def latest_weekly_review(
    user_id: UUID = Depends(get_current_evaluation_learner_id),
    use_case: GetLatestWeeklyReviewUseCase = Depends(get_latest_weekly_review_use_case),
) -> WeeklyReviewResponseDTO:
    try:
        return await use_case.execute(user_id)
    except EvaluationResourceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Weekly review not found") from exc
