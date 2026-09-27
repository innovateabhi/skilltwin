from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.dependencies import get_current_user

from app.models.user import User
from app.models.trainee import Trainee
from app.models.assessment import Assessment
from app.models.assessment_question import AssessmentQuestion
from app.models.assessment_attempt import AssessmentAttempt
from app.models.assessment_answer import AssessmentAnswer
from app.models.trainee_competency import TraineeCompetency
from app.models.competency_history import CompetencyHistory
from app.models.skill_gap import SkillGap
from app.models.competency import Competency

from app.schemas.assessment import (
    AssessmentListItem,
    AssessmentStartResponse,
    AssessmentQuestionResponse,
    AssessmentSubmitRequest,
    AssessmentResultResponse,
    AssessmentHistoryResponse,
)

from app.services.competency_engine import (
    calculate_gap,
    calculate_severity,
    clamp_score,
)


router = APIRouter(
    prefix="/api/trainee/assessments",
    tags=["Trainee Assessments"],
)


def get_trainee(
    current_user: User,
    db: Session,
) -> Trainee:

    trainee = db.scalar(
        select(Trainee).where(
            Trainee.user_id == current_user.id
        )
    )

    if not trainee:
        raise HTTPException(
            status_code=404,
            detail="Trainee profile not found",
        )

    return trainee


@router.get(
    "",
    response_model=list[AssessmentListItem],
)
def list_assessments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    get_trainee(current_user, db)

    assessments = db.scalars(
        select(Assessment)
        .where(Assessment.is_active.is_(True))
        .options(
            joinedload(Assessment.questions),
            joinedload(Assessment.attempts),
        )
        .order_by(Assessment.created_at.desc())
    ).unique().all()

    result = []

    for assessment in assessments:

        completed_attempts = [
            attempt
            for attempt in assessment.attempts
            if attempt.status == "completed"
        ]

        result.append(
            AssessmentListItem(
                id=assessment.id,
                title=assessment.title,
                description=assessment.description,
                duration_minutes=assessment.duration_minutes,
                passing_score=assessment.passing_score,
                question_count=len(assessment.questions),
                completed_attempts=len(
                    completed_attempts
                ),
            )
        )

    return result


@router.get(
    "/history",
    response_model=list[AssessmentHistoryResponse],
)
def assessment_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    trainee = get_trainee(current_user, db)

    attempts = db.scalars(
        select(AssessmentAttempt)
        .where(
            AssessmentAttempt.trainee_id == trainee.id,
            AssessmentAttempt.status == "completed",
        )
        .options(
            joinedload(
                AssessmentAttempt.assessment
            )
        )
        .order_by(
            AssessmentAttempt.completed_at.desc()
        )
    ).all()

    return [
        AssessmentHistoryResponse(
            attempt_id=attempt.id,
            assessment_id=attempt.assessment_id,
            title=attempt.assessment.title,
            score=attempt.score,
            total_points=attempt.total_points,
            percentage=(
                round(
                    attempt.score
                    / attempt.total_points
                    * 100
                )
                if attempt.total_points
                else 0
            ),
            passed=(
                (
                    attempt.score
                    / attempt.total_points
                    * 100
                )
                >= attempt.assessment.passing_score
                if attempt.total_points
                else False
            ),
            completed_at=attempt.completed_at,
        )
        for attempt in attempts
    ]


@router.post(
    "/{assessment_id}/start",
    response_model=AssessmentStartResponse,
)
def start_assessment(
    assessment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    trainee = get_trainee(current_user, db)

    assessment = db.scalar(
        select(Assessment)
        .where(
            Assessment.id == assessment_id,
            Assessment.is_active.is_(True),
        )
        .options(
            joinedload(
                Assessment.questions
            ).joinedload(
                AssessmentQuestion.competency
            )
        )
    )

    if not assessment:
        raise HTTPException(
            status_code=404,
            detail="Assessment not found",
        )

    existing_attempt = db.scalar(
        select(AssessmentAttempt)
        .where(
            AssessmentAttempt.assessment_id
            == assessment.id,
            AssessmentAttempt.trainee_id
            == trainee.id,
            AssessmentAttempt.status
            == "in_progress",
        )
    )

    if existing_attempt:
        attempt = existing_attempt

    else:
        attempt = AssessmentAttempt(
            assessment_id=assessment.id,
            trainee_id=trainee.id,
            status="in_progress",
        )

        db.add(attempt)
        db.commit()
        db.refresh(attempt)

    questions = [
        AssessmentQuestionResponse(
            id=question.id,
            competency_id=question.competency_id,
            competency_name=question.competency.name,
            question_text=question.question_text,
            option_a=question.option_a,
            option_b=question.option_b,
            option_c=question.option_c,
            option_d=question.option_d,
            points=question.points,
        )
        for question in assessment.questions
    ]

    return AssessmentStartResponse(
        attempt_id=attempt.id,
        assessment_id=assessment.id,
        title=assessment.title,
        description=assessment.description,
        duration_minutes=assessment.duration_minutes,
        questions=questions,
    )


@router.post(
    "/attempts/{attempt_id}/submit",
    response_model=AssessmentResultResponse,
)
def submit_assessment(
    attempt_id: int,
    payload: AssessmentSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    trainee = get_trainee(current_user, db)

    attempt = db.scalar(
        select(AssessmentAttempt)
        .where(
            AssessmentAttempt.id == attempt_id,
            AssessmentAttempt.trainee_id == trainee.id,
        )
        .options(
            joinedload(
                AssessmentAttempt.assessment
            )
        )
    )

    if not attempt:
        raise HTTPException(
            status_code=404,
            detail="Assessment attempt not found",
        )

    if attempt.status == "completed":
        raise HTTPException(
            status_code=400,
            detail="This assessment has already been submitted",
        )

    questions = db.scalars(
        select(AssessmentQuestion)
        .where(
            AssessmentQuestion.assessment_id
            == attempt.assessment_id
        )
        .options(
            joinedload(
                AssessmentQuestion.competency
            )
        )
    ).all()

    question_map = {
        question.id: question
        for question in questions
    }

    if not payload.answers:
        raise HTTPException(
            status_code=400,
            detail="Please answer at least one question",
        )

    existing_answers = db.scalars(
        select(AssessmentAnswer)
        .where(
            AssessmentAnswer.attempt_id
            == attempt.id
        )
    ).all()

    if existing_answers:
        raise HTTPException(
            status_code=400,
            detail="Answers have already been submitted",
        )

    total_points = sum(
        question.points
        for question in questions
    )

    score = 0

    competency_points = defaultdict(int)
    competency_earned = defaultdict(int)

    for submitted in payload.answers:

        question = question_map.get(
            submitted.question_id
        )

        if not question:
            continue

        selected = (
            submitted.selected_option
            .strip()
            .upper()
        )

        if selected not in {
            "A",
            "B",
            "C",
            "D",
        }:
            continue

        correct = (
            selected
            == question.correct_option.upper()
        )

        points = (
            question.points
            if correct
            else 0
        )

        score += points

        competency_points[
            question.competency_id
        ] += question.points

        competency_earned[
            question.competency_id
        ] += points

        db.add(
            AssessmentAnswer(
                attempt_id=attempt.id,
                question_id=question.id,
                selected_option=selected,
                is_correct=correct,
                points_awarded=points,
            )
        )

    percentage = (
        round(
            score / total_points * 100
        )
        if total_points
        else 0
    )

    attempt.score = score
    attempt.total_points = total_points
    attempt.status = "completed"
    attempt.completed_at = datetime.utcnow()

    passed = (
        percentage
        >= attempt.assessment.passing_score
    )

    # ---------------------------------------------
    # Update competency intelligence
    # ---------------------------------------------

    for competency_id, possible_points in competency_points.items():

        earned_points = competency_earned[
            competency_id
        ]

        competency_score = (
            round(
                earned_points
                / possible_points
                * 100
            )
            if possible_points
            else 0
        )

        competency_score = clamp_score(
            competency_score
        )

        trainee_competency = db.scalar(
            select(TraineeCompetency)
            .where(
                TraineeCompetency.trainee_id
                == trainee.id,
                TraineeCompetency.competency_id
                == competency_id,
            )
        )

        competency = db.get(
            Competency,
            competency_id,
        )

        if not competency:
            continue

        previous_score = None

        if trainee_competency:

            previous_score = (
                trainee_competency.current_score
            )

            trainee_competency.current_score = (
                competency_score
            )

            trainee_competency.last_assessed_at = (
                datetime.utcnow()
            )

        else:

            trainee_competency = TraineeCompetency(
                trainee_id=trainee.id,
                competency_id=competency_id,
                current_score=competency_score,
                target_score=competency.target_default,
                last_assessed_at=datetime.utcnow(),
            )

            db.add(trainee_competency)

        db.add(
            CompetencyHistory(
                trainee_id=trainee.id,
                competency_id=competency_id,
                score=competency_score,
                previous_score=previous_score,
                source="assessment",
                reference_id=attempt.id,
            )
        )

    db.flush()

    # ---------------------------------------------
    # Recalculate skill gaps
    # ---------------------------------------------

    skills = db.scalars(
        select(
            TraineeCompetency
        )
        .where(
            TraineeCompetency.trainee_id
            == trainee.id
        )
        .options(
            joinedload(
                TraineeCompetency.competency
            )
        )
    ).all()

    skill_scores = defaultdict(list)

    for trainee_competency in skills:

        competency = (
            trainee_competency.competency
        )

        skill_scores[
            competency.skill_id
        ].append(
            (
                trainee_competency.current_score,
                trainee_competency.target_score,
            )
        )

    for skill_id, values in skill_scores.items():

        current_score = round(
            sum(
                current
                for current, _ in values
            )
            / len(values)
        )

        target_score = round(
            sum(
                target
                for _, target in values
            )
            / len(values)
        )

        gap_score = calculate_gap(
            current_score,
            target_score,
        )

        severity = calculate_severity(
            gap_score
        )

        existing_gap = db.scalar(
            select(SkillGap)
            .where(
                SkillGap.trainee_id
                == trainee.id,
                SkillGap.skill_id
                == skill_id,
            )
        )

        if existing_gap:

            existing_gap.current_score = (
                current_score
            )

            existing_gap.target_score = (
                target_score
            )

            existing_gap.gap_score = (
                gap_score
            )

            existing_gap.severity = (
                severity
            )

            existing_gap.status = (
                "closed"
                if gap_score <= 0
                else "open"
            )

        else:

            db.add(
                SkillGap(
                    trainee_id=trainee.id,
                    skill_id=skill_id,
                    current_score=current_score,
                    target_score=target_score,
                    gap_score=gap_score,
                    severity=severity,
                    status=(
                        "closed"
                        if gap_score <= 0
                        else "open"
                    ),
                )
            )

    db.commit()

    return AssessmentResultResponse(
        attempt_id=attempt.id,
        assessment_id=attempt.assessment_id,
        title=attempt.assessment.title,
        score=score,
        total_points=total_points,
        percentage=percentage,
        passed=passed,
        answered_questions=len(
            payload.answers
        ),
        total_questions=len(questions),
        completed_at=attempt.completed_at,
    )