from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user

from app.models.user import User
from app.models.trainee import Trainee
from app.models.course import Course
from app.models.course_module import CourseModule
from app.models.course_lesson import CourseLesson
from app.models.course_enrollment import CourseEnrollment
from app.models.lesson_progress import LessonProgress

from app.schemas.course import CourseResponse


router = APIRouter(
    prefix="/api/trainee/courses",
    tags=["Trainee Courses"],
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
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trainee profile not found",
        )

    return trainee


def build_course_response(
    enrollment: CourseEnrollment,
    db: Session,
) -> CourseResponse:

    course = enrollment.course

    total_lessons = db.scalar(
        select(func.count(CourseLesson.id))
        .join(
            CourseModule,
            CourseLesson.module_id == CourseModule.id,
        )
        .where(
            CourseModule.course_id == course.id
        )
    ) or 0

    completed_lessons = db.scalar(
        select(func.count(LessonProgress.id))
        .join(
            CourseLesson,
            LessonProgress.lesson_id == CourseLesson.id,
        )
        .join(
            CourseModule,
            CourseLesson.module_id == CourseModule.id,
        )
        .where(
            LessonProgress.enrollment_id == enrollment.id,
            LessonProgress.completed.is_(True),
            CourseModule.course_id == course.id,
        )
    ) or 0

    if total_lessons:
        progress_percent = round(
            completed_lessons / total_lessons * 100
        )
    else:
        progress_percent = 0

    return CourseResponse(
        id=course.id,
        title=course.title,
        slug=course.slug,
        description=course.description,
        instructor_name=course.instructor_name,
        thumbnail_url=course.thumbnail_url,
        level=course.level,
        duration_hours=course.duration_hours,
        status=enrollment.status,
        progress_percent=progress_percent,
        completed_lessons=completed_lessons,
        total_lessons=total_lessons,
        last_accessed_at=enrollment.last_accessed_at,
    )


def get_courses(
    current_user: User,
    db: Session,
    status_filter: str | None = None,
):

    trainee = get_trainee(current_user, db)

    stmt = (
        select(CourseEnrollment)
        .join(
            Course,
            CourseEnrollment.course_id == Course.id,
        )
        .where(
            CourseEnrollment.trainee_id == trainee.id,
            Course.is_active.is_(True),
        )
        .order_by(
            CourseEnrollment.last_accessed_at.desc()
        )
    )

    if status_filter:
        stmt = stmt.where(
            CourseEnrollment.status == status_filter
        )

    enrollments = db.scalars(stmt).all()

    return [
        build_course_response(
            enrollment,
            db,
        )
        for enrollment in enrollments
    ]


@router.get(
    "",
    response_model=list[CourseResponse],
)
def list_courses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_courses(
        current_user,
        db,
    )


@router.get(
    "/in-progress",
    response_model=list[CourseResponse],
)
def in_progress_courses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_courses(
        current_user,
        db,
        "in_progress",
    )


@router.get(
    "/recorded",
    response_model=list[CourseResponse],
)
def recorded_courses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_courses(
        current_user,
        db,
        "in_progress",
    )


@router.get(
    "/live",
    response_model=list[CourseResponse],
)
def live_courses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_courses(
        current_user,
        db,
        "in_progress",
    )


@router.get(
    "/completed",
    response_model=list[CourseResponse],
)
def completed_courses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_courses(
        current_user,
        db,
        "completed",
    )