from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------
# Make backend/ available when this script is executed directly:
#
# python scripts/seed_catalog.py
# ---------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


from app.core.database import SessionLocal

from app.models.domain import Domain
from app.models.skill_category import SkillCategory
from app.models.skill import Skill
from app.models.competency import Competency


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

CATALOG_DIR = BACKEND_DIR / "catalog"

DOMAINS_FILE = CATALOG_DIR / "domains.json"
CATEGORIES_FILE = CATALOG_DIR / "categories.json"
SKILLS_FILE = CATALOG_DIR / "skills.json"
COMPETENCIES_FILE = CATALOG_DIR / "competencies.json"


# ---------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------

def banner(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)
    print()


def load_json(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(
            f"Catalogue file not found: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            f"{path.name} must contain a JSON array."
        )

    return data


def validate_unique_slugs(
    items: list[dict],
    filename: str,
) -> None:

    slugs = []

    for item in items:
        slug = item.get("slug")

        if not slug:
            raise ValueError(
                f"{filename}: every record requires a 'slug'."
            )

        slugs.append(slug)

    duplicates = {
        slug
        for slug in slugs
        if slugs.count(slug) > 1
    }

    if duplicates:
        raise ValueError(
            f"{filename}: duplicate slugs found: "
            f"{', '.join(sorted(duplicates))}"
        )


# ---------------------------------------------------------------------
# Domain seeding
# ---------------------------------------------------------------------

def seed_domains(
    session: Session,
    items: list[dict],
) -> dict[str, Domain]:

    result: dict[str, Domain] = {}

    for item in items:

        slug = item["slug"]

        existing = session.execute(
            select(Domain).where(
                Domain.slug == slug
            )
        ).scalar_one_or_none()

        if existing:

            existing.name = item["name"]

            if hasattr(existing, "description"):
                existing.description = item.get(
                    "description"
                )

            domain = existing

        else:

            domain = Domain(
                slug=slug,
                name=item["name"],
                description=item.get(
                    "description"
                ),
            )

            session.add(domain)

        result[slug] = domain

    session.flush()

    return result


# ---------------------------------------------------------------------
# Category seeding
# ---------------------------------------------------------------------

def seed_categories(
    session: Session,
    items: list[dict],
    domains: dict[str, Domain],
) -> dict[str, SkillCategory]:

    result: dict[str, SkillCategory] = {}

    for item in items:

        slug = item["slug"]
        domain_slug = item["domain"]

        if domain_slug not in domains:
            raise ValueError(
                f"Category '{slug}' references "
                f"unknown domain '{domain_slug}'."
            )

        domain = domains[domain_slug]

        existing = session.execute(
            select(SkillCategory).where(
                SkillCategory.slug == slug
            )
        ).scalar_one_or_none()

        if existing:

            existing.name = item["name"]

            if hasattr(existing, "description"):
                existing.description = item.get(
                    "description"
                )

            # Support either FK-based or relationship-based models.
            if hasattr(existing, "domain_id"):
                existing.domain_id = domain.id

            if hasattr(existing, "domain"):
                existing.domain = domain

            category = existing

        else:

            category_kwargs = {
                "slug": slug,
                "name": item["name"],
            }

            if hasattr(SkillCategory, "domain_id"):
                category_kwargs["domain_id"] = domain.id

            if hasattr(SkillCategory, "domain"):
                category_kwargs["domain"] = domain

            if hasattr(SkillCategory, "description"):
                category_kwargs["description"] = item.get(
                    "description"
                )

            category = SkillCategory(
                **category_kwargs
            )

            session.add(category)

        result[slug] = category

    session.flush()

    return result


# ---------------------------------------------------------------------
# Skill seeding
# ---------------------------------------------------------------------

def seed_skills(
    session: Session,
    items: list[dict],
    categories: dict[str, SkillCategory],
) -> dict[str, Skill]:

    result: dict[str, Skill] = {}

    for item in items:

        slug = item["slug"]
        category_slug = item["category"]

        if category_slug not in categories:
            raise ValueError(
                f"Skill '{slug}' references "
                f"unknown category '{category_slug}'."
            )

        category = categories[category_slug]

        existing = session.execute(
            select(Skill).where(
                Skill.slug == slug
            )
        ).scalar_one_or_none()

        if existing:

            existing.name = item["name"]

            if hasattr(existing, "description"):
                existing.description = item.get(
                    "description"
                )

            if hasattr(existing, "category_id"):
                existing.category_id = category.id

            if hasattr(existing, "category"):
                existing.category = category

            skill = existing

        else:

            skill_kwargs = {
                "slug": slug,
                "name": item["name"],
            }

            if hasattr(Skill, "description"):
                skill_kwargs["description"] = item.get(
                    "description"
                )

            if hasattr(Skill, "category_id"):
                skill_kwargs["category_id"] = category.id

            if hasattr(Skill, "category"):
                skill_kwargs["category"] = category

            skill = Skill(
                **skill_kwargs
            )

            session.add(skill)

        result[slug] = skill

    session.flush()

    return result


# ---------------------------------------------------------------------
# Competency seeding
#
# IMPORTANT:
# Competency does NOT have a slug column in the SQLAlchemy model.
#
# The catalogue JSON still uses "slug" as its external identifier.
# We therefore use:
#
#     competency.name + competency.skill_id
#
# to find an existing database record.
#
# The JSON slug remains the key in the returned competency map.
# ---------------------------------------------------------------------

def seed_competencies(
    session: Session,
    items: list[dict],
    skills: dict[str, Skill],
) -> dict[str, Competency]:

    result: dict[str, Competency] = {}

    for item in items:

        slug = item["slug"]
        skill_slug = item["skill"]

        if skill_slug not in skills:
            raise ValueError(
                f"Competency '{slug}' references "
                f"unknown skill '{skill_slug}'."
            )

        skill = skills[skill_slug]

        # -------------------------------------------------------------
        # Competency has no slug column.
        #
        # Use name + skill_id as the database identity.
        # -------------------------------------------------------------

        existing = session.execute(
            select(Competency).where(
                Competency.name == item["name"],
                Competency.skill_id == skill.id,
            )
        ).scalar_one_or_none()

        if existing:

            existing.name = item["name"]

            if hasattr(existing, "description"):
                existing.description = item.get(
                    "description"
                )

            if hasattr(existing, "target_default"):
                existing.target_default = item.get(
                    "target_default",
                    80,
                )

            if hasattr(existing, "skill_id"):
                existing.skill_id = skill.id

            if hasattr(existing, "skill"):
                existing.skill = skill

            competency = existing

        else:

            competency_kwargs = {
                "name": item["name"],
            }

            if hasattr(Competency, "description"):
                competency_kwargs["description"] = item.get(
                    "description"
                )

            if hasattr(Competency, "target_default"):
                competency_kwargs["target_default"] = item.get(
                    "target_default",
                    80,
                )

            if hasattr(Competency, "skill_id"):
                competency_kwargs["skill_id"] = skill.id

            if hasattr(Competency, "skill"):
                competency_kwargs["skill"] = skill

            competency = Competency(
                **competency_kwargs
            )

            session.add(competency)

        # -------------------------------------------------------------
        # Keep the catalogue slug available to the seeder.
        #
        # The database model itself does not store this slug.
        # -------------------------------------------------------------

        result[slug] = competency

    session.flush()

    return result


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------

def validate_references(
    domains: list[dict],
    categories: list[dict],
    skills: list[dict],
    competencies: list[dict],
) -> None:

    domain_slugs = {
        item["slug"]
        for item in domains
    }

    category_slugs = {
        item["slug"]
        for item in categories
    }

    skill_slugs = {
        item["slug"]
        for item in skills
    }

    for item in categories:

        if item["domain"] not in domain_slugs:
            raise ValueError(
                f"Invalid category reference: "
                f"{item['slug']} -> {item['domain']}"
            )

    for item in skills:

        if item["category"] not in category_slugs:
            raise ValueError(
                f"Invalid skill reference: "
                f"{item['slug']} -> {item['category']}"
            )

    for item in competencies:

        if item["skill"] not in skill_slugs:
            raise ValueError(
                f"Invalid competency reference: "
                f"{item['slug']} -> {item['skill']}"
            )


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> None:

    banner("SkillTwin Master Catalogue Seeder")

    domains = load_json(DOMAINS_FILE)
    categories = load_json(CATEGORIES_FILE)
    skills = load_json(SKILLS_FILE)
    competencies = load_json(COMPETENCIES_FILE)

    print(f"Loaded {len(domains)} domains")
    print(f"Loaded {len(categories)} categories")
    print(f"Loaded {len(skills)} skills")
    print(f"Loaded {len(competencies)} competencies")

    print()
    print("Validating catalogue...")

    validate_unique_slugs(
        domains,
        "domains.json",
    )

    validate_unique_slugs(
        categories,
        "categories.json",
    )

    validate_unique_slugs(
        skills,
        "skills.json",
    )

    validate_unique_slugs(
        competencies,
        "competencies.json",
    )

    validate_references(
        domains,
        categories,
        skills,
        competencies,
    )

    print("Catalogue validation passed.")

    session = SessionLocal()

    try:

        domain_map = seed_domains(
            session,
            domains,
        )

        print(
            f"✓ Domains processed: "
            f"{len(domain_map)}"
        )

        category_map = seed_categories(
            session,
            categories,
            domain_map,
        )

        print(
            f"✓ Categories processed: "
            f"{len(category_map)}"
        )

        skill_map = seed_skills(
            session,
            skills,
            category_map,
        )

        print(
            f"✓ Skills processed: "
            f"{len(skill_map)}"
        )

        competency_map = seed_competencies(
            session,
            competencies,
            skill_map,
        )

        print(
            f"✓ Competencies processed: "
            f"{len(competency_map)}"
        )

        session.commit()

        banner("CATALOGUE SEEDING COMPLETE")

        print(
            f"Domains       : {len(domain_map)}"
        )

        print(
            f"Categories    : {len(category_map)}"
        )

        print(
            f"Skills        : {len(skill_map)}"
        )

        print(
            f"Competencies  : {len(competency_map)}"
        )

        print()
        print(
            "The catalogue is ready for SkillTwin."
        )
        print()

    except Exception as exc:

        session.rollback()

        banner("CATALOGUE SEEDING FAILED")

        print(str(exc))
        print()

        raise

    finally:

        session.close()


if __name__ == "__main__":
    main()