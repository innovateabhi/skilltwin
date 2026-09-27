from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class TraineeProfileResponse(BaseModel):
    id: int
    user_id: int
    first_name: str
    last_name: str | None = None
    phone: str | None = None
    date_of_birth: date | None = None
    institution_name: str | None = None
    education_level: str | None = None
    specialization: str | None = None
    target_role: str | None = None
    profile_image: str | None = None
    bio: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TraineeCompetencyResponse(BaseModel):
    id: int
    competency_id: int
    competency_name: str
    competency_description: str | None = None

    skill_id: int
    skill_name: str

    current_score: int
    target_score: int
    gap_score: int
    last_assessed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TraineeSkillResponse(BaseModel):
    skill_id: int
    skill_name: str
    skill_slug: str

    category_id: int
    category_name: str

    domain_id: int
    domain_name: str

    current_score: int
    target_score: int
    gap_score: int

    competency_count: int


class TraineeGapResponse(BaseModel):
    id: int
    skill_id: int
    skill_name: str
    skill_slug: str

    current_score: int
    target_score: int
    gap_score: int
    severity: str
    status: str
    calculated_at: datetime


class TraineeHistoryResponse(BaseModel):
    id: int
    competency_id: int
    competency_name: str
    score: int
    previous_score: int | None = None
    improvement: int
    source: str
    reference_id: int | None = None
    recorded_at: datetime


class DashboardStats(BaseModel):
    total_competencies: int
    assessed_competencies: int
    average_score: int
    skills_with_gaps: int
    critical_gaps: int
    learning_progress: int


class TraineeDashboardResponse(BaseModel):
    profile: TraineeProfileResponse
    stats: DashboardStats
    competencies: list[TraineeCompetencyResponse]
    gaps: list[TraineeGapResponse]
    recent_history: list[TraineeHistoryResponse]