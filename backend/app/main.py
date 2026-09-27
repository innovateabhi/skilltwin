from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers.auth import router as auth_router
from app.routers.trainee import router as trainee_router
from app.routers.catalog import router as catalog_router
from app.routers.assessment import router as assessment_router

from app.routers.course import router as course_router
from app.routers.payment import router as payment_router
from app.routers.course_marketplace import router as course_marketplace_router

from app.routers.ai_tutor import router as ai_tutor_router

from app.routers.ai_interview import router as ai_interview_router
from app.routers.ai_resume import router as ai_resume_router

from app.core.dependencies import get_current_user
from app.routers.trainer import build_trainer_router

from app.routers.admin import router as admin_router

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(catalog_router)
app.include_router(trainee_router)
app.include_router(assessment_router)
app.include_router(course_router)
app.include_router(payment_router)
app.include_router(course_marketplace_router)
app.include_router(ai_tutor_router)
app.include_router(ai_interview_router)
app.include_router(ai_resume_router)
app.include_router(build_trainer_router(get_current_user))
app.include_router(admin_router)

@app.get("/")
def root():
    return {
        "message": "SkillTwin API is running",
        "version": "0.1.0",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }

