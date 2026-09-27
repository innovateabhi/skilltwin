"""add competency tables

Revision ID: b7c91d4e2f10
Revises: 844af562c55a
Create Date: 2026-09-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = "b7c91d4e2f10"
down_revision: Union[str, None] = "844af562c55a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================================
    # 1. SKILLS
    # ============================================================

    op.create_table(
        "skills",
        sa.Column(
            "id",
            mysql.BIGINT(unsigned=True),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=150),
            nullable=False,
        ),
        sa.Column(
            "slug",
            sa.String(length=160),
            nullable=False,
        ),
        sa.Column(
            "category",
            sa.String(length=100),
            nullable=True,
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
        sa.UniqueConstraint("name", name="uq_skills_name"),
        sa.UniqueConstraint("slug", name="uq_skills_slug"),
    )

    op.create_index(
        "ix_skills_name",
        "skills",
        ["name"],
        unique=False,
    )

    op.create_index(
        "ix_skills_slug",
        "skills",
        ["slug"],
        unique=False,
    )

    op.create_index(
        "ix_skills_category",
        "skills",
        ["category"],
        unique=False,
    )

    op.create_index(
        "ix_skills_is_active",
        "skills",
        ["is_active"],
        unique=False,
    )

    # ============================================================
    # 2. COMPETENCIES
    # ============================================================

    op.create_table(
        "competencies",
        sa.Column(
            "id",
            mysql.BIGINT(unsigned=True),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "skill_id",
            mysql.BIGINT(unsigned=True),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=150),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "target_default",
            sa.Integer(),
            nullable=False,
            server_default="80",
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
            ["skill_id"],
            ["skills.id"],
            name="fk_competencies_skill_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_competencies_skill_id",
        "competencies",
        ["skill_id"],
        unique=False,
    )

    op.create_index(
        "ix_competencies_name",
        "competencies",
        ["name"],
        unique=False,
    )

    op.create_index(
        "ix_competencies_is_active",
        "competencies",
        ["is_active"],
        unique=False,
    )

    # ============================================================
    # 3. TRAINEE COMPETENCIES
    # ============================================================

    op.create_table(
        "trainee_competencies",
        sa.Column(
            "id",
            mysql.BIGINT(unsigned=True),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "trainee_id",
            mysql.BIGINT(unsigned=True),
            nullable=False,
        ),
        sa.Column(
            "competency_id",
            mysql.BIGINT(unsigned=True),
            nullable=False,
        ),
        sa.Column(
            "current_score",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "target_score",
            sa.Integer(),
            nullable=False,
            server_default="80",
        ),
        sa.Column(
            "last_assessed_at",
            sa.DateTime(),
            nullable=True,
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
            ["trainee_id"],
            ["trainees.id"],
            name="fk_trainee_competencies_trainee_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["competency_id"],
            ["competencies.id"],
            name="fk_trainee_competencies_competency_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trainee_id",
            "competency_id",
            name="uq_trainee_competency",
        ),
    )

    op.create_index(
        "ix_trainee_competencies_trainee_id",
        "trainee_competencies",
        ["trainee_id"],
        unique=False,
    )

    op.create_index(
        "ix_trainee_competencies_competency_id",
        "trainee_competencies",
        ["competency_id"],
        unique=False,
    )

    # ============================================================
    # 4. COMPETENCY HISTORY
    # ============================================================

    op.create_table(
        "competency_history",
        sa.Column(
            "id",
            mysql.BIGINT(unsigned=True),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "trainee_id",
            mysql.BIGINT(unsigned=True),
            nullable=False,
        ),
        sa.Column(
            "competency_id",
            mysql.BIGINT(unsigned=True),
            nullable=False,
        ),
        sa.Column(
            "score",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "previous_score",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "source",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "reference_id",
            mysql.BIGINT(unsigned=True),
            nullable=True,
        ),
        sa.Column(
            "recorded_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["trainee_id"],
            ["trainees.id"],
            name="fk_competency_history_trainee_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["competency_id"],
            ["competencies.id"],
            name="fk_competency_history_competency_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_competency_history_trainee_id",
        "competency_history",
        ["trainee_id"],
        unique=False,
    )

    op.create_index(
        "ix_competency_history_competency_id",
        "competency_history",
        ["competency_id"],
        unique=False,
    )

    op.create_index(
        "ix_competency_history_recorded_at",
        "competency_history",
        ["recorded_at"],
        unique=False,
    )

    # ============================================================
    # 5. SKILL GAPS
    # ============================================================

    op.create_table(
        "skill_gaps",
        sa.Column(
            "id",
            mysql.BIGINT(unsigned=True),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "trainee_id",
            mysql.BIGINT(unsigned=True),
            nullable=False,
        ),
        sa.Column(
            "skill_id",
            mysql.BIGINT(unsigned=True),
            nullable=False,
        ),
        sa.Column(
            "current_score",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "target_score",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "gap_score",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="open",
        ),
        sa.Column(
            "calculated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(
            ["trainee_id"],
            ["trainees.id"],
            name="fk_skill_gaps_trainee_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"],
            ["skills.id"],
            name="fk_skill_gaps_skill_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trainee_id",
            "skill_id",
            name="uq_trainee_skill_gap",
        ),
    )

    op.create_index(
        "ix_skill_gaps_trainee_id",
        "skill_gaps",
        ["trainee_id"],
        unique=False,
    )

    op.create_index(
        "ix_skill_gaps_skill_id",
        "skill_gaps",
        ["skill_id"],
        unique=False,
    )

    op.create_index(
        "ix_skill_gaps_severity",
        "skill_gaps",
        ["severity"],
        unique=False,
    )

    op.create_index(
        "ix_skill_gaps_status",
        "skill_gaps",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    # Reverse order because of foreign-key dependencies.

    op.drop_index(
        "ix_skill_gaps_status",
        table_name="skill_gaps",
    )
    op.drop_index(
        "ix_skill_gaps_severity",
        table_name="skill_gaps",
    )
    op.drop_index(
        "ix_skill_gaps_skill_id",
        table_name="skill_gaps",
    )
    op.drop_index(
        "ix_skill_gaps_trainee_id",
        table_name="skill_gaps",
    )
    op.drop_table("skill_gaps")

    op.drop_index(
        "ix_competency_history_recorded_at",
        table_name="competency_history",
    )
    op.drop_index(
        "ix_competency_history_competency_id",
        table_name="competency_history",
    )
    op.drop_index(
        "ix_competency_history_trainee_id",
        table_name="competency_history",
    )
    op.drop_table("competency_history")

    op.drop_index(
        "ix_trainee_competencies_competency_id",
        table_name="trainee_competencies",
    )
    op.drop_index(
        "ix_trainee_competencies_trainee_id",
        table_name="trainee_competencies",
    )
    op.drop_table("trainee_competencies")

    op.drop_index(
        "ix_competencies_is_active",
        table_name="competencies",
    )
    op.drop_index(
        "ix_competencies_name",
        table_name="competencies",
    )
    op.drop_index(
        "ix_competencies_skill_id",
        table_name="competencies",
    )
    op.drop_table("competencies")

    op.drop_index(
        "ix_skills_is_active",
        table_name="skills",
    )
    op.drop_index(
        "ix_skills_category",
        table_name="skills",
    )
    op.drop_index(
        "ix_skills_slug",
        table_name="skills",
    )
    op.drop_index(
        "ix_skills_name",
        table_name="skills",
    )
    op.drop_table("skills")