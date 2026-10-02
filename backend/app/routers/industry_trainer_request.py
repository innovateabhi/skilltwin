from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.industry_trainer_request import IndustryTrainerRequest


router = APIRouter(
    prefix="/api/industry/trainers",
    tags=["Industry Trainer Requests"],
)


# ============================================================
# SCHEMAS
# ============================================================

class TrainerRequestCreate(BaseModel):
    trainer_id: int
    training_title: str = Field(
        ...,
        min_length=2,
        max_length=255,
    )
    message: str | None = None


# ============================================================
# HELPERS
# ============================================================

def require_industry(current_user: User):
    if current_user.role != "industry":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only industry users can access this resource",
        )

    return current_user


def serialize_request(
    request: IndustryTrainerRequest,
    db: Session,
):
    industry = (
        db.query(User)
        .filter(User.id == request.industry_id)
        .first()
    )

    trainer = (
        db.query(User)
        .filter(User.id == request.trainer_id)
        .first()
    )

    return {
        "id": request.id,
        "industry_id": request.industry_id,
        "trainer_id": request.trainer_id,

        "training_title": request.training_title,
        "message": request.message,

        "status": request.status,

        "created_at": request.created_at,
        "updated_at": request.updated_at,

        "industry": {
            "id": industry.id,
            "email": industry.email,
            "role": industry.role,
        }
        if industry
        else None,

        "trainer": {
            "id": trainer.id,
            "email": trainer.email,
            "role": trainer.role,
            "is_active": trainer.is_active,
            "is_verified": trainer.is_verified,
        }
        if trainer
        else None,
    }


# ============================================================
# GET INDUSTRY'S TRAINER REQUESTS
# ============================================================

@router.get("/requests")
def get_industry_trainer_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_industry(current_user)

    requests = (
        db.query(IndustryTrainerRequest)
        .filter(
            IndustryTrainerRequest.industry_id
            == current_user.id
        )
        .order_by(
            IndustryTrainerRequest.created_at.desc()
        )
        .all()
    )

    return [
        serialize_request(request, db)
        for request in requests
    ]


# ============================================================
# CREATE TRAINER REQUEST
# ============================================================

@router.post("/requests")
def create_industry_trainer_request(
    payload: TrainerRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_industry(current_user)

    # --------------------------------------------------------
    # Find trainer
    # --------------------------------------------------------

    trainer = (
        db.query(User)
        .filter(
            User.id == payload.trainer_id
        )
        .first()
    )

    if not trainer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trainer not found",
        )

    if trainer.role != "trainer":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected user is not a trainer",
        )

    if not trainer.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This trainer account is not active",
        )

    if not trainer.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This trainer is not verified",
        )

    # --------------------------------------------------------
    # Prevent duplicate pending request
    # --------------------------------------------------------

    existing_request = (
        db.query(IndustryTrainerRequest)
        .filter(
            IndustryTrainerRequest.industry_id
            == current_user.id,
            IndustryTrainerRequest.trainer_id
            == payload.trainer_id,
            IndustryTrainerRequest.status
            == "pending",
        )
        .first()
    )

    if existing_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a pending request for this trainer",
        )

    # --------------------------------------------------------
    # Create request
    # --------------------------------------------------------

    trainer_request = IndustryTrainerRequest(
        industry_id=current_user.id,
        trainer_id=payload.trainer_id,
        training_title=payload.training_title.strip(),
        message=payload.message.strip()
        if payload.message
        else None,
        status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(trainer_request)
    db.commit()
    db.refresh(trainer_request)

    return {
        "message": "Trainer request sent successfully",
        "request": serialize_request(
            trainer_request,
            db,
        ),
    }


# ============================================================
# CANCEL REQUEST
# ============================================================

@router.patch("/requests/{request_id}/cancel")
def cancel_industry_trainer_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_industry(current_user)

    trainer_request = (
        db.query(IndustryTrainerRequest)
        .filter(
            IndustryTrainerRequest.id == request_id,
            IndustryTrainerRequest.industry_id
            == current_user.id,
        )
        .first()
    )

    if not trainer_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trainer request not found",
        )

    if trainer_request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only pending requests can be cancelled"
            ),
        )

    trainer_request.status = "cancelled"
    trainer_request.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(trainer_request)

    return {
        "message": "Trainer request cancelled successfully",
        "request": serialize_request(
            trainer_request,
            db,
        ),
    }


# ============================================================
# GET SINGLE REQUEST
# ============================================================

@router.get("/requests/{request_id}")
def get_industry_trainer_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_industry(current_user)

    trainer_request = (
        db.query(IndustryTrainerRequest)
        .filter(
            IndustryTrainerRequest.id == request_id,
            IndustryTrainerRequest.industry_id
            == current_user.id,
        )
        .first()
    )

    if not trainer_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trainer request not found",
        )

    return serialize_request(
        trainer_request,
        db,
    )