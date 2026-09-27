from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.course import Course
from app.models.course_skill import CourseSkill
from app.models.skill import Skill


COURSE_SKILLS = {
    "AWS Cloud Engineering": [
        "aws",
        "linux",
        "docker",
        "terraform",
        "ci-cd",
    ],
    "Linux & DevOps Fundamentals": [
        "linux",
        "docker",
        "git",
        "ci-cd",
    ],
    "Python for Cloud Automation": [
        "python-programming",
        "aws",
        "rest-api",
    ],
}


def map_course_skills():
    db = SessionLocal()

    try:
        created = 0

        for course_title, skill_slugs in COURSE_SKILLS.items():

            course = db.scalar(
                select(Course).where(
                    Course.title == course_title
                )
            )

            if not course:
                print(
                    f"Course not found: {course_title}"
                )
                continue

            for skill_slug in skill_slugs:

                skill = db.scalar(
                    select(Skill).where(
                        Skill.slug == skill_slug
                    )
                )

                if not skill:
                    print(
                        f"Skill not found: {skill_slug}"
                    )
                    continue

                existing = db.scalar(
                    select(CourseSkill).where(
                        CourseSkill.course_id == course.id,
                        CourseSkill.skill_id == skill.id,
                    )
                )

                if existing:
                    continue

                db.add(
                    CourseSkill(
                        course_id=course.id,
                        skill_id=skill.id,
                    )
                )

                created += 1

        db.commit()

        print()
        print(
            f"Course-skill relationships created: {created}"
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    map_course_skills()