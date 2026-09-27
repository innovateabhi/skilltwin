from app.core.database import Base, engine
from app.models import (
    Course,
    CourseModule,
    CourseLesson,
    CourseEnrollment,
    LessonProgress,
)


def main():
    Base.metadata.create_all(bind=engine)

    print("Course tables created successfully.")


if __name__ == "__main__":
    main()