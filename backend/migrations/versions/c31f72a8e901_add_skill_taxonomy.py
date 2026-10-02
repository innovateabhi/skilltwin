"""add skill taxonomy

Revision ID: c31f72a8e901
Revises: b7c91d4e2f10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision: str = "c31f72a8e901"
down_revision: Union[str, None] = "b7c91d4e2f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ============================================================
    # DOMAINS
    # ============================================================

    op.create_table(
        "domains",

        sa.Column(
            "id",
            mysql.BIGINT(unsigned=True),
            autoincrement=True,
            nullable=False,
        ),

        sa.Column(
            "name",
            sa.String(150),
            nullable=False,
        ),

        sa.Column(
            "slug",
            sa.String(160),
            nullable=False,
        ),

        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text(
                "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
            ),
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "name",
            name="uq_domains_name",
        ),

        sa.UniqueConstraint(
            "slug",
            name="uq_domains_slug",
        ),
    )

    op.create_index(
        "ix_domains_name",
        "domains",
        ["name"],
    )

    op.create_index(
        "ix_domains_slug",
        "domains",
        ["slug"],
    )

    op.create_index(
        "ix_domains_is_active",
        "domains",
        ["is_active"],
    )

    # ============================================================
    # SKILL CATEGORIES
    # ============================================================

    op.create_table(
        "skill_categories",

        sa.Column(
            "id",
            mysql.BIGINT(unsigned=True),
            autoincrement=True,
            nullable=False,
        ),

        sa.Column(
            "domain_id",
            mysql.BIGINT(unsigned=True),
            nullable=False,
        ),

        sa.Column(
            "name",
            sa.String(150),
            nullable=False,
        ),

        sa.Column(
            "slug",
            sa.String(160),
            nullable=False,
        ),

        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text(
                "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
            ),
        ),

        sa.ForeignKeyConstraint(
            ["domain_id"],
            ["domains.id"],
            name="fk_skill_categories_domain_id",
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "slug",
            name="uq_skill_categories_slug",
        ),
    )

    op.create_index(
        "ix_skill_categories_domain_id",
        "skill_categories",
        ["domain_id"],
    )

    op.create_index(
        "ix_skill_categories_name",
        "skill_categories",
        ["name"],
    )

    op.create_index(
        "ix_skill_categories_is_active",
        "skill_categories",
        ["is_active"],
    )

    # ============================================================
    # MODIFY SKILLS
    # ============================================================

    op.add_column(
        "skills",
        sa.Column(
            "category_id",
            mysql.BIGINT(unsigned=True),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_skills_category_id",
        "skills",
        ["category_id"],
    )

    op.create_foreign_key(
        "fk_skills_category_id",
        "skills",
        "skill_categories",
        ["category_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:

    op.drop_constraint(
        "fk_skills_category_id",
        "skills",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_skills_category_id",
        table_name="skills",
    )

    op.drop_column(
        "skills",
        "category_id",
    )

    op.drop_index(
        "ix_skill_categories_is_active",
        table_name="skill_categories",
    )

    op.drop_index(
        "ix_skill_categories_name",
        table_name="skill_categories",
    )

    op.drop_index(
        "ix_skill_categories_domain_id",
        table_name="skill_categories",
    )

    op.drop_table("skill_categories")

    op.drop_index(
        "ix_domains_is_active",
        table_name="domains",
    )

    op.drop_index(
        "ix_domains_slug",
        table_name="domains",
    )

    op.drop_index(
        "ix_domains_name",
        table_name="domains",
    )

    op.drop_table("domains")