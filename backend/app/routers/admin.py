from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin, get_current_admin
from app.models.user import User
from app.models.admin import Admin


router = APIRouter(
    prefix="/api/admin",
    tags=["Admin Portal"],
)


# ============================================================
# ADMIN PROFILE
# ============================================================

@router.get("/me")
def get_admin_profile(
    current_user: User = Depends(require_admin),
    admin: Admin = Depends(get_current_admin),
):
    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "role": current_user.role,
            "is_active": current_user.is_active,
            "is_verified": current_user.is_verified,
        },
        "admin": {
            "id": admin.id,
            "user_id": admin.user_id,
            "first_name": admin.first_name,
            "last_name": admin.last_name,
            "phone": admin.phone,
            "designation": admin.designation,
            "permissions": admin.permissions,
            "created_at": admin.created_at,
            "updated_at": admin.updated_at,
        },
    }


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@router.get("/dashboard")
def admin_dashboard(
    current_user: User = Depends(require_admin),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    total_users = db.query(User).count()

    total_trainees = (
        db.query(User)
        .filter(User.role == "trainee")
        .count()
    )

    total_trainers = (
        db.query(User)
        .filter(User.role == "trainer")
        .count()
    )

    active_users = (
        db.query(User)
        .filter(User.is_active == True)
        .count()
    )

    return {
        "admin": {
            "id": admin.id,
            "name": f"{admin.first_name} {admin.last_name or ''}".strip(),
            "designation": admin.designation,
        },
        "statistics": {
            "total_users": total_users,
            "total_trainees": total_trainees,
            "total_trainers": total_trainers,
            "active_users": active_users,
        },
    }


# ============================================================
# ALL USERS
# ============================================================

@router.get("/users")
def get_users(
    current_user: User = Depends(require_admin),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    users = (
        db.query(User)
        .order_by(User.id.desc())
        .all()
    )

    return [
        {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }
        for user in users
    ]


# ============================================================
# TRAINER REQUESTS
# ============================================================

@router.get("/trainer-requests")
def get_trainer_requests(
    current_user: User = Depends(require_admin),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Return trainer registration requests.

    The request table is joined with users and trainers so
    the admin portal receives useful information in one response.
    """

    rows = db.execute(
        text(
            """
            SELECT
                tr.id,
                tr.user_id,
                tr.status,
                tr.reason,
                tr.reviewed_by,
                tr.reviewed_at,
                tr.created_at,
                tr.updated_at,

                u.email,
                u.is_active,
                u.is_verified,

                t.id AS trainer_id,
                t.first_name,
                t.last_name,
                t.phone,
                t.designation,
                t.specialization,
                t.experience_years,
                t.organization,
                t.bio,
                t.profile_image

            FROM trainer_requests tr

            INNER JOIN users u
                ON u.id = tr.user_id

            LEFT JOIN trainers t
                ON t.user_id = tr.user_id

            ORDER BY
                CASE
                    WHEN tr.status = 'pending' THEN 0
                    WHEN tr.status = 'approved' THEN 1
                    ELSE 2
                END,
                tr.created_at DESC
            """
        )
    ).mappings().all()

    return [dict(row) for row in rows]


# ============================================================
# APPROVE TRAINER
# ============================================================

@router.patch("/trainer-requests/{user_id}/approve")
def approve_trainer(
    user_id: int,
    current_user: User = Depends(require_admin),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Approve a trainer request.

    Actions:
    1. Validate trainer request.
    2. Activate the user.
    3. Mark request approved.
    4. Create trainer profile if it does not already exist.
    """

    request = db.execute(
        text(
            """
            SELECT *
            FROM trainer_requests
            WHERE user_id = :user_id
            LIMIT 1
            """
        ),
        {"user_id": user_id},
    ).mappings().first()

    if not request:
        raise HTTPException(
            status_code=404,
            detail="Trainer request not found.",
        )

    if request["status"] == "approved":
        return {
            "message": "Trainer request is already approved.",
            "user_id": user_id,
        }

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    if str(user.role).lower() != "trainer":
        raise HTTPException(
            status_code=400,
            detail="This user is not registered as a trainer.",
        )

    # --------------------------------------------------------
    # Activate user
    # --------------------------------------------------------

    user.is_active = True

    # --------------------------------------------------------
    # Check whether trainer profile already exists
    # --------------------------------------------------------

    trainer = db.execute(
        text(
            """
            SELECT *
            FROM trainers
            WHERE user_id = :user_id
            LIMIT 1
            """
        ),
        {"user_id": user_id},
    ).mappings().first()

    # --------------------------------------------------------
    # If no trainer profile exists, create a basic one.
    #
    # Existing profile information can be filled later from
    # the trainer's profile page.
    # --------------------------------------------------------

    if not trainer:

        email_name = (
            user.email.split("@")[0]
            if user.email
            else "Trainer"
        )

        db.execute(
            text(
                """
                INSERT INTO trainers (
                    user_id,
                    first_name,
                    last_name,
                    phone,
                    designation,
                    specialization,
                    experience_years,
                    organization,
                    bio,
                    profile_image
                )
                VALUES (
                    :user_id,
                    :first_name,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL,
                    NULL
                )
                """
            ),
            {
                "user_id": user_id,
                "first_name": email_name[:100],
            },
        )

    # --------------------------------------------------------
    # Approve request
    # --------------------------------------------------------

    db.execute(
        text(
            """
            UPDATE trainer_requests
            SET
                status = 'approved',
                reviewed_by = :reviewed_by,
                reviewed_at = CURRENT_TIMESTAMP,
                reason = NULL
            WHERE user_id = :user_id
            """
        ),
        {
            "user_id": user_id,
            "reviewed_by": current_user.id,
        },
    )

    db.commit()

    return {
        "message": "Trainer request approved successfully.",
        "user_id": user_id,
        "status": "approved",
    }


# ============================================================
# REJECT TRAINER
# ============================================================

@router.patch("/trainer-requests/{user_id}/reject")
def reject_trainer(
    user_id: int,
    payload: dict | None = None,
    current_user: User = Depends(require_admin),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Reject a trainer request.

    Optional JSON:
    {
        "reason": "Reason for rejection"
    }
    """

    payload = payload or {}

    reason = str(
        payload.get("reason")
        or "Trainer request rejected by administrator."
    ).strip()

    request = db.execute(
        text(
            """
            SELECT *
            FROM trainer_requests
            WHERE user_id = :user_id
            LIMIT 1
            """
        ),
        {"user_id": user_id},
    ).mappings().first()

    if not request:
        raise HTTPException(
            status_code=404,
            detail="Trainer request not found.",
        )

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    # --------------------------------------------------------
    # Deactivate account
    # --------------------------------------------------------

    user.is_active = False

    # --------------------------------------------------------
    # Mark request rejected
    # --------------------------------------------------------

    db.execute(
        text(
            """
            UPDATE trainer_requests
            SET
                status = 'rejected',
                reason = :reason,
                reviewed_by = :reviewed_by,
                reviewed_at = CURRENT_TIMESTAMP
            WHERE user_id = :user_id
            """
        ),
        {
            "user_id": user_id,
            "reason": reason,
            "reviewed_by": current_user.id,
        },
    )

    db.commit()

    return {
        "message": "Trainer request rejected.",
        "user_id": user_id,
        "status": "rejected",
        "reason": reason,
    }


# ============================================================
# TRAINERS
# ============================================================

@router.get("/trainers")
def get_trainers(
    current_user: User = Depends(require_admin),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Return all trainer profiles together with their user account
    information and approval/request status.
    """

    rows = db.execute(
        text(
            """
            SELECT
                t.id,
                t.user_id,

                t.first_name,
                t.last_name,
                t.phone,
                t.designation,
                t.specialization,
                t.experience_years,
                t.organization,
                t.bio,
                t.profile_image,
                t.created_at,
                t.updated_at,

                u.email,
                u.is_active,
                u.is_verified,

                COALESCE(tr.status, 'approved') AS request_status,
                tr.reason AS request_reason,
                tr.reviewed_at

            FROM trainers t

            INNER JOIN users u
                ON u.id = t.user_id

            LEFT JOIN trainer_requests tr
                ON tr.user_id = t.user_id

            ORDER BY t.created_at DESC
            """
        )
    ).mappings().all()

    return [dict(row) for row in rows]


# ============================================================
# TRAINEES
# ============================================================

@router.get("/trainees")
def get_trainees(
    current_user: User = Depends(require_admin),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(User)
        .filter(User.role == "trainee")
        .order_by(User.id.desc())
        .all()
    )

    return [
        {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }
        for user in rows
    ]