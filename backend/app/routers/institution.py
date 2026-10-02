from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user

router = APIRouter(
    prefix="/api/institution",
    tags=["Institution"],
)


@router.get("/profile")
def get_institution_profile(
    current_user=Depends(get_current_user),
):
    """
    Return the currently authenticated institution profile.
    """

    if current_user.role != "institution":
        raise HTTPException(
            status_code=403,
            detail="Institution access required.",
        )

    return {
        "profile": {
            "id": current_user.id,
            "email": current_user.email,
            "role": current_user.role,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "full_name": (
                f"{current_user.first_name or ''} "
                f"{current_user.last_name or ''}"
            ).strip(),
            "organization_name": getattr(
                current_user,
                "organization_name",
                None,
            ),
            "institution_name": getattr(
                current_user,
                "institution_name",
                None,
            ),
            "organization_type": getattr(
                current_user,
                "organization_type",
                None,
            ),
            "institution_type": getattr(
                current_user,
                "institution_type",
                None,
            ),
            "official_email": getattr(
                current_user,
                "official_email",
                None,
            ),
            "website": getattr(
                current_user,
                "website",
                None,
            ),
            "logo": getattr(
                current_user,
                "logo",
                None,
            ),
            "logo_url": getattr(
                current_user,
                "logo_url",
                None,
            ),
        }
    }