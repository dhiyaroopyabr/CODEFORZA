"""
routers/problems_router.py — Problem CRUD.

Routes:
  GET    /api/problems/                           — list all problems (authenticated)
  POST   /api/problems/                           — create problem with test cases (admin)
  GET    /api/problems/{problem_id}               — problem detail + sample I/O (authenticated)
  DELETE /api/problems/{problem_id}               — delete problem + test cases (admin)
  POST   /api/problems/{problem_id}/test-cases    — add a test case to problem (admin)
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.schemas import (
    ProblemCreate,
    ProblemDetailOut,
    ProblemListOut,
    TestCaseCreate,
    TestCaseOut,
)

router = APIRouter(prefix="/api/problems", tags=["problems"])


@router.get(
    "/",
    response_model=List[ProblemListOut],
    summary="List all problems ordered by difficulty",
)
def list_problems(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Problem)
        .order_by(models.Problem.difficulty.asc())
        .all()
    )


@router.post(
    "/",
    response_model=ProblemDetailOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new problem (admin only)",
)
def create_problem(
    problem_in: ProblemCreate,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(require_admin),
):
    problem = models.Problem(
        title=problem_in.title,
        statement=problem_in.statement,
        input_format=problem_in.input_format,
        output_format=problem_in.output_format,
        constraints=problem_in.constraints,
        difficulty=problem_in.difficulty,
        time_limit=problem_in.time_limit,
        memory_limit=problem_in.memory_limit,
        created_by=current_admin.id,
    )
    db.add(problem)
    db.flush()  # get problem.id before adding test cases

    for tc_in in problem_in.test_cases:
        db.add(models.TestCase(
            problem_id=problem.id,
            input_data=tc_in.input_data,
            expected_output=tc_in.expected_output,
            is_sample=tc_in.is_sample,
        ))

    db.commit()
    db.refresh(problem)
    return _build_detail(problem)


@router.get(
    "/{problem_id}",
    response_model=ProblemDetailOut,
    summary="Get problem detail including sample test cases",
)
def get_problem(
    problem_id: UUID,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    problem = db.query(models.Problem).filter(models.Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return _build_detail(problem)


@router.delete(
    "/{problem_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a problem and all its test cases (admin only)",
)
def delete_problem(
    problem_id: UUID,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    problem = db.query(models.Problem).filter(models.Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    db.delete(problem)
    db.commit()


@router.post(
    "/{problem_id}/test-cases",
    response_model=TestCaseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a test case to an existing problem (admin only)",
)
def add_test_case(
    problem_id: UUID,
    tc_in: TestCaseCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_admin),
):
    if not db.query(models.Problem).filter(models.Problem.id == problem_id).first():
        raise HTTPException(status_code=404, detail="Problem not found")

    tc = models.TestCase(
        problem_id=problem_id,
        input_data=tc_in.input_data,
        expected_output=tc_in.expected_output,
        is_sample=tc_in.is_sample,
    )
    db.add(tc)
    db.commit()
    db.refresh(tc)
    return tc


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_detail(problem: models.Problem) -> dict:
    """
    Build the ProblemDetailOut response.
    Only sample test cases are exposed to contestants.
    """
    sample_tcs = [
        TestCaseOut.model_validate(tc)
        for tc in problem.test_cases
        if tc.is_sample
    ]
    base = ProblemDetailOut.model_validate(problem)
    base.sample_test_cases = sample_tcs
    return base
