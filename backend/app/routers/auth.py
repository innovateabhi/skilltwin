from datetime import timedelta

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

from app.schemas.auth import (
    ChangePasswordRequest,
    Token,
    UpdateProfileRequest,
    UserLogin,
    UserRegister,
    UserResponse,
)


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

    if role not in PUBLIC_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid account type",
        )

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

    if role == "institution":
        if not user_data.organization_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization name is required",
            )

    if role == "industry":
        if not user_data.company_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company name is required",
            )

    new_user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=role,
        is_active=True,
        is_verified=False,
    )

    db.add(new_user)
    db.flush()

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

    elif role == "institution":
        profile = Institution(
            user_id=new_user.id,
            organization_name=user_data.organization_name,
            organization_type=user_data.organization_type,
            official_email=user_data.official_email or user_data.email,
            phone=user_data.phone,
            website=user_data.website,
        )

        db.add(profile)

    elif role == "industry":
        profile = Industry(
            user_id=new_user.id,
            company_name=user_data.company_name,
            industry_type=user_data.industry_type,
            official_email=user_data.official_email or user_data.email,
            phone=user_data.phone,
            website=user_data.website,
        )

        db.add(profile)

    db.commit()
    db.refresh(new_user)

    return new_user


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

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

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


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.put(
    "/change-password",
)
def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(
        password_data.current_password,
        current_user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    if (
        password_data.current_password
        == password_data.new_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )

    current_user.password_hash = hash_password(
        password_data.new_password
    )

    db.commit()

    return {
        "message": "Password changed successfully",
    }