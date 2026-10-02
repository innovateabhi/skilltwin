from datetime import datetime

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
# HELPERS
# ============================================================

def table_exists(
    db: Session,
    table_name: str,
) -> bool:
    """
    Check whether a table exists in the current database.
    """
    result = db.execute(
        text(
            """
            SELECT COUNT(*) AS count
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name = :table_name
            """
        ),
        {
            "table_name": table_name,
        },
    ).scalar()

    return bool(result)


def table_columns(
    db: Session,
    table_name: str,
) -> list[str]:
    """
    Return column names for a table.
    """
    if not table_exists(db, table_name):
        return []

    rows = db.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = :table_name
            ORDER BY ordinal_position
            """
        ),
        {
            "table_name": table_name,
        },
    ).scalars().all()

    return list(rows)


def safe_select_all(
    db: Session,
    table_name: str,
    order_candidates: tuple[str, ...] = (
        "created_at",
        "updated_at",
        "id",
    ),
):
    """
    Safely return all rows from a table.
    If the table does not exist, return [].
    """
    if not table_exists(db, table_name):
        return []

    columns = table_columns(db, table_name)

    if not columns:
        return []

    order_column = next(
        (
            column
            for column in order_candidates
            if column in columns
        ),
        None,
    )

    if order_column:
        sql = text(
            f"""
            SELECT *
            FROM `{table_name}`
            ORDER BY `{order_column}` DESC
            """
        )
    else:
        sql = text(
            f"""
            SELECT *
            FROM `{table_name}`
            """
        )

    rows = db.execute(sql).mappings().all()

    return [dict(row) for row in rows]


def safe_count(
    db: Session,
    table_name: str,
) -> int:
    """
    Safely count rows in a table.
    """
    if not table_exists(db, table_name):
        return 0

    result = db.execute(
        text(
            f"""
            SELECT COUNT(*) AS count
            FROM `{table_name}`
            """
        )
    ).scalar()

    return int(result or 0)


def pick_column(
    columns: list[str],
    *candidates: str,
):
    """
    Return the first candidate that exists.
    """
    for candidate in candidates:
        if candidate in columns:
            return candidate

    return None


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

    total_institutions = (
        db.query(User)
        .filter(User.role == "institution")
        .count()
    )

    total_industries = (
        db.query(User)
        .filter(User.role == "industry")
        .count()
    )

    # Courses
    total_courses = safe_count(
        db,
        "courses",
    )

    # Assessments
    if table_exists(db, "assessments"):
        total_assessments = safe_count(
            db,
            "assessments",
        )
    elif table_exists(db, "trainer_questionnaires"):
        total_assessments = safe_count(
            db,
            "trainer_questionnaires",
        )
    elif table_exists(db, "questionnaires"):
        total_assessments = safe_count(
            db,
            "questionnaires",
        )
    else:
        total_assessments = 0

    # Certifications
    if table_exists(db, "certifications"):
        total_certifications = safe_count(
            db,
            "certifications",
        )
    elif table_exists(db, "certificates"):
        total_certifications = safe_count(
            db,
            "certificates",
        )
    elif table_exists(db, "trainee_certifications"):
        total_certifications = safe_count(
            db,
            "trainee_certifications",
        )
    else:
        total_certifications = 0

    # Pending approval requests
    pending_trainer_requests = 0

    if table_exists(db, "trainer_requests"):
        pending_trainer_requests = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM trainer_requests
                WHERE status = 'pending'
                """
            )
        ).scalar() or 0

    total_users = db.query(User).count()

    active_users = (
        db.query(User)
        .filter(User.is_active == True)
        .count()
    )

    return {
        "admin": {
            "id": admin.id,
            "name": (
                f"{admin.first_name or ''} "
                f"{admin.last_name or ''}"
            ).strip(),
            "designation": admin.designation,
        },

        "stats": {
            "trainees": total_trainees,
            "trainers": total_trainers,
            "institutions": total_institutions,
            "industries": total_industries,
            "courses": total_courses,
            "assessments": total_assessments,
            "certifications": total_certifications,
            "pendingTrainerRequests": int(
                pending_trainer_requests
            ),
        },

        # Keep these too for compatibility
        # with any other existing frontend code.
        "statistics": {
            "total_users": total_users,
            "total_trainees": total_trainees,
            "total_trainers": total_trainers,
            "total_institutions": total_institutions,
            "total_industries": total_industries,
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
    request = db.execute(
        text(
            """
            SELECT *
            FROM trainer_requests
            WHERE user_id = :user_id
            LIMIT 1
            """
        ),
        {
            "user_id": user_id,
        },
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

    if str(user.role).lower() != "trainer":
        raise HTTPException(
            status_code=400,
            detail="This user is not registered as a trainer.",
        )

    if request["status"] == "approved":
        return {
            "message": "Trainer request is already approved.",
            "user_id": user_id,
            "status": "approved",
            "is_active": user.is_active,
            "is_verified": user.is_verified,
        }

    # --------------------------------------------------------
    # APPROVE USER
    # --------------------------------------------------------

    user.is_active = True
    user.is_verified = True

    # --------------------------------------------------------
    # UPDATE TRAINER REQUEST
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
        "is_active": True,
        "is_verified": True,
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
        {
            "user_id": user_id,
        },
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

    if str(user.role).lower() != "trainer":
        raise HTTPException(
            status_code=400,
            detail="This user is not registered as a trainer.",
        )

    # --------------------------------------------------------
    # REJECT USER
    #
    # Keep account active so trainer can:
    # 1. Login
    # 2. See rejection status/reason
    # 3. Resubmit application
    #
    # is_verified remains FALSE, so protected trainer
    # functionality must still be blocked.
    # --------------------------------------------------------

    user.is_active = True
    user.is_verified = False

    # --------------------------------------------------------
    # UPDATE TRAINER REQUEST
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
        "is_active": True,
        "is_verified": False,
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

                COALESCE(
                    tr.status,
                    'approved'
                ) AS request_status,

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
    """
    Return complete trainee profiles for the Admin Portal.

    Combines:
        users
        trainees

    so the frontend receives:
        first_name
        last_name
        email
        institution_name
        education_level
        specialization
        target_role
        etc.
    """

    rows = db.execute(
        text(
            """
            SELECT
                t.id AS trainee_id,
                t.user_id,

                t.first_name,
                t.last_name,
                t.phone,
                t.institution_name,
                t.education_level,
                t.specialization,
                t.target_role,
                t.bio,
                t.profile_image,

                t.created_at AS trainee_created_at,
                t.updated_at AS trainee_updated_at,

                u.id,
                u.email,
                u.role,
                u.is_active,
                u.is_verified,
                u.created_at,
                u.updated_at

            FROM trainees t

            INNER JOIN users u
                ON u.id = t.user_id

            ORDER BY t.created_at DESC
            """
        )
    ).mappings().all()

    return [dict(row) for row in rows]


# ============================================================
# INSTITUTIONS
# ============================================================

@router.get("/institutions")
def get_admin_institutions(
    current_user: User = Depends(require_admin),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Return institution profiles for the Admin Portal.
    Uses the existing institutions table.
    """

    if not table_exists(db, "institutions"):
        return []

    rows = db.execute(
        text(
            """
            SELECT
                i.id,
                i.user_id,
                i.organization_name,
                i.organization_type,
                i.registration_number,
                i.official_email,
                i.phone,
                i.website,
                i.address,
                i.city,
                i.state,
                i.country,
                i.description,
                i.logo,
                i.created_at,
                i.updated_at,

                u.is_active,
                u.is_verified

            FROM institutions i

            LEFT JOIN users u
                ON u.id = i.user_id

            ORDER BY i.created_at DESC
            """
        )
    ).mappings().all()

    return [dict(row) for row in rows]


# ============================================================
# INDUSTRIES
# ============================================================

@router.get("/industries")
def get_admin_industries(
    current_user: User = Depends(require_admin),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Return industry/company profiles for the Admin Portal.
    Uses the existing industries table.
    """

    if not table_exists(db, "industries"):
        return []

    rows = db.execute(
        text(
            """
            SELECT
                i.id,
                i.user_id,
                i.company_name,
                i.industry_type,
                i.registration_number,
                i.official_email,
                i.phone,
                i.website,
                i.address,
                i.city,
                i.state,
                i.country,
                i.description,
                i.logo,
                i.created_at,
                i.updated_at,

                u.is_active,
                u.is_verified

            FROM industries i

            LEFT JOIN users u
                ON u.id = i.user_id

            ORDER BY i.created_at DESC
            """
        )
    ).mappings().all()

    return [dict(row) for row in rows]


# ============================================================
# COURSES
# ============================================================

@router.get("/courses")
def get_admin_courses(
    current_user: User = Depends(require_admin),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Admin view of all courses.
    """

    return safe_select_all(
        db,
        "courses",
        (
            "created_at",
            "updated_at",
            "id",
        ),
    )


# ============================================================
# ASSESSMENTS
# ============================================================

@router.get("/assessments")
def get_admin_assessments(
    current_user: User = Depends(require_admin),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Admin view of assessments.
    """

    possible_tables = [
        "assessments",
        "trainer_questionnaires",
        "questionnaires",
    ]

    for table_name in possible_tables:
        if table_exists(db, table_name):
            return safe_select_all(
                db,
                table_name,
                (
                    "created_at",
                    "updated_at",
                    "id",
                ),
            )

    return []


# ============================================================
# CERTIFICATIONS
# ============================================================

@router.get("/certifications")
def get_admin_certifications(
    current_user: User = Depends(require_admin),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Admin view of certifications.
    """

    possible_tables = [
        "certifications",
        "certificates",
        "trainee_certifications",
    ]

    for table_name in possible_tables:
        if table_exists(db, table_name):
            return safe_select_all(
                db,
                table_name,
                (
                    "issued_at",
                    "created_at",
                    "updated_at",
                    "id",
                ),
            )

    return []


# ============================================================
# COMPETENCIES
# ============================================================

@router.get("/competencies")
def get_admin_competencies(
    current_user: User = Depends(require_admin),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Admin competency intelligence endpoint.
    """

    if table_exists(db, "competencies"):
        return safe_select_all(
            db,
            "competencies",
            (
                "created_at",
                "updated_at",
                "id",
            ),
        )

    if table_exists(db, "trainee_competencies"):
        return safe_select_all(
            db,
            "trainee_competencies",
            (
                "updated_at",
                "created_at",
                "id",
            ),
        )

    return []


# ============================================================
# TRAINER MATCHING
# ============================================================

@router.get("/trainer-matching")
def get_admin_trainer_matching(
    current_user: User = Depends(require_admin),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Return competency-based trainer matching information.

    The endpoint uses the existing:
        trainers
        trainer_competencies
        competencies

    tables.

    Because the exact trainer_competencies schema can differ
    between database versions, the endpoint detects the
    available relationship columns before querying.
    """

    if not table_exists(db, "trainer_competencies"):
        return []

    if not table_exists(db, "trainers"):
        return []

    if not table_exists(db, "competencies"):
        return []

    trainer_competency_columns = table_columns(
        db,
        "trainer_competencies",
    )

    competency_columns = table_columns(
        db,
        "competencies",
    )

    trainer_columns = table_columns(
        db,
        "trainers",
    )

    trainer_id_column = pick_column(
        trainer_competency_columns,
        "trainer_id",
        "trainer_profile_id",
    )

    competency_id_column = pick_column(
        trainer_competency_columns,
        "competency_id",
        "competency",
    )

    level_column = pick_column(
        trainer_competency_columns,
        "level",
        "proficiency_level",
        "competency_level",
        "skill_level",
    )

    score_column = pick_column(
        trainer_competency_columns,
        "match_score",
        "score",
        "proficiency_score",
        "rating",
    )

    trainer_name_column = pick_column(
        trainer_columns,
        "first_name",
    )

    trainer_last_name_column = pick_column(
        trainer_columns,
        "last_name",
    )

    competency_name_column = pick_column(
        competency_columns,
        "name",
        "competency_name",
    )

    if not trainer_id_column:
        return []

    if not competency_id_column:
        return []

    if not competency_name_column:
        return []

    if not trainer_name_column:
        return []

    trainer_last_name_sql = (
        f"COALESCE(t.`{trainer_last_name_column}`, '')"
        if trainer_last_name_column
        else "''"
    )

    if level_column:
        level_sql = f"tc.`{level_column}`"
    else:
        level_sql = "'Not specified'"

    if score_column:
        score_sql = f"tc.`{score_column}`"
    else:
        score_sql = "NULL"

    trainee_count_sql = "0"

    if (
        table_exists(db, "trainee_competencies")
        and table_exists(db, "users")
    ):
        trainee_competency_columns = table_columns(
            db,
            "trainee_competencies",
        )

        trainee_competency_id_column = pick_column(
            trainee_competency_columns,
            "competency_id",
            "competency",
        )

        if trainee_competency_id_column:
            trainee_count_sql = f"""
                (
                    SELECT COUNT(DISTINCT tc2.trainee_id)
                    FROM trainee_competencies tc2
                    WHERE tc2.`{trainee_competency_id_column}`
                        = tc.`{competency_id_column}`
                )
            """

    sql = text(
        f"""
        SELECT
            t.id AS trainer_id,

            CONCAT(
                t.`{trainer_name_column}`,
                CASE
                    WHEN {trainer_last_name_sql} <> ''
                    THEN CONCAT(' ', {trainer_last_name_sql})
                    ELSE ''
                END
            ) AS trainer_name,

            c.id AS competency_id,
            c.`{competency_name_column}` AS competency_name,

            {level_sql} AS level,
            {score_sql} AS match_score,
            {trainee_count_sql} AS trainee_count,

            CASE
                WHEN u.is_active = 1
                THEN 'Active'
                ELSE 'Inactive'
            END AS status

        FROM trainer_competencies tc

        INNER JOIN trainers t
            ON t.id = tc.`{trainer_id_column}`

        INNER JOIN competencies c
            ON c.id = tc.`{competency_id_column}`

        LEFT JOIN users u
            ON u.id = t.user_id

        ORDER BY
            t.first_name ASC,
            c.name ASC
        """
    )

    try:
        rows = db.execute(sql).mappings().all()
    except Exception:
        return []

    return [dict(row) for row in rows]


# ============================================================
# NOTIFICATIONS
# ============================================================

@router.get("/notifications")
def get_admin_notifications(
    current_user: User = Depends(require_admin),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Admin notification feed.
    """

    possible_tables = [
        "notifications",
        "admin_notifications",
        "trainer_notifications",
        "trainee_notifications",
    ]

    for table_name in possible_tables:
        if table_exists(db, table_name):
            return safe_select_all(
                db,
                table_name,
                (
                    "created_at",
                    "updated_at",
                    "id",
                ),
            )

    return []


# ============================================================
# ANNOUNCEMENTS
# ============================================================

@router.get("/announcements")
def get_admin_announcements(
    current_user: User = Depends(require_admin),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Return platform announcements.
    """

    possible_tables = [
        "announcements",
        "admin_announcements",
    ]

    for table_name in possible_tables:
        if table_exists(db, table_name):
            return safe_select_all(
                db,
                table_name,
                (
                    "published_at",
                    "created_at",
                    "updated_at",
                    "id",
                ),
            )

    return []


@router.post("/announcements")
def create_admin_announcement(
    payload: dict,
    current_user: User = Depends(require_admin),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Create an announcement.
    """

    table_name = None

    if table_exists(db, "announcements"):
        table_name = "announcements"

    elif table_exists(db, "admin_announcements"):
        table_name = "admin_announcements"

    if not table_name:
        raise HTTPException(
            status_code=503,
            detail=(
                "Announcement storage is not configured yet. "
                "Create the announcements table before publishing."
            ),
        )

    columns = table_columns(
        db,
        table_name,
    )

    title = str(
        payload.get("title")
        or payload.get("headline")
        or ""
    ).strip()

    content = str(
        payload.get("content")
        or payload.get("description")
        or payload.get("message")
        or ""
    ).strip()

    if not title:
        raise HTTPException(
            status_code=400,
            detail="Announcement title is required.",
        )

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Announcement content is required.",
        )

    insert_columns = []
    insert_values = []
    params = {}

    if "title" in columns:
        insert_columns.append("title")
        insert_values.append(":title")
        params["title"] = title

    elif "headline" in columns:
        insert_columns.append("headline")
        insert_values.append(":title")
        params["title"] = title

    if "content" in columns:
        insert_columns.append("content")
        insert_values.append(":content")
        params["content"] = content

    elif "description" in columns:
        insert_columns.append("description")
        insert_values.append(":content")
        params["content"] = content

    elif "message" in columns:
        insert_columns.append("message")
        insert_values.append(":content")
        params["content"] = content

    if "created_by" in columns:
        insert_columns.append("created_by")
        insert_values.append(":created_by")
        params["created_by"] = current_user.id

    elif "author_id" in columns:
        insert_columns.append("author_id")
        insert_values.append(":created_by")
        params["created_by"] = current_user.id

    if "created_at" in columns:
        insert_columns.append("created_at")
        insert_values.append("CURRENT_TIMESTAMP")

    if "updated_at" in columns:
        insert_columns.append("updated_at")
        insert_values.append("CURRENT_TIMESTAMP")

    if "published_at" in columns:
        insert_columns.append("published_at")
        insert_values.append("CURRENT_TIMESTAMP")

    if "status" in columns:
        insert_columns.append("status")
        insert_values.append(":status")
        params["status"] = payload.get(
            "status",
            "published",
        )

    if not insert_columns:
        raise HTTPException(
            status_code=500,
            detail=(
                "Announcement table does not contain "
                "supported title/content columns."
            ),
        )

    sql = text(
        f"""
        INSERT INTO `{table_name}`
        ({", ".join(f"`{column}`" for column in insert_columns)})
        VALUES
        ({", ".join(insert_values)})
        """
    )

    result = db.execute(
        sql,
        params,
    )

    db.commit()

    return {
        "message": "Announcement created successfully.",
        "id": result.lastrowid,
        "title": title,
        "content": content,
    }


# ============================================================
# ACHIEVEMENTS
# ============================================================

@router.get("/achievements")
def get_admin_achievements(
    current_user: User = Depends(require_admin),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Admin achievement records.
    """

    possible_tables = [
        "achievements",
        "trainee_achievements",
        "certifications",
    ]

    for table_name in possible_tables:
        if table_exists(db, table_name):
            return safe_select_all(
                db,
                table_name,
                (
                    "achieved_at",
                    "issued_at",
                    "created_at",
                    "updated_at",
                    "id",
                ),
            )

    return []


# ============================================================
# ANALYTICS
# ============================================================

@router.get("/analytics")
def get_admin_analytics(
    current_user: User = Depends(require_admin),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Platform-wide admin analytics.
    """

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

    total_institutions = (
        db.query(User)
        .filter(User.role == "institution")
        .count()
    )

    total_industries = (
        db.query(User)
        .filter(User.role == "industry")
        .count()
    )

    active_users = (
        db.query(User)
        .filter(User.is_active == True)
        .count()
    )

    verified_users = (
        db.query(User)
        .filter(User.is_verified == True)
        .count()
    )

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "verified": verified_users,
            "trainees": total_trainees,
            "trainers": total_trainers,
            "institutions": total_institutions,
            "industries": total_industries,
        },

        "learning": {
            "courses": safe_count(
                db,
                "courses",
            ),

            "assessments": (
                safe_count(db, "assessments")
                if table_exists(db, "assessments")
                else safe_count(
                    db,
                    "trainer_questionnaires",
                )
            ),

            "certifications": (
                safe_count(db, "certifications")
                if table_exists(db, "certifications")
                else safe_count(
                    db,
                    "certificates",
                )
            ),

            "competencies": safe_count(
                db,
                "competencies",
            ),
        },

        "engagement": {
            "course_enrollments": safe_count(
                db,
                "course_enrollments",
            ),

            "notifications": safe_count(
                db,
                "notifications",
            ),

            "announcements": (
                safe_count(
                    db,
                    "announcements",
                )
                if table_exists(db, "announcements")
                else safe_count(
                    db,
                    "admin_announcements",
                )
            ),
        },
    }


# ============================================================
# REPORTS
# ============================================================

@router.get("/reports")
def get_admin_reports(
    current_user: User = Depends(require_admin),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Platform report summary.
    """

    total_users = db.query(User).count()

    role_distribution = {
        "trainee": (
            db.query(User)
            .filter(User.role == "trainee")
            .count()
        ),

        "trainer": (
            db.query(User)
            .filter(User.role == "trainer")
            .count()
        ),

        "institution": (
            db.query(User)
            .filter(User.role == "institution")
            .count()
        ),

        "industry": (
            db.query(User)
            .filter(User.role == "industry")
            .count()
        ),

        "admin": (
            db.query(User)
            .filter(User.role == "admin")
            .count()
        ),
    }

    return {
        "generated_at": datetime.utcnow(),

        "summary": {
            "total_users": total_users,

            "active_users": (
                db.query(User)
                .filter(User.is_active == True)
                .count()
            ),

            "courses": safe_count(
                db,
                "courses",
            ),

            "assessments": (
                safe_count(db, "assessments")
                if table_exists(db, "assessments")
                else safe_count(
                    db,
                    "trainer_questionnaires",
                )
            ),

            "certifications": (
                safe_count(db, "certifications")
                if table_exists(db, "certifications")
                else safe_count(
                    db,
                    "certificates",
                )
            ),

            "competencies": safe_count(
                db,
                "competencies",
            ),

            "enrollments": safe_count(
                db,
                "course_enrollments",
            ),
        },

        "role_distribution": role_distribution,
    }