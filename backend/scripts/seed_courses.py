from datetime import datetime, timedelta

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models import (
    Course,
    CourseLesson,
    CourseModule,
)
from app.models.course_category import CourseCategory


# ============================================================
# SKILLTWIN COURSE CATALOGUE
# ============================================================
#
# Each course is connected to an existing CourseCategory
# using category_slug.
#
# This script is SAFE TO RUN MULTIPLE TIMES:
# - Existing courses are updated instead of duplicated.
# - Missing courses are created.
# - Existing category mappings are corrected.
# - Missing modules and lessons are created.
#
# Total catalogue: 20 courses
# ============================================================

COURSES_DATA = [
    {
        "title": "AWS Cloud Engineering",
        "slug": "aws-cloud-engineering",
        "description": (
            "Learn AWS fundamentals, compute, storage, networking, "
            "IAM, monitoring and practical cloud deployment."
        ),
        "instructor_name": "SkillTwin Cloud Team",
        "level": "Intermediate",
        "duration_hours": 24,
        "price_paise": 149900,
        "currency": "INR",
        "is_free": False,
        "category_slug": "cloud-computing",
    },
    {
        "title": "Linux & DevOps Fundamentals",
        "slug": "linux-devops-fundamentals",
        "description": (
            "Build practical Linux, Git, CI/CD, automation and "
            "DevOps foundations for modern software environments."
        ),
        "instructor_name": "SkillTwin DevOps Team",
        "level": "Beginner",
        "duration_hours": 18,
        "price_paise": 99900,
        "currency": "INR",
        "is_free": False,
        "category_slug": "devops-infrastructure",
    },
    {
        "title": "Python for Cloud Automation",
        "slug": "python-cloud-automation",
        "description": (
            "Use Python to automate cloud infrastructure, "
            "deployment workflows and operational tasks."
        ),
        "instructor_name": "SkillTwin Engineering Team",
        "level": "Intermediate",
        "duration_hours": 20,
        "price_paise": 129900,
        "currency": "INR",
        "is_free": False,
        "category_slug": "programming",
    },
    {
        "title": "Full Stack Web Development",
        "slug": "full-stack-web-development",
        "description": (
            "Learn frontend and backend web development, APIs, "
            "databases and production-ready application architecture."
        ),
        "instructor_name": "SkillTwin Web Team",
        "level": "Intermediate",
        "duration_hours": 32,
        "price_paise": 179900,
        "currency": "INR",
        "is_free": False,
        "category_slug": "web-development",
    },
    {
        "title": "Python Programming Mastery",
        "slug": "python-programming-mastery",
        "description": (
            "Master Python programming from fundamentals to "
            "object-oriented programming, modules and practical projects."
        ),
        "instructor_name": "SkillTwin Programming Team",
        "level": "Beginner",
        "duration_hours": 22,
        "price_paise": 89900,
        "currency": "INR",
        "is_free": False,
        "category_slug": "programming",
    },
    {
        "title": "Docker & Kubernetes Essentials",
        "slug": "docker-kubernetes-essentials",
        "description": (
            "Learn containerization with Docker and orchestration "
            "fundamentals with Kubernetes."
        ),
        "instructor_name": "SkillTwin DevOps Team",
        "level": "Intermediate",
        "duration_hours": 26,
        "price_paise": 159900,
        "currency": "INR",
        "is_free": False,
        "category_slug": "devops-infrastructure",
    },
    {
        "title": "Cybersecurity Fundamentals",
        "slug": "cybersecurity-fundamentals",
        "description": (
            "Understand cybersecurity fundamentals, threats, "
            "network security, authentication and defensive practices."
        ),
        "instructor_name": "SkillTwin Security Team",
        "level": "Beginner",
        "duration_hours": 20,
        "price_paise": 109900,
        "currency": "INR",
        "is_free": False,
        "category_slug": "cybersecurity",
    },
    {
        "title": "Ethical Hacking & Penetration Testing",
        "slug": "ethical-hacking-penetration-testing",
        "description": (
            "Explore ethical hacking methodologies, vulnerability "
            "assessment and penetration testing concepts."
        ),
        "instructor_name": "SkillTwin Security Team",
        "level": "Advanced",
        "duration_hours": 30,
        "price_paise": 199900,
        "currency": "INR",
        "is_free": False,
        "category_slug": "cybersecurity",
    },
    {
        "title": "Data Science with Python",
        "slug": "data-science-with-python",
        "description": (
            "Learn data analysis, visualization, statistics and "
            "practical data science workflows using Python."
        ),
        "instructor_name": "SkillTwin Data Team",
        "level": "Intermediate",
        "duration_hours": 28,
        "price_paise": 169900,
        "currency": "INR",
        "is_free": False,
        "category_slug": "data-science-analytics",
    },
    {
        "title": "SQL & Database Management",
        "slug": "sql-database-management",
        "description": (
            "Learn SQL, relational databases, queries, joins, "
            "normalization and practical database management."
        ),
        "instructor_name": "SkillTwin Data Team",
        "level": "Beginner",
        "duration_hours": 16,
        "price_paise": 79900,
        "currency": "INR",
        "is_free": False,
        "category_slug": "data-databases",
    },
    {
        "title": "Machine Learning Fundamentals",
        "slug": "machine-learning-fundamentals",
        "description": (
            "Understand machine learning concepts, supervised and "
            "unsupervised learning, model evaluation and workflows."
        ),
        "instructor_name": "SkillTwin AI Team",
        "level": "Intermediate",
        "duration_hours": 30,
        "price_paise": 189900,
        "currency": "INR",
        "is_free": False,
        "category_slug": "artificial-intelligence-machine-learning",
    },
    {
        "title": "Generative AI & LLM Engineering",
        "slug": "generative-ai-llm-engineering",
        "description": (
            "Learn generative AI concepts, LLM applications, "
            "prompt engineering, RAG and AI application architecture."
        ),
        "instructor_name": "SkillTwin AI Team",
        "level": "Advanced",
        "duration_hours": 26,
        "price_paise": 219900,
        "currency": "INR",
        "is_free": False,
        "category_slug": "artificial-intelligence-machine-learning",
    },
    {
        "title": "React Frontend Development",
        "slug": "react-frontend-development",
        "description": (
            "Build modern responsive interfaces using React, "
            "component architecture, routing, state and API integration."
        ),
        "instructor_name": "SkillTwin Web Team",
        "level": "Intermediate",
        "duration_hours": 24,
        "price_paise": 139900,
        "currency": "INR",
        "is_free": False,
        "category_slug": "web-development",
    },
    {
        "title": "Mobile App Development",
        "slug": "mobile-app-development",
        "description": (
            "Learn mobile application development concepts, "
            "application architecture, APIs and deployment workflows."
        ),
        "instructor_name": "SkillTwin Mobile Team",
        "level": "Intermediate",
        "duration_hours": 28,
        "price_paise": 159900,
        "currency": "INR",
        "is_free": False,
        "category_slug": "mobile-development",
    },
    {
        "title": "UI/UX Design Fundamentals",
        "slug": "ui-ux-design-fundamentals",
        "description": (
            "Learn user research, information architecture, wireframes, "
            "prototyping and modern UI/UX design principles."
        ),
        "instructor_name": "SkillTwin Design Team",
        "level": "Beginner",
        "duration_hours": 18,
        "price_paise": 99900,
        "currency": "INR",
        "is_free": False,
        "category_slug": "ui-ux-design",
    },
    {
        "title": "Digital Marketing Essentials",
        "slug": "digital-marketing-essentials",
        "description": (
            "Learn SEO, social media marketing, content strategy, "
            "digital advertising and marketing analytics."
        ),
        "instructor_name": "SkillTwin Marketing Team",
        "level": "Beginner",
        "duration_hours": 20,
        "price_paise": 89900,
        "currency": "INR",
        "is_free": False,
        "category_slug": "marketing-sales",
    },
    {
        "title": "Project Management Fundamentals",
        "slug": "project-management-fundamentals",
        "description": (
            "Learn project planning, scope management, scheduling, "
            "risk management, collaboration and project delivery."
        ),
        "instructor_name": "SkillTwin Management Team",
        "level": "Beginner",
        "duration_hours": 16,
        "price_paise": 89900,
        "currency": "INR",
        "is_free": False,
        "category_slug": "project-management",
    },
    {
        "title": "Entrepreneurship & Startup Strategy",
        "slug": "entrepreneurship-startup-strategy",
        "description": (
            "Explore startup fundamentals, business models, market "
            "research, validation, strategy and growth planning."
        ),
        "instructor_name": "SkillTwin Business Team",
        "level": "Intermediate",
        "duration_hours": 18,
        "price_paise": 119900,
        "currency": "INR",
        "is_free": False,
        "category_slug": "entrepreneurship",
    },
    {
        "title": "Professional Communication",
        "slug": "professional-communication",
        "description": (
            "Develop professional communication, presentation, "
            "business writing and workplace collaboration skills."
        ),
        "instructor_name": "SkillTwin Professional Skills Team",
        "level": "Beginner",
        "duration_hours": 12,
        "price_paise": 69900,
        "currency": "INR",
        "is_free": False,
        "category_slug": "communication",
    },
    {
        "title": "Financial Accounting Fundamentals",
        "slug": "financial-accounting-fundamentals",
        "description": (
            "Understand accounting principles, financial statements, "
            "bookkeeping and essential financial analysis."
        ),
        "instructor_name": "SkillTwin Finance Team",
        "level": "Beginner",
        "duration_hours": 18,
        "price_paise": 99900,
        "currency": "INR",
        "is_free": False,
        "category_slug": "finance-accounting",
    },
]


# ============================================================
# MODULES + LESSONS
# ============================================================

def create_default_modules_and_lessons(
    db,
    course: Course,
):
    """
    Creates a basic learning structure for a course only if
    the course does not already have modules.
    """

    existing_module = db.scalar(
        select(CourseModule)
        .where(CourseModule.course_id == course.id)
        .limit(1)
    )

    if existing_module:
        return

    modules = [
        CourseModule(
            course_id=course.id,
            title="Getting Started",
            order_index=1,
        ),
        CourseModule(
            course_id=course.id,
            title="Core Concepts",
            order_index=2,
        ),
        CourseModule(
            course_id=course.id,
            title="Practical Implementation",
            order_index=3,
        ),
    ]

    db.add_all(modules)
    db.flush()

    for module_index, module in enumerate(modules):

        lessons = [
            CourseLesson(
                module_id=module.id,
                title=f"{module.title} - Lecture 1",
                description=(
                    "Core concepts and practical introduction."
                ),
                lesson_type="recorded",
                duration_minutes=35,
                order_index=1,
                is_published=True,
            ),
            CourseLesson(
                module_id=module.id,
                title=f"{module.title} - Lecture 2",
                description=(
                    "Hands-on practical learning session."
                ),
                lesson_type="recorded",
                duration_minutes=45,
                order_index=2,
                is_published=True,
            ),
        ]

        # Add a live session to the final module.
        if module_index == 2:
            lessons.append(
                CourseLesson(
                    module_id=module.id,
                    title="Live Doubt Clearing Session",
                    description=(
                        "Interactive live session with the instructor."
                    ),
                    lesson_type="live",
                    duration_minutes=60,
                    scheduled_at=(
                        datetime.utcnow() + timedelta(days=3)
                    ),
                    meeting_url="https://meet.google.com/",
                    order_index=3,
                    is_published=True,
                )
            )

        db.add_all(lessons)


# ============================================================
# MAIN SEED FUNCTION
# ============================================================

def main():
    db = SessionLocal()

    try:
        created = 0
        updated = 0
        skipped = 0

        print()
        print("=" * 60)
        print("SKILLTWIN COURSE CATALOGUE SEED")
        print("=" * 60)
        print()

        for data in COURSES_DATA:

            category_slug = data["category_slug"]

            # ------------------------------------------------
            # Find category
            # ------------------------------------------------
            category = db.scalar(
                select(CourseCategory)
                .where(
                    CourseCategory.slug == category_slug,
                    CourseCategory.is_active.is_(True),
                )
            )

            if not category:
                print(
                    f"[SKIPPED] Category not found: "
                    f"{category_slug}"
                )

                skipped += 1
                continue

            # ------------------------------------------------
            # Find existing course by unique slug
            # ------------------------------------------------
            course = db.scalar(
                select(Course)
                .where(
                    Course.slug == data["slug"]
                )
            )

            # Remove category_slug because it is not a
            # column in the Course model.
            course_data = {
                key: value
                for key, value in data.items()
                if key != "category_slug"
            }

            # ------------------------------------------------
            # UPDATE EXISTING COURSE
            # ------------------------------------------------
            if course:

                changed = False

                for key, value in course_data.items():

                    if getattr(course, key) != value:
                        setattr(course, key, value)
                        changed = True

                # Make sure the course is connected to the
                # correct marketplace category.
                if course.category_id != category.id:
                    course.category_id = category.id
                    changed = True

                # Make sure seeded courses are active.
                if not course.is_active:
                    course.is_active = True
                    changed = True

                if changed:
                    updated += 1

                    print(
                        f"[UPDATED] {course.title}"
                        f" -> {category.name}"
                    )
                else:
                    print(
                        f"[EXISTS]  {course.title}"
                    )

                # Add modules/lessons only if none exist.
                create_default_modules_and_lessons(
                    db,
                    course,
                )

            # ------------------------------------------------
            # CREATE NEW COURSE
            # ------------------------------------------------
            else:

                course = Course(
                    **course_data,
                    category_id=category.id,
                    is_active=True,
                )

                db.add(course)
                db.flush()

                create_default_modules_and_lessons(
                    db,
                    course,
                )

                created += 1

                print(
                    f"[CREATED] {course.title}"
                    f" -> {category.name}"
                )

        db.commit()

        # ====================================================
        # FINAL COUNTS
        # ====================================================

        total_courses = db.scalar(
            select(func.count(Course.id))
        ) or 0

        active_courses = db.scalar(
            select(func.count(Course.id))
            .where(
                Course.is_active.is_(True)
            )
        ) or 0

        mapped_courses = db.scalar(
            select(func.count(Course.id))
            .where(
                Course.category_id.is_not(None),
                Course.is_active.is_(True),
            )
        ) or 0

        print()
        print("=" * 60)
        print("COURSE CATALOGUE SUMMARY")
        print("=" * 60)
        print(f"Courses created : {created}")
        print(f"Courses updated : {updated}")
        print(f"Courses skipped : {skipped}")
        print(f"Total courses   : {total_courses}")
        print(f"Active courses  : {active_courses}")
        print(f"Mapped courses  : {mapped_courses}")
        print("=" * 60)
        print()
        print("Course catalogue seeded successfully.")
        print()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()

