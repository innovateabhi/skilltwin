from datetime import datetime

from pydantic import BaseModel, Field


class TrainerProfileUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    designation: str | None = Field(default=None, max_length=150)
    specialization: str | None = Field(default=None, max_length=150)
    experience_years: float | None = Field(default=None, ge=0, le=999.9)
    organization: str | None = Field(default=None, max_length=255)
    bio: str | None = None
    profile_image: str | None = Field(default=None, max_length=500)


class QuestionnaireCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    deadline: datetime | None = None
    course_id: int | None = None


class QuestionnaireQuestionCreate(BaseModel):
    question: str = Field(..., min_length=1)
    options: list[str] = Field(default_factory=list)
    correct_answer: str | None = None
    marks: float = Field(default=1, ge=0)


class CompetencyCreate(BaseModel):
    competency_id: int | None = None
    competency_name: str = Field(..., min_length=1, max_length=255)
    level: str | None = Field(default=None, max_length=50)


class NotificationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    recipient_user_id: int | None = None