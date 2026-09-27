from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.models.admin import Admin


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login"
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:

    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


# ============================================================
# ROLE CHECKING
# ============================================================

def require_role(*allowed_roles):

    def role_dependency(
        current_user: User = Depends(get_current_user),
    ) -> User:

        user_role = str(
            current_user.role
        ).lower()

        normalized_roles = [
            str(role).lower()
            for role in allowed_roles
        ]

        if user_role not in normalized_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )

        return current_user

    return role_dependency


# ============================================================
# ADMIN
# ============================================================

def require_admin(
    current_user: User = Depends(
        require_role("admin")
    ),
) -> User:

    return current_user


# ============================================================
# TRAINER
# ============================================================

def require_trainer(
    current_user: User = Depends(
        require_role("trainer")
    ),
) -> User:

    return current_user


# ============================================================
# TRAINEE
# ============================================================

def require_trainee(
    current_user: User = Depends(
        require_role("trainee")
    ),
) -> User:

    return current_user


# ============================================================
# ADMIN PROFILE
# ============================================================

def get_current_admin(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Admin:

    admin = (
        db.query(Admin)
        .filter(
            Admin.user_id == current_user.id
        )
        .first()
    )

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin profile is not configured for this account.",
        )

    return admin