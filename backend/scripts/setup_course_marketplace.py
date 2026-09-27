from sqlalchemy import inspect, text

from app.core.database import Base, engine
from app.models.course_domain import CourseDomain
from app.models.course_category import CourseCategory
from app.models.course_skill import CourseSkill
from app.models.course import Course


def setup_database():
    print("Setting up SkillTwin course marketplace...")

    # Create new tables.
    Base.metadata.create_all(
        bind=engine,
        tables=[
            CourseDomain.__table__,
            CourseCategory.__table__,
            CourseSkill.__table__,
        ],
    )

    inspector = inspect(engine)

    course_columns = {
        column["name"]
        for column in inspector.get_columns("courses")
    }

    if "category_id" not in course_columns:
        print("Adding category_id to courses...")

        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    ALTER TABLE courses
                    ADD COLUMN category_id INT NULL,
                    ADD INDEX ix_courses_category_id (category_id),
                    ADD CONSTRAINT fk_courses_category
                    FOREIGN KEY (category_id)
                    REFERENCES course_categories(id)
                    ON DELETE SET NULL
                    """
                )
            )

        print("category_id added successfully.")
    else:
        print("category_id already exists.")

    print("Course marketplace database setup completed.")


if __name__ == "__main__":
    setup_database()