from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user


router = APIRouter(
    prefix="/api/industry",
    tags=["Industry Portal"],
)


# ============================================================
# HELPERS
# ============================================================

def industry_required(db: Session, user):
    """
    Make sure the authenticated user is an Industry user and
    return the industry profile.
    """

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    role = str(getattr(user, "role", "")).lower()

    if role != "industry":
        raise HTTPException(
            status_code=403,
            detail="Industry access required",
        )

    industry = db.execute(
        text(
            """
            SELECT *
            FROM industries
            WHERE user_id = :user_id
            LIMIT 1
            """
        ),
        {
            "user_id": user.id,
        },
    ).mappings().first()

    if not industry:
        raise HTTPException(
            status_code=404,
            detail="Industry profile not found",
        )

    return industry


def safe_count(
    db: Session,
    table: str,
    where: str | None = None,
    params: dict | None = None,
):
    try:
        sql = f"SELECT COUNT(*) FROM `{table}`"

        if where:
            sql += f" WHERE {where}"

        return int(
            db.execute(
                text(sql),
                params or {},
            ).scalar()
            or 0
        )

    except Exception:
        return 0


# ============================================================
# ME
# ============================================================

@router.get("/me")
def get_me(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    industry = industry_required(db, user)

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
        },
        "industry": dict(industry),
    }


# ============================================================
# PROFILE
# ============================================================

@router.get("/profile")
def get_profile(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    industry = industry_required(db, user)

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at,
        },
        "industry": dict(industry),
    }


@router.put("/profile")
def update_profile(
    payload: dict,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    industry = industry_required(db, user)

    allowed = {
        "company_name",
        "industry_type",
        "registration_number",
        "official_email",
        "phone",
        "website",
        "address",
        "city",
        "state",
        "country",
        "description",
        "logo",
    }

    update_data = {
        key: value
        for key, value in payload.items()
        if key in allowed
    }

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No valid profile fields supplied",
        )

    if "company_name" in update_data:
        if not str(update_data["company_name"]).strip():
            raise HTTPException(
                status_code=400,
                detail="Company name cannot be empty",
            )

    set_parts = []

    params = {
        "industry_id": industry["id"],
    }

    for key, value in update_data.items():
        set_parts.append(f"`{key}` = :{key}")
        params[key] = value

    set_parts.append("updated_at = CURRENT_TIMESTAMP")

    db.execute(
        text(
            f"""
            UPDATE industries
            SET {", ".join(set_parts)}
            WHERE id = :industry_id
            """
        ),
        params,
    )

    db.commit()

    return {
        "message": "Industry profile updated successfully",
    }


# ============================================================
# DASHBOARD
# ============================================================

@router.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    industry = industry_required(db, user)

    talent_pool = safe_count(
        db,
        "trainees",
    )

    active_requirements = safe_count(
        db,
        "skill_gaps",
        "`status` = 'open'",
    )

    training_programs = safe_count(
        db,
        "courses",
    )

    trainer_count = safe_count(
        db,
        "trainers",
    )

    total_gaps = safe_count(
        db,
        "skill_gaps",
    )

    resolved_gaps = safe_count(
        db,
        "skill_gaps",
        "`gap_score` <= 0",
    )

    skill_coverage = (
        round((resolved_gaps / total_gaps) * 100)
        if total_gaps
        else 0
    )

    # --------------------------------------------------------
    # Top skill gaps
    # --------------------------------------------------------

    top_skills = []

    try:
        rows = db.execute(
            text(
                """
                SELECT
                    s.id,
                    s.name,
                    COUNT(sg.id) AS gap_count,
                    ROUND(AVG(sg.current_score), 0) AS current_score,
                    ROUND(AVG(sg.target_score), 0) AS target_score,
                    ROUND(AVG(sg.gap_score), 0) AS average_gap
                FROM skill_gaps sg
                INNER JOIN skills s
                    ON s.id = sg.skill_id
                GROUP BY s.id, s.name
                ORDER BY gap_count DESC
                LIMIT 8
                """
            )
        ).mappings().all()

        top_skills = [dict(row) for row in rows]

    except Exception:
        top_skills = []

    # --------------------------------------------------------
    # Recent talent
    # --------------------------------------------------------

    talent = []

    try:
        rows = db.execute(
            text(
                """
                SELECT
                    t.id,
                    t.user_id,
                    t.first_name,
                    t.last_name,
                    t.specialization,
                    t.target_role,
                    t.institution_name,
                    t.education_level,
                    u.email
                FROM trainees t
                INNER JOIN users u
                    ON u.id = t.user_id
                WHERE u.is_active = 1
                ORDER BY t.id DESC
                LIMIT 8
                """
            )
        ).mappings().all()

        talent = [dict(row) for row in rows]

    except Exception:
        talent = []

    return {
        "industry": dict(industry),
        "stats": {
            "talent_pool": talent_pool,
            "active_requirements": active_requirements,
            "training_programs": training_programs,
            "trainer_count": trainer_count,
            "skill_coverage": skill_coverage,
        },
        "top_skills": top_skills,
        "talent": talent,
    }


# ============================================================
# TALENT
# ============================================================

@router.get("/talent")
def talent(
    search: str | None = None,
    specialization: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    industry_required(db, user)

    sql = """
        SELECT
            t.id,
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
            u.email,
            u.is_active
        FROM trainees t
        INNER JOIN users u
            ON u.id = t.user_id
        WHERE u.is_active = 1
    """

    params = {}

    if search:
        sql += """
            AND (
                CONCAT(
                    COALESCE(t.first_name, ''),
                    ' ',
                    COALESCE(t.last_name, '')
                ) LIKE :search
                OR t.specialization LIKE :search
                OR t.target_role LIKE :search
                OR t.institution_name LIKE :search
            )
        """

        params["search"] = f"%{search}%"

    if specialization:
        sql += """
            AND t.specialization LIKE :specialization
        """

        params["specialization"] = f"%{specialization}%"

    sql += " ORDER BY t.id DESC"

    rows = db.execute(
        text(sql),
        params,
    ).mappings().all()

    return [dict(row) for row in rows]


@router.get("/talent/{talent_id}")
def talent_by_id(
    talent_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    industry_required(db, user)

    row = db.execute(
        text(
            """
            SELECT
                t.*,
                u.email,
                u.is_active,
                u.is_verified
            FROM trainees t
            INNER JOIN users u
                ON u.id = t.user_id
            WHERE t.id = :talent_id
            LIMIT 1
            """
        ),
        {
            "talent_id": talent_id,
        },
    ).mappings().first()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Talent profile not found",
        )

    return dict(row)


@router.get("/talent/search")
def search_talent(
    search: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return talent(
        search=search,
        db=db,
        user=user,
    )


# ============================================================
# SKILLS
# ============================================================

@router.get("/skills")
def skills(
    search: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    industry_required(db, user)

    sql = """
        SELECT
            s.id,
            s.name,
            s.slug,
            s.category,
            s.description,
            s.is_active,
            COUNT(sg.id) AS gap_count,
            ROUND(AVG(sg.current_score), 0) AS average_current,
            ROUND(AVG(sg.target_score), 0) AS average_target,
            ROUND(AVG(sg.gap_score), 0) AS average_gap
        FROM skills s
        LEFT JOIN skill_gaps sg
            ON sg.skill_id = s.id
        WHERE s.is_active = 1
    """

    params = {}

    if search:
        sql += """
            AND (
                s.name LIKE :search
                OR s.category LIKE :search
                OR s.description LIKE :search
            )
        """

        params["search"] = f"%{search}%"

    sql += """
        GROUP BY
            s.id,
            s.name,
            s.slug,
            s.category,
            s.description,
            s.is_active
        ORDER BY
            gap_count DESC,
            s.name ASC
    """

    rows = db.execute(
        text(sql),
        params,
    ).mappings().all()

    return [dict(row) for row in rows]


# ============================================================
# SKILL GAPS / COMPETENCY INSIGHTS
# ============================================================

@router.get("/skills/gaps")
def skill_gaps(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    industry_required(db, user)

    rows = db.execute(
        text(
            """
            SELECT
                s.id AS skill_id,
                s.name AS skill_name,
                s.category,
                COUNT(sg.id) AS affected_talent,
                ROUND(AVG(sg.current_score), 0) AS current_score,
                ROUND(AVG(sg.target_score), 0) AS target_score,
                ROUND(AVG(sg.gap_score), 0) AS gap_score,
                SUM(
                    CASE
                        WHEN sg.severity = 'critical'
                        THEN 1
                        ELSE 0
                    END
                ) AS critical_count,
                SUM(
                    CASE
                        WHEN sg.severity = 'moderate'
                        THEN 1
                        ELSE 0
                    END
                ) AS moderate_count
            FROM skill_gaps sg
            INNER JOIN skills s
                ON s.id = sg.skill_id
            GROUP BY
                s.id,
                s.name,
                s.category
            ORDER BY
                gap_score DESC
            """
        )
    ).mappings().all()

    return [dict(row) for row in rows]


# ============================================================
# TRAINERS
# ============================================================

@router.get("/trainers")
def trainers(
    search: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    industry_required(db, user)

    sql = """
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
            u.email,
            u.is_active,
            u.is_verified
        FROM trainers t
        INNER JOIN users u
            ON u.id = t.user_id
        WHERE u.is_active = 1
    """

    params = {}

    if search:
        sql += """
            AND (
                CONCAT(
                    COALESCE(t.first_name, ''),
                    ' ',
                    COALESCE(t.last_name, '')
                ) LIKE :search
                OR t.specialization LIKE :search
                OR t.designation LIKE :search
                OR t.organization LIKE :search
            )
        """

        params["search"] = f"%{search}%"

    sql += " ORDER BY t.id DESC"

    rows = db.execute(
        text(sql),
        params,
    ).mappings().all()

    return [dict(row) for row in rows]


@router.get("/trainers/{trainer_id}")
def trainer_by_id(
    trainer_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    industry_required(db, user)

    row = db.execute(
        text(
            """
            SELECT
                t.*,
                u.email,
                u.is_active,
                u.is_verified
            FROM trainers t
            INNER JOIN users u
                ON u.id = t.user_id
            WHERE t.id = :trainer_id
            LIMIT 1
            """
        ),
        {
            "trainer_id": trainer_id,
        },
    ).mappings().first()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Trainer not found",
        )

    return dict(row)


# ============================================================
# TRAINING PROGRAMS
# ============================================================

@router.get("/training")
def training(
    search: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    industry_required(db, user)

    if not _table_exists(db, "courses"):
        return []

    sql = """
        SELECT *
        FROM courses
    """

    params = {}

    if search:
        columns = _table_columns(db, "courses")

        searchable = [
            column
            for column in [
                "title",
                "name",
                "description",
                "category",
            ]
            if column in columns
        ]

        if searchable:
            sql += " WHERE " + " OR ".join(
                f"`{column}` LIKE :search"
                for column in searchable
            )

            params["search"] = f"%{search}%"

    sql += " ORDER BY id DESC"

    try:
        rows = db.execute(
            text(sql),
            params,
        ).mappings().all()

        return [dict(row) for row in rows]

    except Exception:
        return []


@router.get("/training/{program_id}")
def training_program(
    program_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    industry_required(db, user)

    row = db.execute(
        text(
            """
            SELECT *
            FROM courses
            WHERE id = :program_id
            LIMIT 1
            """
        ),
        {
            "program_id": program_id,
        },
    ).mappings().first()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Training program not found",
        )

    return dict(row)


# ============================================================
# REPORTS
# ============================================================

@router.get("/reports")
def reports(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    industry_required(db, user)

    total_talent = safe_count(db, "trainees")
    total_trainers = safe_count(db, "trainers")
    total_courses = safe_count(db, "courses")
    total_gaps = safe_count(db, "skill_gaps")

    critical_gaps = safe_count(
        db,
        "skill_gaps",
        "`severity` = 'critical'",
    )

    moderate_gaps = safe_count(
        db,
        "skill_gaps",
        "`severity` = 'moderate'",
    )

    low_gaps = safe_count(
        db,
        "skill_gaps",
        "`severity` = 'low'",
    )

    resolved_gaps = safe_count(
        db,
        "skill_gaps",
        "`gap_score` <= 0",
    )

    coverage = (
        round(
            (resolved_gaps / total_gaps) * 100
        )
        if total_gaps
        else 0
    )

    return {
        "summary": {
            "talent": total_talent,
            "trainers": total_trainers,
            "training_programs": total_courses,
            "skill_gaps": total_gaps,
            "skill_coverage": coverage,
        },
        "gap_distribution": {
            "critical": critical_gaps,
            "moderate": moderate_gaps,
            "low": low_gaps,
            "resolved": resolved_gaps,
        },
    }


@router.get("/reports/skills")
def skill_report(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return skill_gaps(
        db=db,
        user=user,
    )


@router.get("/reports/talent")
def talent_report(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    industry_required(db, user)

    rows = db.execute(
        text(
            """
            SELECT
                t.specialization,
                COUNT(*) AS talent_count
            FROM trainees t
            GROUP BY t.specialization
            ORDER BY talent_count DESC
            """
        )
    ).mappings().all()

    return [dict(row) for row in rows]


@router.get("/reports/training")
def training_report(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    industry_required(db, user)

    total_courses = safe_count(
        db,
        "courses",
    )

    total_enrollments = safe_count(
        db,
        "course_enrollments",
    )

    return {
        "total_programs": total_courses,
        "total_enrollments": total_enrollments,
    }


# ============================================================
# ANALYTICS
# ============================================================

@router.get("/analytics")
def analytics(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    industry_required(db, user)

    total_gaps = safe_count(db, "skill_gaps")

    average_gap = 0

    try:
        average_gap = round(
            float(
                db.execute(
                    text(
                        """
                        SELECT COALESCE(
                            AVG(gap_score),
                            0
                        )
                        FROM skill_gaps
                        """
                    )
                ).scalar()
                or 0
            )
        )

    except Exception:
        average_gap = 0

    return {
        "total_skill_gaps": total_gaps,
        "average_skill_gap": average_gap,
    }


# ============================================================
# NOTIFICATIONS
# ============================================================

@router.get("/notifications")
def notifications(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    industry_required(db, user)

    # Industry notifications are currently generated from
    # live platform activity because there is no dedicated
    # industry_notifications table in the existing schema.

    items = []

    critical = safe_count(
        db,
        "skill_gaps",
        "`severity` = 'critical'",
    )

    if critical:
        items.append(
            {
                "id": "critical-skill-gaps",
                "title": "Critical skill gaps detected",
                "message": f"{critical} critical skill gap records require attention.",
                "type": "warning",
                "read": False,
            }
        )

    courses = safe_count(
        db,
        "courses",
    )

    items.append(
        {
            "id": "training-programs",
            "title": "Training ecosystem",
            "message": f"{courses} training programs are currently available.",
            "type": "info",
            "read": True,
        }
    )

    return items


# ============================================================
# OPTIONAL TABLE HELPERS
# ============================================================

def _table_exists(db: Session, table_name: str):
    try:
        result = db.execute(
            text(
                """
                SELECT COUNT(*)
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

    except Exception:
        return False


def _table_columns(db: Session, table_name: str):
    try:
        rows = db.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = DATABASE()
                AND table_name = :table_name
                """
            ),
            {
                "table_name": table_name,
            },
        ).scalars().all()

        return set(rows)

    except Exception:
        return set()