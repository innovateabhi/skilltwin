from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssessmentListItem(BaseModel):
    id: int
    title: str
    description: str | None = None
    duration_minutes: int
    passing_score: int
    question_count: int
    completed_attempts: int

    model_config = ConfigDict(
        from_attributes=True,
    )


class AssessmentQuestionResponse(BaseModel):
    id: int
    competency_id: int
    competency_name: str

    question_text: str

    option_a: str
    option_b: str
    option_c: str
    option_d: str

    points: int

    model_config = ConfigDict(
        from_attributes=True,
    )


class AssessmentStartResponse(BaseModel):
    attempt_id: int
    assessment_id: int
    title: str
    description: str | None = None
    duration_minutes: int
    questions: list[AssessmentQuestionResponse]


class AssessmentAnswerRequest(BaseModel):
    question_id: int
    selected_option: str


class AssessmentSubmitRequest(BaseModel):
    answers: list[AssessmentAnswerRequest]


class AssessmentResultResponse(BaseModel):
    attempt_id: int
    assessment_id: int
    title: str

    score: int
    total_points: int
    percentage: int

    passed: bool

    answered_questions: int
    total_questions: int

    completed_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class AssessmentHistoryResponse(BaseModel):
    attempt_id: int
    assessment_id: int
    title: str
    score: int
    total_points: int
    percentage: int
    passed: bool
    completed_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )