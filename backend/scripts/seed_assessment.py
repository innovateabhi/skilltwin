from sqlalchemy import select

from app.core.database import SessionLocal

from app.models.assessment import Assessment
from app.models.assessment_question import AssessmentQuestion
from app.models.competency import Competency


QUESTIONS = [
    {
        "question_text": "Which approach best demonstrates practical competency in this area?",
        "a": "Memorizing terminology without applying it",
        "b": "Applying the concept correctly to a realistic problem",
        "c": "Avoiding the concept entirely",
        "d": "Only reading documentation",
        "correct": "B",
    },
    {
        "question_text": "When solving a technical problem, which approach is generally most useful?",
        "a": "Guess and immediately deploy",
        "b": "Ignore available evidence",
        "c": "Analyze the problem, test a solution, and verify the result",
        "d": "Repeat the same failed approach",
        "correct": "C",
    },
    {
        "question_text": "What best demonstrates independent technical capability?",
        "a": "Following instructions without understanding them",
        "b": "Being able to explain, implement, test, and troubleshoot the solution",
        "c": "Copying an answer without validation",
        "d": "Avoiding unfamiliar problems",
        "correct": "B",
    },
    {
        "question_text": "What is an important part of validating a technical solution?",
        "a": "Assuming it works",
        "b": "Testing expected and unexpected cases",
        "c": "Removing all tests",
        "d": "Only checking the user interface",
        "correct": "B",
    },
    {
        "question_text": "Which behavior most strongly indicates developing mastery?",
        "a": "Repeating one memorized example",
        "b": "Applying knowledge to new situations",
        "c": "Avoiding difficult tasks",
        "d": "Depending on step-by-step instructions for every task",
        "correct": "B",
    },
]


def main():

    db = SessionLocal()

    try:

        existing = db.scalar(
            select(Assessment).where(
                Assessment.title
                == "SkillTwin Competency Baseline"
            )
        )

        if existing:
            print(
                "Assessment already exists:",
                existing.id,
            )
            return

        competencies = db.scalars(
            select(Competency)
            .where(
                Competency.is_active.is_(True)
            )
            .order_by(Competency.id)
            .limit(len(QUESTIONS))
        ).all()

        if len(competencies) < len(QUESTIONS):
            raise RuntimeError(
                "Not enough active competencies. "
                "Seed the catalogue first."
            )

        assessment = Assessment(
            title="SkillTwin Competency Baseline",
            description=(
                "A baseline assessment used to measure "
                "your current competency profile."
            ),
            duration_minutes=15,
            passing_score=70,
            is_active=True,
        )

        db.add(assessment)
        db.flush()

        for index, competency in enumerate(
            competencies
        ):

            item = QUESTIONS[index]

            question = AssessmentQuestion(
                assessment_id=assessment.id,
                competency_id=competency.id,
                question_text=item[
                    "question_text"
                ],
                option_a=item["a"],
                option_b=item["b"],
                option_c=item["c"],
                option_d=item["d"],
                correct_option=item[
                    "correct"
                ],
                points=20,
            )

            db.add(question)

        db.commit()

        print(
            f"Created assessment #{assessment.id}"
        )

        print(
            f"Created {len(QUESTIONS)} questions"
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()