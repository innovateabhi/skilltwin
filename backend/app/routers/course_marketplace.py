from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.dependencies import get_current_user

from app.models.user import User
from app.models.trainee import Trainee
from app.models.course import Course
from app.models.course_domain import CourseDomain
from app.models.course_category import CourseCategory
from app.models.course_enrollment import CourseEnrollment
from app.models.course_lesson import CourseLesson
from app.models.course_module import CourseModule


router = APIRouter(
    prefix="/api/course-marketplace",
    tags=["Course Marketplace"],
)


class MarketplaceCourseResponse(BaseModel):
    id: int
    title: str
    slug: str
    description: str | None
    instructor_name: str | None
    thumbnail_url: str | None
    level: str
    duration_hours: int
    price_paise: int
    currency: str
    is_free: bool
    domain_id: int
    domain_name: str
    category_id: int
    category_name: str
    total_lessons: int
    enrolled: bool


class MarketplaceCategoryResponse(BaseModel):
    id: int
    name: str
    slug: str
    domain_id: int
    domain_name: str
    course_count: int


class MarketplaceDomainResponse(BaseModel):
    id: int
    name: str
    slug: str
    course_count: int


def get_current_trainee(
    current_user: User,
    db: Session,
):
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


@router.get("/domains")
def get_domains(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    domains = db.scalars(
        select(CourseDomain)
        .where(CourseDomain.is_active.is_(True))
        .order_by(CourseDomain.display_order)
    ).all()

    result = []

    for domain in domains:

        course_count = db.scalar(
            select(func.count(Course.id))
            .join(
                CourseCategory,
                Course.category_id == CourseCategory.id,
            )
            .where(
                CourseCategory.domain_id == domain.id,
                Course.is_active.is_(True),
            )
        ) or 0

        result.append(
            MarketplaceDomainResponse(
                id=domain.id,
                name=domain.name,
                slug=domain.slug,
                course_count=course_count,
            )
        )

    return result


@router.get("/categories")
def get_categories(
    domain_slug: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = (
        select(
            CourseCategory,
            CourseDomain,
        )
        .join(
            CourseDomain,
            CourseCategory.domain_id == CourseDomain.id,
        )
        .where(
            CourseCategory.is_active.is_(True),
            CourseDomain.is_active.is_(True),
        )
        .order_by(
            CourseDomain.display_order,
            CourseCategory.display_order,
        )
    )

    if domain_slug:
        query = query.where(
            CourseDomain.slug == domain_slug
        )

    rows = db.execute(query).all()

    result = []

    for category, domain in rows:

        course_count = db.scalar(
            select(func.count(Course.id))
            .where(
                Course.category_id == category.id,
                Course.is_active.is_(True),
            )
        ) or 0

        result.append(
            MarketplaceCategoryResponse(
                id=category.id,
                name=category.name,
                slug=category.slug,
                domain_id=domain.id,
                domain_name=domain.name,
                course_count=course_count,
            )
        )

    return result


@router.get("/courses")
def get_marketplace_courses(
    search: str | None = None,
    domain_slug: str | None = None,
    category_slug: str | None = None,
    level: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trainee = get_current_trainee(
        current_user,
        db,
    )

    query = (
        select(
            Course,
            CourseCategory,
            CourseDomain,
        )
        .join(
            CourseCategory,
            Course.category_id == CourseCategory.id,
        )
        .join(
            CourseDomain,
            CourseCategory.domain_id == CourseDomain.id,
        )
        .where(
            Course.is_active.is_(True),
            CourseCategory.is_active.is_(True),
            CourseDomain.is_active.is_(True),
        )
        .order_by(
            Course.created_at.desc()
        )
    )

    if search:
        search_term = f"%{search.strip()}%"

        query = query.where(
            or_(
                Course.title.ilike(search_term),
                Course.description.ilike(search_term),
                Course.instructor_name.ilike(search_term),
                CourseCategory.name.ilike(search_term),
                CourseDomain.name.ilike(search_term),
            )
        )

    if domain_slug:
        query = query.where(
            CourseDomain.slug == domain_slug
        )

    if category_slug:
        query = query.where(
            CourseCategory.slug == category_slug
        )

    if level:
        query = query.where(
            Course.level == level
        )

    rows = db.execute(query).all()

    result = []

    for course, category, domain in rows:

        total_lessons = db.scalar(
            select(func.count(CourseLesson.id))
            .join(
                CourseModule,
                CourseLesson.module_id == CourseModule.id,
            )
            .where(
                CourseModule.course_id == course.id,
                CourseLesson.is_published.is_(True),
            )
        ) or 0

        enrollment = db.scalar(
            select(CourseEnrollment)
            .where(
                CourseEnrollment.course_id == course.id,
                CourseEnrollment.trainee_id == trainee.id,
            )
        )

        result.append(
            MarketplaceCourseResponse(
                id=course.id,
                title=course.title,
                slug=course.slug,
                description=course.description,
                instructor_name=course.instructor_name,
                thumbnail_url=course.thumbnail_url,
                level=course.level,
                duration_hours=course.duration_hours,
                price_paise=course.price_paise,
                currency=course.currency,
                is_free=course.is_free,
                domain_id=domain.id,
                domain_name=domain.name,
                category_id=category.id,
                category_name=category.name,
                total_lessons=total_lessons,
                enrolled=enrollment is not None,
            )
        )

    return result


@router.get("/courses/{course_id}")
def get_course_details(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    trainee = get_current_trainee(
        current_user,
        db,
    )

    course = db.scalar(
        select(Course)
        .options(
            joinedload(Course.modules)
        )
        .where(
            Course.id == course_id,
            Course.is_active.is_(True),
        )
    )

    if not course:
        raise HTTPException(
            status_code=404,
            detail="Course not found",
        )

    category = db.scalar(
        select(CourseCategory)
        .where(
            CourseCategory.id == course.category_id
        )
    )

    if not category:
        raise HTTPException(
            status_code=500,
            detail="Course category is not configured",
        )

    domain = db.scalar(
        select(CourseDomain)
        .where(
            CourseDomain.id == category.domain_id
        )
    )

    enrollment = db.scalar(
        select(CourseEnrollment)
        .where(
            CourseEnrollment.course_id == course.id,
            CourseEnrollment.trainee_id == trainee.id,
        )
    )

    modules = []

    for module in course.modules:

        lessons = []

        for lesson in module.lessons:
            lessons.append(
                {
                    "id": lesson.id,
                    "title": lesson.title,
                    "description": lesson.description,
                    "lesson_type": lesson.lesson_type,
                    "video_url": lesson.video_url,
                    "duration_minutes": lesson.duration_minutes,
                    "scheduled_at": lesson.scheduled_at,
                    "meeting_url": lesson.meeting_url,
                    "order_index": lesson.order_index,
                    "is_published": lesson.is_published,
                }
            )

        modules.append(
            {
                "id": module.id,
                "title": module.title,
                "order_index": module.order_index,
                "lessons": lessons,
            }
        )

    return {
        "id": course.id,
        "title": course.title,
        "slug": course.slug,
        "description": course.description,
        "instructor_name": course.instructor_name,
        "thumbnail_url": course.thumbnail_url,
        "level": course.level,
        "duration_hours": course.duration_hours,
        "price_paise": course.price_paise,
        "currency": course.currency,
        "is_free": course.is_free,
        "domain": {
            "id": domain.id,
            "name": domain.name,
            "slug": domain.slug,
        },
        "category": {
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
        },
        "enrolled": enrollment is not None,
        "enrollment_id": (
            enrollment.id
            if enrollment
            else None
        ),
        "modules": modules,
    }