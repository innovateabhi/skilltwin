from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.course import Course
from app.models.course_category import CourseCategory


COURSE_CATEGORY_MAP = {
    "AWS Cloud Engineering": "cloud-computing",
    "Linux & DevOps Fundamentals": "devops-infrastructure",
    "Python for Cloud Automation": "programming",
}


def map_courses():
    db = SessionLocal()

    try:
        for course_title, category_slug in COURSE_CATEGORY_MAP.items():

            course = db.scalar(
                select(Course).where(
                    Course.title == course_title
                )
            )

            if not course:
                print(f"Course not found: {course_title}")
                continue

            category = db.scalar(
                select(CourseCategory).where(
                    CourseCategory.slug == category_slug
                )
            )

            if not category:
                print(
                    f"Category not found: {category_slug}"
                )
                continue

            course.category_id = category.id

            print(
                f"{course.title}"
                f" -> {category.name}"
            )

        db.commit()

        print()
        print("Existing courses mapped successfully.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    map_courses()