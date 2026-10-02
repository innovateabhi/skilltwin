from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user

from app.models.user import User
from app.models.trainer import Trainer
from app.models.institution import Institution
from app.models.industry import Industry
from app.models.trainer_request import TrainerRequest


router = APIRouter(
    prefix="/api/trainer-requests",
    tags=["Trainer Requests"],
)


# ============================================================
# ADMIN AUTHORIZATION
# ============================================================

def require_admin(
    current_user: User,
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )

    return current_user


# ============================================================
# HELPERS
# ============================================================

def get_request_user(
    request: TrainerRequest,
    db: Session,
):
    return (
        db.query(User)
        .filter(User.id == request.user_id)
        .first()
    )


def build_request_response(
    request: TrainerRequest,
    user: User | None,
    db: Session,
):
    if not user:
        return {
            "id": request.id,
            "user_id": request.user_id,
            "status": request.status,
            "reason": request.reason,
            "reviewed_by": request.reviewed_by,
            "reviewed_at": request.reviewed_at,
            "created_at": request.created_at,
            "updated_at": request.updated_at,
            "user": None,
        }

    response = {
        "id": request.id,
        "user_id": request.user_id,
        "status": request.status,
        "reason": request.reason,
        "reviewed_by": request.reviewed_by,
        "reviewed_at": request.reviewed_at,
        "created_at": request.created_at,
        "updated_at": request.updated_at,

        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
        },

        # Backward-compatible fields
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
    }

    # --------------------------------------------------------
    # TRAINER
    # --------------------------------------------------------

    if user.role == "trainer":
        profile = (
            db.query(Trainer)
            .filter(
                Trainer.user_id == user.id
            )
            .first()
        )

        if profile:
            response.update(
                {
                    "first_name": profile.first_name,
                    "last_name": profile.last_name,
                    "full_name": (
                        f"{profile.first_name or ''} "
                        f"{profile.last_name or ''}"
                    ).strip(),
                    "phone": profile.phone,
                    "designation": profile.designation,
                    "specialization": profile.specialization,
                    "experience_years": profile.experience_years,
                    "organization": profile.organization,
                }
            )

    # --------------------------------------------------------
    # INSTITUTION
    # --------------------------------------------------------

    elif user.role == "institution":
        profile = (
            db.query(Institution)
            .filter(
                Institution.user_id == user.id
            )
            .first()
        )

        if profile:
            response.update(
                {
                    "organization_name": profile.organization_name,
                    "organization_type": profile.organization_type,
                    "official_email": profile.official_email,
                    "phone": profile.phone,
                    "website": profile.website,
                    "full_name": profile.organization_name,
                }
            )

    # --------------------------------------------------------
    # INDUSTRY
    # --------------------------------------------------------

    elif user.role == "industry":
        profile = (
            db.query(Industry)
            .filter(
                Industry.user_id == user.id
            )
            .first()
        )

        if profile:
            response.update(
                {
                    "company_name": profile.company_name,
                    "industry_type": profile.industry_type,
                    "official_email": profile.official_email,
                    "phone": profile.phone,
                    "website": profile.website,
                    "full_name": profile.company_name,
                }
            )

    return response


# ============================================================
# TRAINER - GET OWN REQUEST
# ============================================================

@router.get("/me")
def get_my_trainer_request(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "trainer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only trainers can access trainer requests",
        )

    trainer_request = (
        db.query(TrainerRequest)
        .filter(
            TrainerRequest.user_id == current_user.id
        )
        .first()
    )

    if not trainer_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trainer request not found",
        )

    return build_request_response(
        trainer_request,
        current_user,
        db,
    )


# ============================================================
# TRAINER - RESUBMIT REJECTED REQUEST
# ============================================================

@router.post("/resubmit")
def resubmit_trainer_request(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "trainer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only trainers can resubmit trainer requests",
        )

    trainer_request = (
        db.query(TrainerRequest)
        .filter(
            TrainerRequest.user_id == current_user.id
        )
        .first()
    )

    if not trainer_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trainer request not found",
        )

    if trainer_request.status == "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your trainer request is already pending",
        )

    if trainer_request.status == "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your trainer account is already approved",
        )

    trainer_request.status = "pending"
    trainer_request.reason = None
    trainer_request.reviewed_by = None
    trainer_request.reviewed_at = None

    current_user.is_verified = False
    current_user.is_active = True

    db.commit()
    db.refresh(trainer_request)

    return {
        "message": "Trainer request resubmitted successfully",
        "request": build_request_response(
            trainer_request,
            current_user,
            db,
        ),
    }


# ============================================================
# ADMIN - ALL REQUESTS
# ============================================================

@router.get("")
def get_all_trainer_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_admin(current_user)

    requests = (
        db.query(TrainerRequest)
        .order_by(
            TrainerRequest.created_at.desc()
        )
        .all()
    )

    return [
        build_request_response(
            request,
            get_request_user(request, db),
            db,
        )
        for request in requests
    ]


# ============================================================
# ADMIN - PENDING REQUESTS
# ============================================================

@router.get("/pending")
def get_pending_trainer_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_admin(current_user)

    requests = (
        db.query(TrainerRequest)
        .filter(
            TrainerRequest.status == "pending"
        )
        .order_by(
            TrainerRequest.created_at.asc()
        )
        .all()
    )

    return [
        build_request_response(
            request,
            get_request_user(request, db),
            db,
        )
        for request in requests
    ]


# ============================================================
# ADMIN - APPROVE
# ============================================================

@router.post("/{request_id}/approve")
def approve_trainer_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_admin(current_user)

    approval_request = (
        db.query(TrainerRequest)
        .filter(
            TrainerRequest.id == request_id
        )
        .first()
    )

    if not approval_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration request not found",
        )

    if approval_request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending requests can be approved",
        )

    user = get_request_user(
        approval_request,
        db,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found",
        )

    if user.role not in {
        "trainer",
        "institution",
        "industry",
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account type cannot be approved through registration requests",
        )

    approval_request.status = "approved"
    approval_request.reason = None
    approval_request.reviewed_by = current_user.id
    approval_request.reviewed_at = datetime.utcnow()

    user.is_verified = True
    user.is_active = True

    db.commit()

    db.refresh(approval_request)
    db.refresh(user)

    role_name = {
        "trainer": "Trainer",
        "institution": "Institution",
        "industry": "Industry",
    }.get(
        user.role,
        "Registration",
    )

    return {
        "message": f"{role_name} request approved successfully",

        "request": {
            "id": approval_request.id,
            "user_id": approval_request.user_id,
            "status": approval_request.status,
            "reviewed_by": approval_request.reviewed_by,
            "reviewed_at": approval_request.reviewed_at,
        },

        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
        },
    }


# ============================================================
# ADMIN - REJECT
# ============================================================

@router.post("/{request_id}/reject")
def reject_trainer_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_admin(current_user)

    rejection_request = (
        db.query(TrainerRequest)
        .filter(
            TrainerRequest.id == request_id
        )
        .first()
    )

    if not rejection_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration request not found",
        )

    if rejection_request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending requests can be rejected",
        )

    user = get_request_user(
        rejection_request,
        db,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found",
        )

    if user.role not in {
        "trainer",
        "institution",
        "industry",
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account type cannot be rejected through registration requests",
        )

    rejection_request.status = "rejected"

    rejection_request.reason = (
        f"{user.role.capitalize()} application "
        "rejected by administrator."
    )

    rejection_request.reviewed_by = current_user.id
    rejection_request.reviewed_at = datetime.utcnow()

    user.is_verified = False

    db.commit()

    db.refresh(rejection_request)
    db.refresh(user)

    role_name = {
        "trainer": "Trainer",
        "institution": "Institution",
        "industry": "Industry",
    }.get(
        user.role,
        "Registration",
    )

    return {
        "message": f"{role_name} request rejected successfully",

        "request": {
            "id": rejection_request.id,
            "user_id": rejection_request.user_id,
            "status": rejection_request.status,
            "reason": rejection_request.reason,
            "reviewed_by": rejection_request.reviewed_by,
            "reviewed_at": rejection_request.reviewed_at,
        },

        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
        },
    }