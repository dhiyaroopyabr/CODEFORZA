"""
routers/judge_router.py — Code execution and submission judging.

Routes:
  POST /api/judge/run                          — run code (playground, no test cases)
  POST /api/judge/submit                       — submit against a problem's test cases
  GET  /api/judge/submissions                  — current user's submission history
  GET  /api/judge/submissions/{submission_id}  — single submission detail
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.dependencies import get_current_user
from app.executor import SUPPORTED_LANGUAGES, execute_code, judge_submission
from app.schemas import RunRequest, RunResult, SubmissionOut, SubmitRequest

router = APIRouter(prefix="/api/judge", tags=["judge"])


@router.post(
    "/run",
    response_model=RunResult,
    summary="Run code with optional stdin (playground mode)",
)
def run_code(
    req: RunRequest,
    current_user: models.User = Depends(get_current_user),
):
    """
    Execute arbitrary code without test cases.
    Useful for testing before submitting.
    Time limit is fixed at 5 seconds in playground mode.
    """
    result = execute_code(
        language=req.language,
        code=req.code,
        stdin_data=req.stdin,
        time_limit=5.0,
    )
    return RunResult(
        status=result.status,
        stdout=result.stdout,
        stderr=result.stderr,
        execution_time=result.execution_time,
    )


@router.post(
    "/submit",
    response_model=SubmissionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Submit code for judging against a problem's test cases",
)
def submit_code(
    req: SubmitRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Judge code against all test cases for the given problem.
    Returns immediately with the verdict (synchronous for local dev).
    Hidden test cases are never exposed — only the verdict is returned.
    """
    problem = db.query(models.Problem).filter(models.Problem.id == req.problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    # Collect ALL test cases (including hidden ones)
    test_pairs = [
        (tc.input_data, tc.expected_output)
        for tc in problem.test_cases
    ]

    # Create a "Running" submission record before executing
    submission = models.Submission(
        user_id=current_user.id,
        problem_id=req.problem_id,
        language=req.language,
        code=req.code,
        status="Running",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    # Execute and judge
    verdict = judge_submission(
        language=req.language,
        code=req.code,
        test_cases=test_pairs,
        time_limit=problem.time_limit,
    )

    # Update the submission with the final verdict
    submission.status = verdict["status"]
    submission.stderr = verdict.get("stderr", "")
    submission.execution_time = verdict["execution_time"]
    # Don't store stdout for submissions — only for /run (privacy + storage)
    db.commit()
    db.refresh(submission)
    return submission


@router.get(
    "/submissions",
    response_model=List[SubmissionOut],
    summary="Get your last 50 submissions",
)
def my_submissions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Submission)
        .filter(models.Submission.user_id == current_user.id)
        .order_by(models.Submission.created_at.desc())
        .limit(50)
        .all()
    )


@router.get(
    "/submissions/{submission_id}",
    response_model=SubmissionOut,
    summary="Get a specific submission (only your own)",
)
def get_submission(
    submission_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    submission = (
        db.query(models.Submission)
        .filter(
            models.Submission.id == submission_id,
            models.Submission.user_id == current_user.id,  # users can only see their own
        )
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission
