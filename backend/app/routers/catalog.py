from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain import Domain
from app.models.skill_category import SkillCategory
from app.models.skill import Skill
from app.models.competency import Competency
from app.schemas.catalog import (
    DomainResponse,
    CategoryResponse,
    SkillResponse,
    CompetencyResponse,
)


router = APIRouter(
    prefix="/api/catalog",
    tags=["Catalogue"],
)


# ============================================================
# DOMAINS
# ============================================================

@router.get(
    "/domains",
    response_model=list[DomainResponse],
)
def get_domains(
    db: Session = Depends(get_db),
):
    statement = (
        select(Domain)
        .where(Domain.is_active.is_(True))
        .order_by(Domain.name)
    )

    return db.scalars(statement).all()


@router.get(
    "/domains/{slug}",
    response_model=DomainResponse,
)
def get_domain(
    slug: str,
    db: Session = Depends(get_db),
):
    statement = select(Domain).where(
        Domain.slug == slug,
        Domain.is_active.is_(True),
    )

    domain = db.scalar(statement)

    if not domain:
        raise HTTPException(
            status_code=404,
            detail="Domain not found",
        )

    return domain


# ============================================================
# CATEGORIES
# ============================================================

@router.get(
    "/categories",
    response_model=list[CategoryResponse],
)
def get_categories(
    db: Session = Depends(get_db),
):
    statement = (
        select(SkillCategory)
        .where(SkillCategory.is_active.is_(True))
        .order_by(SkillCategory.name)
    )

    return db.scalars(statement).all()


@router.get(
    "/categories/{slug}",
    response_model=CategoryResponse,
)
def get_category(
    slug: str,
    db: Session = Depends(get_db),
):
    statement = select(SkillCategory).where(
        SkillCategory.slug == slug,
        SkillCategory.is_active.is_(True),
    )

    category = db.scalar(statement)

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found",
        )

    return category


# ============================================================
# SKILLS
# ============================================================

@router.get(
    "/skills",
    response_model=list[SkillResponse],
)
def get_skills(
    db: Session = Depends(get_db),
):
    statement = (
        select(Skill)
        .where(Skill.is_active.is_(True))
        .order_by(Skill.name)
    )

    return db.scalars(statement).all()


@router.get(
    "/skills/{slug}",
    response_model=SkillResponse,
)
def get_skill(
    slug: str,
    db: Session = Depends(get_db),
):
    statement = select(Skill).where(
        Skill.slug == slug,
        Skill.is_active.is_(True),
    )

    skill = db.scalar(statement)

    if not skill:
        raise HTTPException(
            status_code=404,
            detail="Skill not found",
        )

    return skill


# ============================================================
# COMPETENCIES
# ============================================================

@router.get(
    "/competencies",
    response_model=list[CompetencyResponse],
)
def get_competencies(
    db: Session = Depends(get_db),
):
    statement = (
        select(Competency)
        .where(Competency.is_active.is_(True))
        .order_by(Competency.name)
    )

    return db.scalars(statement).all()


@router.get(
    "/competencies/{competency_id}",
    response_model=CompetencyResponse,
)
def get_competency(
    competency_id: int,
    db: Session = Depends(get_db),
):
    statement = select(Competency).where(
        Competency.id == competency_id,
        Competency.is_active.is_(True),
    )

    competency = db.scalar(statement)

    if not competency:
        raise HTTPException(
            status_code=404,
            detail="Competency not found",
        )

    return competency