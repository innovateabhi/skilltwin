from datetime import timedelta
import logging
import traceback

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)

from app.models.user import User
from app.models.trainee import Trainee
from app.models.trainer import Trainer
from app.models.institution import Institution
from app.models.industry import Industry
from app.models.trainer_request import TrainerRequest

from app.schemas.auth import (
    ChangePasswordRequest,
    Token,
    UserLogin,
    UserRegister,
    UserResponse,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


PUBLIC_ROLES = {
    "trainee",
    "trainer",
    "institution",
    "industry",
}


# ============================================================
# REGISTER
# ============================================================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db),
):
    role = user_data.role.strip().lower()

    # --------------------------------------------------------
    # Validate role
    # --------------------------------------------------------

    if role not in PUBLIC_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid account type",
        )

    # --------------------------------------------------------
    # Check duplicate email
    # --------------------------------------------------------

    existing_user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered",
        )

    # --------------------------------------------------------
    # Validate trainee / trainer
    # --------------------------------------------------------

    if role in {"trainee", "trainer"}:

        if not user_data.first_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="First name is required",
            )

        if not user_data.last_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Last name is required",
            )

    # --------------------------------------------------------
    # Validate institution
    # --------------------------------------------------------

    if role == "institution":

        if not user_data.organization_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization name is required",
            )

    # --------------------------------------------------------
    # Validate industry
    # --------------------------------------------------------

    if role == "industry":

        if not user_data.company_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company name is required",
            )

    # --------------------------------------------------------
    # Create user
    #
    # Trainer / Institution / Industry are created as
    # unverified accounts and must be approved by admin.
    # --------------------------------------------------------

    new_user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=role,
        is_active=True,
        is_verified=False,
    )

    db.add(new_user)

    # Generate user ID before creating dependent records
    db.flush()

    # --------------------------------------------------------
    # TRAINEE PROFILE
    # --------------------------------------------------------

    if role == "trainee":

        profile = Trainee(
            user_id=new_user.id,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
            institution_name=user_data.institution_name,
            education_level=user_data.education_level,
            specialization=user_data.specialization,
            target_role=user_data.target_role,
        )

        db.add(profile)

    # --------------------------------------------------------
    # TRAINER PROFILE
    # --------------------------------------------------------

    elif role == "trainer":

        profile = Trainer(
            user_id=new_user.id,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
            designation=user_data.designation,
            specialization=user_data.specialization,
            experience_years=user_data.experience_years,
            organization=user_data.organization,
        )

        db.add(profile)

    # --------------------------------------------------------
    # INSTITUTION PROFILE
    # --------------------------------------------------------

    elif role == "institution":

        profile = Institution(
            user_id=new_user.id,
            organization_name=user_data.organization_name,
            organization_type=user_data.organization_type,
            official_email=(
                user_data.official_email
                or user_data.email
            ),
            phone=user_data.phone,
            website=user_data.website,
        )

        db.add(profile)

    # --------------------------------------------------------
    # INDUSTRY PROFILE
    # --------------------------------------------------------

    elif role == "industry":

        profile = Industry(
            user_id=new_user.id,
            company_name=user_data.company_name,
            industry_type=user_data.industry_type,
            official_email=(
                user_data.official_email
                or user_data.email
            ),
            phone=user_data.phone,
            website=user_data.website,
        )

        db.add(profile)

    # --------------------------------------------------------
    # CREATE ADMIN APPROVAL REQUEST
    #
    # For now, TrainerRequest is reused for:
    #
    # trainer
    # institution
    # industry
    #
    # The existing Admin "Trainer Requests" section can
    # therefore handle all three account types.
    # --------------------------------------------------------

    if role in {"trainer", "institution", "industry"}:

        approval_request = TrainerRequest(
            user_id=new_user.id,
            status="pending",
        )

        db.add(approval_request)

    # --------------------------------------------------------
    # Commit
    # --------------------------------------------------------

    try:

        db.commit()
        db.refresh(new_user)

    except Exception as e:

        db.rollback()

        # ----------------------------------------------------
        # TEMPORARY DEBUG LOGGING
        # ----------------------------------------------------
        # This prints the actual database/SQLAlchemy error
        # into journalctl so we can identify the exact cause
        # of the registration failure.
        # ----------------------------------------------------

        logger.error(
            "REGISTER DATABASE ERROR: %r",
            e,
            exc_info=True,
        )

        traceback.print_exc()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create account",
        )

    return new_user


# ============================================================
# LOGIN
# ============================================================

@router.post(
    "/login",
    response_model=Token,
)
def login(
    user_data: UserLogin,
    db: Session = Depends(get_db),
):

    user = (
        db.query(User)
        .filter(User.email == user_data.email)
        .first()
    )

    # --------------------------------------------------------
    # Invalid credentials
    # --------------------------------------------------------

    if not user or not verify_password(
        user_data.password,
        user.password_hash,
    ):

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    # --------------------------------------------------------
    # Inactive account
    # --------------------------------------------------------

    if not user.is_active:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # --------------------------------------------------------
    # ADMIN APPROVAL
    #
    # Trainer, Institution and Industry accounts must be
    # approved by the administrator before login.
    # --------------------------------------------------------

    if (
        user.role in {"trainer", "institution", "industry"}
        and not user.is_verified
    ):

        role_name = {
            "trainer": "trainer",
            "institution": "institution",
            "industry": "industry",
        }.get(
            user.role,
            "account",
        )

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Your {role_name} profile is pending "
                "administrator approval. "
                "You will be able to login once your "
                "profile is approved."
            ),
        )

    # --------------------------------------------------------
    # Create JWT
    # --------------------------------------------------------

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role,
        },
        expires_delta=timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


# ============================================================
# CURRENT USER
# ============================================================

@router.get(
    "/me",
)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return the authenticated user together with
    role-specific profile information.
    """

    response = {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
    }

    # ========================================================
    # TRAINEE PROFILE
    # ========================================================

    if current_user.role == "trainee":

        profile = (
            db.query(Trainee)
            .filter(
                Trainee.user_id == current_user.id
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
                    "institution_name": profile.institution_name,
                    "education_level": profile.education_level,
                    "specialization": profile.specialization,
                    "target_role": profile.target_role,
                }
            )

    # ========================================================
    # TRAINER PROFILE
    # ========================================================

    elif current_user.role == "trainer":

        profile = (
            db.query(Trainer)
            .filter(
                Trainer.user_id == current_user.id
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

    # ========================================================
    # INSTITUTION PROFILE
    # ========================================================

    elif current_user.role == "institution":

        profile = (
            db.query(Institution)
            .filter(
                Institution.user_id == current_user.id
            )
            .first()
        )

        if profile:

            response.update(
                {
                    "institution_id": profile.id,
                    "organization_name": profile.organization_name,
                    "organization_type": profile.organization_type,
                    "official_email": profile.official_email,
                    "phone": profile.phone,
                    "website": profile.website,
                }
            )

    # ========================================================
    # INDUSTRY PROFILE
    # ========================================================

    elif current_user.role == "industry":

        profile = (
            db.query(Industry)
            .filter(
                Industry.user_id == current_user.id
            )
            .first()
        )

        if profile:

            response.update(
                {
                    "industry_id": profile.id,
                    "company_name": profile.company_name,
                    "industry_type": profile.industry_type,
                    "official_email": profile.official_email,
                    "phone": profile.phone,
                    "website": profile.website,
                }
            )

    return response


# ============================================================
# CHANGE PASSWORD
# ============================================================

@router.put(
    "/change-password",
)
def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    # --------------------------------------------------------
    # Verify current password
    # --------------------------------------------------------

    if not verify_password(
        password_data.current_password,
        current_user.password_hash,
    ):

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # --------------------------------------------------------
    # Ensure new password is different
    # --------------------------------------------------------

    if (
        password_data.current_password
        == password_data.new_password
    ):

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "New password must be different "
                "from current password"
            ),
        )

    # --------------------------------------------------------
    # Update password
    # --------------------------------------------------------

    current_user.password_hash = hash_password(
        password_data.new_password
    )

    db.commit()

    return {
        "message": "Password changed successfully",
    }
