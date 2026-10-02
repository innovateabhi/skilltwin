from datetime import datetime

from pydantic import BaseModel


class CourseResponse(BaseModel):
    id: int
    title: str
    slug: str
    description: str | None
    instructor_name: str | None
    thumbnail_url: str | None
    level: str
    duration_hours: int
    status: str
    progress_percent: int
    completed_lessons: int
    total_lessons: int
    last_accessed_at: datetime | None

    class Config:
        from_attributes = True