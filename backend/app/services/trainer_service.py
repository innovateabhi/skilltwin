"""
Database helpers for the Trainer Portal.

This service deliberately uses SQLAlchemy Core/reflection instead of assuming
exact column names in an existing SkillTwin database. It discovers available
columns and writes only columns that exist. This makes the module safer to
install into an existing database.

Existing tables used:
    users, trainers, courses, course_enrollments, lesson_progress,
    assessments, assessment_attempts, competencies

Trainer-specific tables are created by:
    migrations/trainer_portal.sql
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session


def table_columns(db: Session, table: str) -> set[str]:
    try:
        return {c["name"] for c in inspect(db.bind).get_columns(table)}
    except Exception:
        return set()


def table_exists(db: Session, table: str) -> bool:
    try:
        return inspect(db.bind).has_table(table)
    except Exception:
        return False


def pick(columns: set[str], *names: str) -> Optional[str]:
    for name in names:
        if name in columns:
            return name
    return None


def qident(name: str) -> str:
    # Names come only from SQLAlchemy inspection, not user input.
    return f"`{name.replace('`', '``')}`"


def first_value(row: Any, *names: str, default=None):
    for n in names:
        try:
            value = getattr(row, n, None)
        except Exception:
            value = None
        if value is not None:
            return value
    return default


def current_user_id(current_user: Any) -> Optional[int]:
    value = first_value(current_user, "id", "user_id")
    if value is not None:
        return int(value)
    if isinstance(current_user, dict):
        value = current_user.get("id", current_user.get("user_id"))
        return int(value) if value is not None else None
    return None


def current_role(current_user: Any) -> str:
    value = first_value(current_user, "role", "user_role", "type", default="")
    if isinstance(current_user, dict):
        value = current_user.get("role", current_user.get("user_role", value))
    return str(value or "").lower()


def get_trainer_row(db: Session, user_id: int):
    if not table_exists(db, "trainers"):
        return None

    cols = table_columns(db, "trainers")
    user_col = pick(cols, "user_id", "userId", "user")
    id_col = pick(cols, "id", "trainer_id")

    if not user_col:
        return None

    sql = text(
        f"SELECT * FROM `trainers` WHERE {qident(user_col)} = :uid LIMIT 1"
    )
    return db.execute(sql, {"uid": user_id}).mappings().first()


def trainer_required(db: Session, current_user: Any):
    uid = current_user_id(current_user)
    if not uid:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Authentication required")

    role = current_role(current_user)
    if role not in {"trainer", "trainers"}:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Trainer role required")

    trainer = get_trainer_row(db, uid)
    if not trainer:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=403,
            detail="Trainer profile is not active or has not been approved by an administrator",
        )
    return uid, trainer


def safe_count(db: Session, table: str, where: str = "", params: dict | None = None) -> int:
    if not table_exists(db, table):
        return 0
    sql = f"SELECT COUNT(*) AS c FROM `{table}`"
    if where:
        sql += f" WHERE {where}"
    row = db.execute(text(sql), params or {}).first()
    return int(row.c or 0)


def insert_dynamic(db: Session, table: str, data: Dict[str, Any]) -> int:
    cols = table_columns(db, table)
    payload = {k: v for k, v in data.items() if k in cols}
    if not payload:
        raise ValueError(f"No compatible columns found for table {table}")

    names = list(payload.keys())
    sql = (
        f"INSERT INTO `{table}` "
        f"({', '.join(qident(n) for n in names)}) "
        f"VALUES ({', '.join(':'+n for n in names)})"
    )
    result = db.execute(text(sql), payload)
    db.flush()
    return int(result.lastrowid or 0)


def update_dynamic(db: Session, table: str, where_col: str, where_value: Any, data: Dict[str, Any]):
    cols = table_columns(db, table)
    payload = {k: v for k, v in data.items() if k in cols}
    payload = {k: v for k, v in payload.items() if k != where_col}
    if not payload:
        return

    sets = ", ".join(f"{qident(k)} = :{k}" for k in payload)
    payload["_where"] = where_value
    db.execute(
        text(
            f"UPDATE `{table}` SET {sets} "
            f"WHERE {qident(where_col)} = :_where"
        ),
        payload,
    )
    db.flush()


def now():
    return datetime.utcnow()
