from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.database import SessionLocal

from app.models.course import Course
from app.models.course_category import CourseCategory
from app.models.course_domain import CourseDomain
from app.models.course_enrollment import CourseEnrollment
from app.models.course_lesson import CourseLesson
from app.models.course_module import CourseModule


CLASSROOM_BASE_URL = "https://skilltwin-classroom.duckdns.org"


# ============================================================
# DOMAIN
# ============================================================

def get_or_create_domain(db):
    domain = db.scalar(
        select(CourseDomain).where(
            CourseDomain.slug == "cloud-devops"
        )
    )

    if domain:
        print(
            f"[EXISTS] Domain: {domain.name} "
            f"(ID {domain.id})"
        )
        return domain

    domain = CourseDomain(
        slug="cloud-devops",
        name="Cloud & DevOps",
        description=(
            "Cloud computing, DevOps, Linux, containers "
            "and infrastructure."
        ),
        display_order=1,
        is_active=True,
    )

    db.add(domain)
    db.flush()

    print(
        f"[CREATED] Domain: {domain.name} "
        f"(ID {domain.id})"
    )

    return domain


# ============================================================
# CATEGORY
# ============================================================

def get_or_create_category(db, domain):
    category = db.scalar(
        select(CourseCategory).where(
            CourseCategory.slug == "cloud-engineering"
        )
    )

    if category:
        print(
            f"[EXISTS] Category: {category.name} "
            f"(ID {category.id})"
        )
        return category

    category = CourseCategory(
        domain_id=domain.id,
        slug="cloud-engineering",
        name="Cloud Engineering",
        description=(
            "Cloud infrastructure, AWS and modern "
            "cloud engineering practices."
        ),
        display_order=1,
        is_active=True,
    )

    db.add(category)
    db.flush()

    print(
        f"[CREATED] Category: {category.name} "
        f"(ID {category.id})"
    )

    return category


# ============================================================
# COURSE 1
# ============================================================

def create_course_one(db, category):
    slug = "cloud-devops-fundamentals"

    existing = db.scalar(
        select(Course).where(
            Course.slug == slug
        )
    )

    if existing:
        print(
            f"[SKIP] Course already exists: "
            f"{existing.title} (ID {existing.id})"
        )
        return existing

    course = Course(
        title="Cloud & DevOps Fundamentals",
        slug=slug,
        description=(
            "A beginner-friendly self-paced course covering "
            "cloud computing, Linux, Git, Docker and CI/CD "
            "fundamentals."
        ),
        instructor_name="SkillTwin Learning Team",
        thumbnail_url=None,
        level="Beginner",
        duration_hours=8,
        price_paise=0,
        currency="INR",
        is_free=True,
        is_active=True,
        category_id=category.id,
    )

    db.add(course)
    db.flush()

    modules = [
        (
            "Introduction to Cloud Computing",
            [
                (
                    "What is Cloud Computing?",
                    "Understand cloud computing, its benefits "
                    "and major service models.",
                    25,
                ),
                (
                    "IaaS, PaaS and SaaS",
                    "Learn the three major cloud service models.",
                    30,
                ),
            ],
        ),
        (
            "Linux Fundamentals",
            [
                (
                    "Linux Basics",
                    "Learn filesystems, directories, permissions "
                    "and basic commands.",
                    40,
                ),
                (
                    "Linux Administration",
                    "Understand users, processes, services "
                    "and system management.",
                    45,
                ),
            ],
        ),
        (
            "Git & GitHub",
            [
                (
                    "Git Fundamentals",
                    "Learn repositories, commits, branches "
                    "and merges.",
                    35,
                ),
                (
                    "Working with GitHub",
                    "Learn remote repositories, push, pull "
                    "and collaboration.",
                    35,
                ),
            ],
        ),
        (
            "Docker Fundamentals",
            [
                (
                    "Introduction to Docker",
                    "Understand containers, images "
                    "and Docker architecture.",
                    40,
                ),
                (
                    "Building and Running Containers",
                    "Build Docker images and run "
                    "containerized applications.",
                    45,
                ),
            ],
        ),
        (
            "CI/CD Basics",
            [
                (
                    "CI/CD Concepts",
                    "Understand continuous integration "
                    "and continuous delivery.",
                    30,
                ),
                (
                    "Deployment Pipeline Basics",
                    "Learn the basic stages of a modern "
                    "deployment pipeline.",
                    35,
                ),
            ],
        ),
    ]

    for module_index, (module_title, lessons) in enumerate(
        modules,
        start=1,
    ):
        module = CourseModule(
            course_id=course.id,
            title=module_title,
            order_index=module_index,
        )

        db.add(module)
        db.flush()

        for lesson_index, (
            lesson_title,
            description,
            duration,
        ) in enumerate(lessons, start=1):

            lesson = CourseLesson(
                module_id=module.id,
                title=lesson_title,
                description=description,
                lesson_type="recorded",
                video_url=None,
                duration_minutes=duration,
                scheduled_at=None,
                meeting_url=None,
                order_index=lesson_index,
                is_published=True,
            )

            db.add(lesson)

    db.flush()

    print(
        f"[CREATED] {course.title} "
        f"(ID {course.id})"
    )

    return course


# ============================================================
# COURSE 2
# ============================================================

def create_course_two(db, category):
    slug = "aws-cloud-engineering-bootcamp"

    existing = db.scalar(
        select(Course).where(
            Course.slug == slug
        )
    )

    if existing:
        print(
            f"[SKIP] Course already exists: "
            f"{existing.title} (ID {existing.id})"
        )
        return existing

    course = Course(
        title="AWS Cloud Engineering Bootcamp",
        slug=slug,
        description=(
            "A live instructor-led AWS cloud engineering "
            "bootcamp covering AWS fundamentals, EC2, "
            "networking, IAM, security and deployment."
        ),
        instructor_name="SkillTwin Cloud Academy",
        thumbnail_url=None,
        level="Intermediate",
        duration_hours=10,
        price_paise=0,
        currency="INR",
        is_free=True,
        is_active=True,
        category_id=category.id,
    )

    db.add(course)
    db.flush()

    now = datetime.utcnow()

    sessions = [
        (
            "AWS Fundamentals",
            (
                "Introduction to AWS services, regions, "
                "availability zones and cloud architecture."
            ),
            1,
            60,
        ),
        (
            "EC2 & Cloud Networking",
            (
                "Learn EC2 instances, VPC basics, subnets, "
                "security groups and networking."
            ),
            2,
            90,
        ),
        (
            "IAM & Cloud Security",
            (
                "Learn IAM users, roles, policies and "
                "fundamental AWS security practices."
            ),
            3,
            75,
        ),
        (
            "AWS Deployment",
            (
                "Deploy a web application on AWS and "
                "understand production deployment basics."
            ),
            4,
            90,
        ),
        (
            "Final Hands-on Session",
            (
                "Build and deploy a complete cloud-based "
                "application with instructor guidance."
            ),
            5,
            120,
        ),
    ]

    for index, (
        title,
        description,
        order_index,
        duration,
    ) in enumerate(sessions):

        module = CourseModule(
            course_id=course.id,
            title=f"Live Session {index + 1}",
            order_index=index + 1,
        )

        db.add(module)
        db.flush()

        scheduled_at = now + timedelta(days=index)

        # Keep the room format consistent with the classroom
        # integration. These are placeholder/demo room URLs.
        meeting_url = (
            f"{CLASSROOM_BASE_URL}/live/"
            f"SKT-AWSCLO-DEMO-{index + 1:02d}"
        )

        lesson = CourseLesson(
            module_id=module.id,
            title=title,
            description=description,
            lesson_type="live",
            video_url=None,
            duration_minutes=duration,
            scheduled_at=scheduled_at,
            meeting_url=meeting_url,
            order_index=order_index,
            is_published=True,
        )

        db.add(lesson)

    db.flush()

    print(
        f"[CREATED] {course.title} "
        f"(ID {course.id})"
    )

    return course


# ============================================================
# ENROLLMENT
# ============================================================

def enroll_trainee(db, trainee, course):
    existing = db.scalar(
        select(CourseEnrollment).where(
            CourseEnrollment.trainee_id == trainee.id,
            CourseEnrollment.course_id == course.id,
        )
    )

    if existing:
        changed = False

        # Restore cancelled demo enrollments.
        if existing.status == "cancelled":
            existing.status = "in_progress"
            changed = True

        # Demo courses are free.
        if existing.payment_status != "not_required":
            existing.payment_status = "not_required"
            changed = True

        if existing.enrolled_at is None:
            existing.enrolled_at = datetime.utcnow()
            changed = True

        if changed:
            db.flush()

        print(
            f"[EXISTS] {course.title} "
            f"-> trainee ID {trainee.id} "
            f"(Enrollment ID {existing.id})"
        )

        return existing

    enrollment = CourseEnrollment(
        trainee_id=trainee.id,
        course_id=course.id,
        status="in_progress",
        payment_status="not_required",
        payment_reference="DEMO-SKILLTWIN",
        enrolled_at=datetime.utcnow(),
    )

    db.add(enrollment)
    db.flush()

    print(
        f"[ENROLLED] {course.title} "
        f"-> trainee ID {trainee.id}"
    )

    return enrollment


# ============================================================
# MAIN
# ============================================================

def main():
    db = SessionLocal()

    try:
        print()
        print("=" * 60)
        print("SKILLTWIN DEMO COURSE SEED")
        print("=" * 60)

        # ----------------------------------------------------
        # Find the first trainee
        # ----------------------------------------------------

        from app.models.trainee import Trainee

        trainee = db.scalar(
            select(Trainee)
            .order_by(Trainee.id.asc())
        )

        if not trainee:
            print(
                "[ERROR] No trainee exists in the database."
            )
            print(
                "Create a trainee account first, "
                "then run this script again."
            )
            return

        print(
            f"[TRAINEE] Using trainee ID={trainee.id}, "
            f"user_id={trainee.user_id}"
        )

        # ----------------------------------------------------
        # Domain
        # ----------------------------------------------------

        domain = get_or_create_domain(db)

        # ----------------------------------------------------
        # Category
        # ----------------------------------------------------

        category = get_or_create_category(
            db,
            domain,
        )

        # ----------------------------------------------------
        # Courses
        # ----------------------------------------------------

        course_one = create_course_one(
            db,
            category,
        )

        course_two = create_course_two(
            db,
            category,
        )

        # ----------------------------------------------------
        # Enroll first trainee
        # ----------------------------------------------------

        enroll_trainee(
            db,
            trainee,
            course_one,
        )

        enroll_trainee(
            db,
            trainee,
            course_two,
        )

        db.commit()

        print()
        print("=" * 60)
        print("DEMO COURSE SEED COMPLETED")
        print("=" * 60)

        print(
            f"Course 1 : {course_one.title} "
            f"(ID {course_one.id})"
        )

        print(
            f"Course 2 : {course_two.title} "
            f"(ID {course_two.id})"
        )

        print(
            f"Trainee  : ID {trainee.id}"
        )

        print("=" * 60)

    except Exception as exc:
        db.rollback()

        print()
        print("[ERROR] Demo course seed failed:")
        print(exc)

        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
