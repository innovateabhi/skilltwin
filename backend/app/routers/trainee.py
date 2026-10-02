from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user

from app.models.user import User
from app.models.trainee import Trainee
from app.models.trainee_competency import TraineeCompetency
from app.models.competency import Competency
from app.models.competency_history import CompetencyHistory
from app.models.skill_gap import SkillGap
from app.models.skill import Skill
from app.models.skill_category import SkillCategory
from app.models.domain import Domain

from app.models.course_enrollment import CourseEnrollment
from app.models.course import Course
from app.models.course_category import CourseCategory
from app.models.course_domain import CourseDomain
from app.models.course_module import CourseModule
from app.models.course_lesson import CourseLesson

from app.schemas.trainee import (
    DashboardStats,
    TraineeCompetencyResponse,
    TraineeDashboardResponse,
    TraineeGapResponse,
    TraineeHistoryResponse,
    TraineeProfileResponse,
    TraineeSkillResponse,
)


router = APIRouter(
    prefix="/api/trainee",
    tags=["Trainee"],
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trainee profile not found",
        )

    return trainee


@router.get(
    "/profile",
    response_model=TraineeProfileResponse,
)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_trainee(current_user, db)


@router.get(
    "/competencies",
    response_model=list[TraineeCompetencyResponse],
)
def get_competencies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trainee = get_trainee(current_user, db)

    rows = db.execute(
        select(
            TraineeCompetency,
            Competency,
            Skill,
        )
        .join(
            Competency,
            TraineeCompetency.competency_id == Competency.id,
        )
        .join(
            Skill,
            Competency.skill_id == Skill.id,
        )
        .where(
            TraineeCompetency.trainee_id == trainee.id
        )
        .order_by(
            TraineeCompetency.current_score.desc()
        )
    ).all()

    result = []

    for trainee_competency, competency, skill in rows:
        gap = max(
            trainee_competency.target_score
            - trainee_competency.current_score,
            0,
        )

        result.append(
            TraineeCompetencyResponse(
                id=trainee_competency.id,
                competency_id=competency.id,
                competency_name=competency.name,
                competency_description=competency.description,
                skill_id=skill.id,
                skill_name=skill.name,
                current_score=trainee_competency.current_score,
                target_score=trainee_competency.target_score,
                gap_score=gap,
                last_assessed_at=trainee_competency.last_assessed_at,
            )
        )

    return result


@router.get(
    "/skills",
    response_model=list[TraineeSkillResponse],
)
def get_skills(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trainee = get_trainee(current_user, db)

    rows = db.execute(
        select(
            Skill,
            SkillCategory,
            Domain,
            func.avg(TraineeCompetency.current_score),
            func.max(TraineeCompetency.target_score),
            func.count(TraineeCompetency.id),
        )
        .join(
            Competency,
            Competency.skill_id == Skill.id,
        )
        .join(
            TraineeCompetency,
            TraineeCompetency.competency_id == Competency.id,
        )
        .join(
            SkillCategory,
            Skill.category_id == SkillCategory.id,
        )
        .join(
            Domain,
            SkillCategory.domain_id == Domain.id,
        )
        .where(
            TraineeCompetency.trainee_id == trainee.id
        )
        .group_by(
            Skill.id,
            SkillCategory.id,
            Domain.id,
        )
        .order_by(
            Skill.name
        )
    ).all()

    result = []

    for (
        skill,
        category,
        domain,
        average_score,
        target_score,
        competency_count,
    ) in rows:
        current = round(average_score or 0)
        target = int(target_score or 80)

        result.append(
            TraineeSkillResponse(
                skill_id=skill.id,
                skill_name=skill.name,
                skill_slug=skill.slug,
                category_id=category.id,
                category_name=category.name,
                domain_id=domain.id,
                domain_name=domain.name,
                current_score=current,
                target_score=target,
                gap_score=max(target - current, 0),
                competency_count=competency_count,
            )
        )

    return result


@router.get(
    "/gaps",
    response_model=list[TraineeGapResponse],
)
def get_gaps(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trainee = get_trainee(current_user, db)

    rows = db.execute(
        select(
            SkillGap,
            Skill,
        )
        .join(
            Skill,
            SkillGap.skill_id == Skill.id,
        )
        .where(
            SkillGap.trainee_id == trainee.id,
            SkillGap.status == "open",
        )
        .order_by(
            SkillGap.gap_score.desc()
        )
    ).all()

    return [
        TraineeGapResponse(
            id=gap.id,
            skill_id=skill.id,
            skill_name=skill.name,
            skill_slug=skill.slug,
            current_score=gap.current_score,
            target_score=gap.target_score,
            gap_score=gap.gap_score,
            severity=gap.severity,
            status=gap.status,
            calculated_at=gap.calculated_at,
        )
        for gap, skill in rows
    ]


@router.get(
    "/history",
    response_model=list[TraineeHistoryResponse],
)
def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trainee = get_trainee(current_user, db)

    rows = db.execute(
        select(
            CompetencyHistory,
            Competency,
        )
        .join(
            Competency,
            CompetencyHistory.competency_id == Competency.id,
        )
        .where(
            CompetencyHistory.trainee_id == trainee.id
        )
        .order_by(
            CompetencyHistory.recorded_at.desc()
        )
        .limit(50)
    ).all()

    return [
        TraineeHistoryResponse(
            id=history.id,
            competency_id=competency.id,
            competency_name=competency.name,
            score=history.score,
            previous_score=history.previous_score,
            improvement=(
                history.score - history.previous_score
                if history.previous_score is not None
                else 0
            ),
            source=history.source,
            reference_id=history.reference_id,
            recorded_at=history.recorded_at,
        )
        for history, competency in rows
    ]


@router.get(
    "/dashboard",
    response_model=TraineeDashboardResponse,
)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trainee = get_trainee(current_user, db)

    # -----------------------------
    # Competencies
    # -----------------------------

    competency_rows = db.execute(
        select(
            TraineeCompetency,
            Competency,
            Skill,
        )
        .join(
            Competency,
            TraineeCompetency.competency_id == Competency.id,
        )
        .join(
            Skill,
            Competency.skill_id == Skill.id,
        )
        .where(
            TraineeCompetency.trainee_id == trainee.id
        )
        .order_by(
            TraineeCompetency.current_score.desc()
        )
    ).all()

    competencies = []

    for trainee_competency, competency, skill in competency_rows:
        gap = max(
            trainee_competency.target_score
            - trainee_competency.current_score,
            0,
        )

        competencies.append(
            TraineeCompetencyResponse(
                id=trainee_competency.id,
                competency_id=competency.id,
                competency_name=competency.name,
                competency_description=competency.description,
                skill_id=skill.id,
                skill_name=skill.name,
                current_score=trainee_competency.current_score,
                target_score=trainee_competency.target_score,
                gap_score=gap,
                last_assessed_at=trainee_competency.last_assessed_at,
            )
        )

    # -----------------------------
    # Skill gaps
    # -----------------------------

    gap_rows = db.execute(
        select(
            SkillGap,
            Skill,
        )
        .join(
            Skill,
            SkillGap.skill_id == Skill.id,
        )
        .where(
            SkillGap.trainee_id == trainee.id,
            SkillGap.status == "open",
        )
        .order_by(
            SkillGap.gap_score.desc()
        )
    ).all()

    gaps = [
        TraineeGapResponse(
            id=gap.id,
            skill_id=skill.id,
            skill_name=skill.name,
            skill_slug=skill.slug,
            current_score=gap.current_score,
            target_score=gap.target_score,
            gap_score=gap.gap_score,
            severity=gap.severity,
            status=gap.status,
            calculated_at=gap.calculated_at,
        )
        for gap, skill in gap_rows
    ]

    # -----------------------------
    # Recent history
    # -----------------------------

    history_rows = db.execute(
        select(
            CompetencyHistory,
            Competency,
        )
        .join(
            Competency,
            CompetencyHistory.competency_id == Competency.id,
        )
        .where(
            CompetencyHistory.trainee_id == trainee.id
        )
        .order_by(
            CompetencyHistory.recorded_at.desc()
        )
        .limit(5)
    ).all()

    recent_history = [
        TraineeHistoryResponse(
            id=history.id,
            competency_id=competency.id,
            competency_name=competency.name,
            score=history.score,
            previous_score=history.previous_score,
            improvement=(
                history.score - history.previous_score
                if history.previous_score is not None
                else 0
            ),
            source=history.source,
            reference_id=history.reference_id,
            recorded_at=history.recorded_at,
        )
        for history, competency in history_rows
    ]

    # -----------------------------
    # Statistics
    # -----------------------------

    total_competencies = len(competencies)

    assessed_competencies = sum(
        1
        for item in competencies
        if item.last_assessed_at is not None
    )

    average_score = round(
        sum(item.current_score for item in competencies)
        / total_competencies
    ) if total_competencies else 0

    skills_with_gaps = len(gaps)

    critical_gaps = sum(
        1
        for gap in gaps
        if gap.severity == "critical"
    )

    learning_progress = (
        round(
            (average_score / 80) * 100
        )
        if average_score
        else 0
    )

    learning_progress = min(
        max(learning_progress, 0),
        100,
    )

    stats = DashboardStats(
        total_competencies=total_competencies,
        assessed_competencies=assessed_competencies,
        average_score=average_score,
        skills_with_gaps=skills_with_gaps,
        critical_gaps=critical_gaps,
        learning_progress=learning_progress,
    )

    return TraineeDashboardResponse(
        profile=trainee,
        stats=stats,
        competencies=competencies,
        gaps=gaps,
        recent_history=recent_history,
    )


# ============================================================
# MY COURSES
# ============================================================

@router.get(
    "/my-courses",
)
def get_my_courses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trainee = get_trainee(current_user, db)

    rows = db.execute(
        select(
            CourseEnrollment,
            Course,
            CourseCategory,
            CourseDomain,
        )
        .join(
            Course,
            CourseEnrollment.course_id == Course.id,
        )
        .outerjoin(
            CourseCategory,
            Course.category_id == CourseCategory.id,
        )
        .outerjoin(
            CourseDomain,
            CourseCategory.domain_id == CourseDomain.id,
        )
        .where(
            CourseEnrollment.trainee_id == trainee.id,

            # Allow both paid courses and free/demo courses.
            CourseEnrollment.payment_status.in_(
                ["paid", "not_required"]
            ),

            # "active" is the current status used by the
            # demo/default enrollment records.
            CourseEnrollment.status.in_(
                [
                    "active",
                    "in_progress",
                    "completed",
                ]
            ),

            Course.is_active.is_(True),
        )
        .order_by(
            CourseEnrollment.last_accessed_at.desc(),
            CourseEnrollment.enrolled_at.desc(),
        )
    ).all()

    result = []

    for (
        enrollment,
        course,
        category,
        domain,
    ) in rows:

        # ----------------------------------------------------
        # Determine current enrollment progress
        # ----------------------------------------------------

        if enrollment.status == "completed":
            progress_status = "completed"

        elif enrollment.status in [
            "active",
            "in_progress",
        ]:
            if enrollment.last_accessed_at:
                progress_status = "in_progress"
            else:
                progress_status = "not_started"

        else:
            progress_status = "not_started"

        # ----------------------------------------------------
        # Load published lessons for this course
        # ----------------------------------------------------

        lessons = db.scalars(
            select(CourseLesson)
            .join(
                CourseModule,
                CourseLesson.module_id == CourseModule.id,
            )
            .where(
                CourseModule.course_id == course.id,
                CourseLesson.is_published.is_(True),
            )
            .order_by(
                CourseLesson.order_index.asc(),
            )
        ).all()

        # ----------------------------------------------------
        # Determine delivery type
        #
        # If the course has at least one live lesson,
        # it is treated as a live course.
        #
        # Otherwise it is treated as recorded/self-paced.
        # ----------------------------------------------------

        has_live_lessons = any(
            lesson.lesson_type == "live"
            for lesson in lessons
        )

        delivery_type = (
            "live"
            if has_live_lessons
            else "recorded"
        )

        # ----------------------------------------------------
        # Find next upcoming live class
        # ----------------------------------------------------

        next_live_class = None

        if delivery_type == "live":

            now = datetime.utcnow()

            upcoming_live_lessons = [
                lesson
                for lesson in lessons
                if (
                    lesson.lesson_type == "live"
                    and lesson.scheduled_at is not None
                    and lesson.scheduled_at >= now
                )
            ]

            if upcoming_live_lessons:

                next_lesson = min(
                    upcoming_live_lessons,
                    key=lambda lesson: lesson.scheduled_at,
                )

                next_live_class = {
                    "lesson_id": next_lesson.id,
                    "title": next_lesson.title,
                    "description": next_lesson.description,
                    "scheduled_at": next_lesson.scheduled_at,
                    "duration_minutes": next_lesson.duration_minutes,
                    "meeting_url": next_lesson.meeting_url,
                }

        # ----------------------------------------------------
        # Return course
        # ----------------------------------------------------

        result.append(
            {
                "enrollment_id": enrollment.id,

                "course_id": course.id,
                "title": course.title,
                "slug": course.slug,
                "description": course.description,

                "instructor_name": course.instructor_name,
                "thumbnail_url": course.thumbnail_url,

                "level": course.level,
                "duration_hours": course.duration_hours,

                "currency": course.currency,

                "domain_id": (
                    domain.id
                    if domain
                    else None
                ),

                "domain_name": (
                    domain.name
                    if domain
                    else None
                ),

                "category_id": (
                    category.id
                    if category
                    else None
                ),

                "category_name": (
                    category.name
                    if category
                    else None
                ),

                "enrollment_status": enrollment.status,
                "payment_status": enrollment.payment_status,
                "progress_status": progress_status,

                # Course delivery information
                "delivery_type": delivery_type,

                # Upcoming live-class information
                "next_live_class": next_live_class,

                "enrolled_at": enrollment.enrolled_at,
                "last_accessed_at": enrollment.last_accessed_at,
                "completed_at": enrollment.completed_at,
            }
        )

    return result


# ============================================================
# PRESENTATION / DEMO DATA
# ============================================================

DEMO_OPPORTUNITIES = [
    {
        "id": 1,
        "title": "Cloud Engineer Intern",
        "company_name": "CloudNova Technologies",
        "company_logo": None,
        "location": "Bengaluru, India",
        "type": "Internship",
        "experience_level": "Fresher",
        "description": "Work with AWS infrastructure, Linux systems, CI/CD pipelines and cloud deployment automation.",
        "skills": ["AWS", "Linux", "Docker", "Git", "Python"],
        "match_percentage": 88,
        "application_url": "#",
    },
    {
        "id": 2,
        "title": "DevOps Intern",
        "company_name": "TechSphere Labs",
        "company_logo": None,
        "location": "Remote",
        "type": "Internship",
        "experience_level": "Fresher",
        "description": "Assist with CI/CD automation, Docker containers, monitoring and cloud infrastructure.",
        "skills": ["Docker", "Git", "Linux", "CI/CD", "AWS"],
        "match_percentage": 84,
        "application_url": "#",
    },
    {
        "id": 3,
        "title": "Python Backend Developer",
        "company_name": "Nexora Systems",
        "company_logo": None,
        "location": "Hyderabad, India",
        "type": "Full-time",
        "experience_level": "Entry Level",
        "description": "Build REST APIs and backend services using Python and modern web technologies.",
        "skills": ["Python", "FastAPI", "REST API", "SQL", "Git"],
        "match_percentage": 79,
        "application_url": "#",
    },
    {
        "id": 4,
        "title": "Cybersecurity Intern",
        "company_name": "SecureGrid Technologies",
        "company_logo": None,
        "location": "Pune, India",
        "type": "Internship",
        "experience_level": "Fresher",
        "description": "Support security monitoring, vulnerability assessment and incident analysis.",
        "skills": ["Linux", "Networking", "Cybersecurity", "SIEM", "Python"],
        "match_percentage": 76,
        "application_url": "#",
    },
    {
        "id": 5,
        "title": "Junior Cloud Operations Engineer",
        "company_name": "InfraStack",
        "company_logo": None,
        "location": "Mumbai, India",
        "type": "Full-time",
        "experience_level": "Entry Level",
        "description": "Monitor cloud infrastructure and support deployment, networking and operational automation.",
        "skills": ["AWS", "Linux", "Networking", "CloudWatch", "Python"],
        "match_percentage": 82,
        "application_url": "#",
    },
    {
        "id": 6,
        "title": "AI/ML Engineering Intern",
        "company_name": "CognitiveWorks",
        "company_logo": None,
        "location": "Remote",
        "type": "Internship",
        "experience_level": "Fresher",
        "description": "Assist in developing machine-learning pipelines and AI-powered applications.",
        "skills": ["Python", "Machine Learning", "AI", "SQL", "Git"],
        "match_percentage": 71,
        "application_url": "#",
    },
    {
        "id": 7,
        "title": "Full Stack Developer Intern",
        "company_name": "PixelForge Technologies",
        "company_logo": None,
        "location": "Kolkata, India",
        "type": "Internship",
        "experience_level": "Fresher",
        "description": "Develop modern web applications using frontend and backend technologies.",
        "skills": ["React", "JavaScript", "Python", "SQL", "Git"],
        "match_percentage": 74,
        "application_url": "#",
    },
    {
        "id": 8,
        "title": "Cloud Support Associate",
        "company_name": "OrbitCloud",
        "company_logo": None,
        "location": "Noida, India",
        "type": "Full-time",
        "experience_level": "Entry Level",
        "description": "Provide technical support for cloud infrastructure, deployments and Linux-based systems.",
        "skills": ["AWS", "Linux", "Networking", "Troubleshooting"],
        "match_percentage": 86,
        "application_url": "#",
    },
]


@router.get("/opportunities")
def get_demo_opportunities(
    current_user: User = Depends(get_current_user),
):
    """
    Presentation/demo opportunities.

    Replace this endpoint later with the real
    opportunity recommendation engine.
    """

    return DEMO_OPPORTUNITIES


@router.get("/career-readiness")
def get_demo_career_readiness(
    current_user: User = Depends(get_current_user),
):
    """
    Presentation/demo career-readiness profile.

    Replace this later with the real competency/AI
    career-readiness calculation.
    """

    return {
        "readiness_percentage": 72,
        "target_role": "Cloud / DevOps Engineer",

        "skills_ready": [
            "Linux",
            "Python",
            "AWS",
            "Git",
            "Networking",
        ],

        "skill_gaps": [
            "Docker",
            "Kubernetes",
            "Terraform",
            "CI/CD",
        ],

        "courses_completed": 3,
        "certificates": 2,

        "strengths": [
            {
                "name": "Linux & System Administration",
                "score": 82,
            },
            {
                "name": "Python",
                "score": 78,
            },
            {
                "name": "AWS Cloud",
                "score": 75,
            },
            {
                "name": "Git & Version Control",
                "score": 81,
            },
        ],

        "gaps": [
            {
                "name": "Kubernetes",
                "current_score": 42,
                "target_score": 80,
                "gap_score": 38,
            },
            {
                "name": "Terraform",
                "current_score": 38,
                "target_score": 75,
                "gap_score": 37,
            },
            {
                "name": "CI/CD",
                "current_score": 55,
                "target_score": 80,
                "gap_score": 25,
            },
        ],

        "recommended_actions": [
            {
                "title": "Complete a Docker & Kubernetes learning path",
                "description": "Build practical container orchestration skills for cloud engineering roles.",
                "priority": "High",
            },
            {
                "title": "Build an automated CI/CD pipeline",
                "description": "Deploy a real application using GitHub Actions, Docker and AWS.",
                "priority": "High",
            },
            {
                "title": "Learn Terraform fundamentals",
                "description": "Practice Infrastructure as Code by provisioning AWS resources.",
                "priority": "Medium",
            },
            {
                "title": "Apply to matched cloud opportunities",
                "description": "Your current profile matches several entry-level cloud and DevOps roles.",
                "priority": "Medium",
            },
        ],
    }


@router.get("/skill-gap-analysis")
def get_skill_gap_analysis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trainee = (
        db.query(Trainee)
        .filter(Trainee.user_id == current_user.id)
        .first()
    )

    if not trainee:
        raise HTTPException(
            status_code=404,
            detail="Trainee profile not found.",
        )

    competency_records = (
        db.query(TraineeCompetency)
        .filter(
            TraineeCompetency.trainee_id == trainee.id
        )
        .all()
    )

    skill_gap_records = (
        db.query(SkillGap)
        .filter(
            SkillGap.trainee_id == trainee.id
        )
        .all()
    )

    items = []

    # ---------------------------------------------------------
    # Competency based gaps
    # ---------------------------------------------------------

    for record in competency_records:
        competency = record.competency

        if not competency:
            continue

        current_score = float(
            record.current_score or 0
        )

        target_score = float(
            record.target_score or 80
        )

        gap_score = max(
            0,
            target_score - current_score
        )

        if gap_score >= 35:
            priority = "Critical"
            status = "critical"
        elif gap_score >= 20:
            priority = "High"
            status = "needs_improvement"
        elif gap_score >= 10:
            priority = "Medium"
            status = "developing"
        else:
            priority = "Low"
            status = "ready"

        items.append(
            {
                "id": f"competency-{record.id}",
                "source": "competency",
                "skill_id": getattr(
                    competency,
                    "id",
                    None,
                ),
                "name": getattr(
                    competency,
                    "name",
                    "Unnamed competency",
                ),
                "description": getattr(
                    competency,
                    "description",
                    None,
                ),
                "current_score": round(
                    current_score
                ),
                "target_score": round(
                    target_score
                ),
                "gap_score": round(
                    gap_score
                ),
                "priority": priority,
                "status": status,
                "category": getattr(
                    competency,
                    "category_name",
                    None,
                ),
            }
        )

    # ---------------------------------------------------------
    # SkillGap based records
    # ---------------------------------------------------------

    for record in skill_gap_records:
        skill = record.skill

        if not skill:
            continue

        current_score = float(
            record.current_score or 0
        )

        target_score = float(
            record.target_score or 80
        )

        gap_score = float(
            record.gap_score
            if record.gap_score is not None
            else max(
                0,
                target_score - current_score,
            )
        )

        if gap_score >= 35:
            priority = "Critical"
            status = "critical"
        elif gap_score >= 20:
            priority = "High"
            status = "needs_improvement"
        elif gap_score >= 10:
            priority = "Medium"
            status = "developing"
        else:
            priority = "Low"
            status = "ready"

        # Avoid duplicates if the same skill already
        # exists through competency analysis.
        existing = next(
            (
                item
                for item in items
                if item["name"].lower()
                == getattr(
                    skill,
                    "name",
                    "",
                ).lower()
            ),
            None,
        )

        if existing:
            continue

        items.append(
            {
                "id": f"skill-gap-{record.id}",
                "source": "skill_gap",
                "skill_id": getattr(
                    skill,
                    "id",
                    None,
                ),
                "name": getattr(
                    skill,
                    "name",
                    "Unnamed skill",
                ),
                "description": getattr(
                    skill,
                    "description",
                    None,
                ),
                "current_score": round(
                    current_score
                ),
                "target_score": round(
                    target_score
                ),
                "gap_score": round(
                    gap_score
                ),
                "priority": priority,
                "status": status,
                "category": None,
            }
        )

    # ---------------------------------------------------------
    # Sort largest gaps first
    # ---------------------------------------------------------

    items.sort(
        key=lambda item: (
            -item["gap_score"],
            item["name"].lower(),
        )
    )

    total = len(items)

    if total:
        overall_score = round(
            sum(
                item["current_score"]
                for item in items
            )
            / total
        )
    else:
        overall_score = 0

    critical_count = sum(
        1
        for item in items
        if item["status"] == "critical"
    )

    high_count = sum(
        1
        for item in items
        if item["priority"] == "High"
    )

    medium_count = sum(
        1
        for item in items
        if item["priority"] == "Medium"
    )

    ready_count = sum(
        1
        for item in items
        if item["status"] == "ready"
    )

    if items:
        top_gaps = items[:5]
    else:
        top_gaps = []

    recommendations = []

    for item in top_gaps:
        if item["status"] == "critical":
            action = (
                "Start structured learning and complete "
                "a practical assessment."
            )
        elif item["priority"] == "High":
            action = (
                "Practice this skill through a guided "
                "project or learning path."
            )
        elif item["priority"] == "Medium":
            action = (
                "Strengthen this skill with targeted practice."
            )
        else:
            action = (
                "Maintain this skill and validate it "
                "through an assessment."
            )

        recommendations.append(
            {
                "skill": item["name"],
                "priority": item["priority"],
                "action": action,
                "gap_score": item["gap_score"],
            }
        )

    return {
        "target_role": (
            trainee.target_role
            or "Target role not defined"
        ),
        "overall_score": overall_score,
        "total_skills": total,
        "critical_gaps": critical_count,
        "high_priority_gaps": high_count,
        "medium_priority_gaps": medium_count,
        "skills_ready": ready_count,
        "skills": items,
        "recommendations": recommendations,
    }
