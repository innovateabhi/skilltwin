from datetime import datetime

from sqlalchemy import select

from app.core.database import SessionLocal

from app.models.trainee import Trainee
from app.models.course import Course
from app.models.course_enrollment import CourseEnrollment


DEFAULT_COURSE_SLUGS = [
    "cloud-devops-fundamentals",
    "aws-cloud-engineering-bootcamp",
]


def main():
    db = SessionLocal()

    try:
        print()
        print("=" * 60)
        print("SKILLTWIN DEFAULT COURSE ENROLLMENT")
        print("=" * 60)

        # ---------------------------------------------------------
        # Find the two default courses
        # ---------------------------------------------------------

        courses = (
            db.execute(
                select(Course).where(
                    Course.slug.in_(DEFAULT_COURSE_SLUGS),
                    Course.is_active.is_(True),
                )
            )
            .scalars()
            .all()
        )

        if not courses:
            print(
                "[ERROR] Default courses were not found."
            )
            print(
                "Run seed_demo_courses.py first "
                "if the courses do not exist."
            )
            return

        print()
        print("DEFAULT COURSES FOUND:")

        for course in courses:
            print(
                f"  ID={course.id} | "
                f"{course.title}"
            )

        # ---------------------------------------------------------
        # Find all trainees
        # ---------------------------------------------------------

        trainees = (
            db.execute(
                select(Trainee)
                .order_by(Trainee.id.asc())
            )
            .scalars()
            .all()
        )

        if not trainees:
            print()
            print("[ERROR] No trainees found.")
            return

        print()
        print(
            f"FOUND {len(trainees)} TRAINEE(S)."
        )

        created_count = 0
        existing_count = 0
        updated_count = 0

        # ---------------------------------------------------------
        # Enroll every trainee into every default course
        # ---------------------------------------------------------

        for trainee in trainees:

            print()
            print(
                f"TRAINEE ID={trainee.id} "
                f"(USER ID={trainee.user_id})"
            )

            for course in courses:

                existing = db.execute(
                    select(CourseEnrollment).where(
                        CourseEnrollment.trainee_id == trainee.id,
                        CourseEnrollment.course_id == course.id,
                    )
                ).scalar_one_or_none()

                # -------------------------------------------------
                # Existing enrollment
                # -------------------------------------------------

                if existing:

                    changed = False

                    # If an old/cancelled demo enrollment exists,
                    # restore it.
                    if existing.status == "cancelled":
                        existing.status = "in_progress"
                        changed = True

                    # These demo courses are free.
                    if existing.payment_status != "not_required":
                        existing.payment_status = "not_required"
                        changed = True

                    # Make sure required timestamp exists.
                    if existing.enrolled_at is None:
                        existing.enrolled_at = datetime.utcnow()
                        changed = True

                    if changed:
                        db.flush()
                        updated_count += 1

                        print(
                            f"  UPDATED  -> "
                            f"{course.title} "
                            f"(Enrollment ID={existing.id})"
                        )
                    else:
                        existing_count += 1

                        print(
                            f"  EXISTS   -> "
                            f"{course.title} "
                            f"(Enrollment ID={existing.id})"
                        )

                    continue

                # -------------------------------------------------
                # Create enrollment
                # -------------------------------------------------

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
                    f"  CREATED  -> "
                    f"{course.title} "
                    f"(Enrollment ID={enrollment.id})"
                )

                created_count += 1

        # ---------------------------------------------------------
        # Commit
        # ---------------------------------------------------------

        db.commit()

        # ---------------------------------------------------------
        # Summary
        # ---------------------------------------------------------

        print()
        print("=" * 60)
        print("DEFAULT COURSE ENROLLMENT COMPLETED")
        print("=" * 60)

        print(
            f"New enrollments      : {created_count}"
        )

        print(
            f"Existing enrollments : {existing_count}"
        )

        print(
            f"Updated enrollments  : {updated_count}"
        )

        print(
            f"Total trainees       : {len(trainees)}"
        )

        print(
            f"Default courses      : {len(courses)}"
        )

        print("=" * 60)

    except Exception as exc:

        db.rollback()

        print()
        print(
            "[ERROR] Default course enrollment failed:"
        )
        print(exc)

        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
