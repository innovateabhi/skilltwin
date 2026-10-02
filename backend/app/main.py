from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

# ============================================================
# CORE / AUTH
# ============================================================

from app.core.dependencies import get_current_user

from app.routers.auth import router as auth_router


# ============================================================
# TRAINEE / LEARNING
# ============================================================

from app.routers.trainee import router as trainee_router
from app.routers.catalog import router as catalog_router
from app.routers.assessment import router as assessment_router

from app.routers.course import router as course_router
from app.routers.payment import router as payment_router
from app.routers.course_marketplace import (
    router as course_marketplace_router
)


# ============================================================
# AI
# ============================================================

from app.routers.ai_tutor import router as ai_tutor_router
from app.routers.ai_interview import router as ai_interview_router
from app.routers.ai_resume import router as ai_resume_router


# ============================================================
# TRAINER
# ============================================================

from app.routers.trainer import build_trainer_router

from app.routers.trainer_request import (
    router as trainer_request_router
)


# ============================================================
# ADMIN
# ============================================================

from app.routers.admin import router as admin_router


# ============================================================
# INDUSTRY
# ============================================================

from app.routers.industry_trainer_request import (
    router as industry_trainer_request_router
)

from app.routers.industry import (
    router as industry_router
)


# INSTITUTION
from app.routers.institution import (
    router as institution_router
)

# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# AUTH ROUTES
# ============================================================

app.include_router(auth_router)


# ============================================================
# TRAINEE / LEARNING ROUTES
# ============================================================

app.include_router(catalog_router)
app.include_router(trainee_router)
app.include_router(assessment_router)

app.include_router(course_router)
app.include_router(payment_router)
app.include_router(course_marketplace_router)


# ============================================================
# AI ROUTES
# ============================================================

app.include_router(ai_tutor_router)
app.include_router(ai_interview_router)
app.include_router(ai_resume_router)


# ============================================================
# TRAINER ROUTES
# ============================================================

app.include_router(
    build_trainer_router(get_current_user)
)


# ============================================================
# ADMIN ROUTES
# ============================================================

app.include_router(admin_router)

# Trainer account verification:
# Trainer → Admin → Approve / Reject
app.include_router(trainer_request_router)


# ============================================================
# INDUSTRY ROUTES
# ============================================================

# IMPORTANT:
# Industry trainer-request routes MUST be registered
# BEFORE the general industry routes.
#
# Otherwise:
#
# /api/industry/trainers/requests
#
# can be interpreted by:
#
# /api/industry/trainers/{trainer_id}
#
# as:
#
# trainer_id = "requests"
#
# which causes FastAPI to return HTTP 422.

app.include_router(
    industry_trainer_request_router
)

app.include_router(
    industry_router
)

app.include_router(institution_router)
# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "message": "SkillTwin API is running",
        "version": "0.1.0",
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }

