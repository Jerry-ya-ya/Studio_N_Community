"""project review

Revision ID: 012_project_review
Revises: 011_todo_levels
Create Date: 2026-08-04
"""
from alembic import op
import sqlalchemy as sa


revision = "012_project_review"
down_revision = "011_todo_levels"
branch_labels = None
depends_on = None


def has_column(inspector, table_name, column_name):
    return column_name in [column["name"] for column in inspector.get_columns(table_name)]


def has_check_constraint(inspector, table_name, constraint_name):
    return constraint_name in [
        constraint["name"]
        for constraint in inspector.get_check_constraints(table_name)
    ]


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not has_column(inspector, "project_recruitment", "review_status"):
        op.add_column(
            "project_recruitment",
            sa.Column("review_status", sa.String(length=20), nullable=True),
        )
        op.execute("UPDATE project_recruitment SET review_status = 'open' WHERE review_status IS NULL")
        op.alter_column("project_recruitment", "review_status", nullable=False)

    if not has_check_constraint(inspector, "project_recruitment", "ck_project_recruitment_review_status"):
        op.create_check_constraint(
            "ck_project_recruitment_review_status",
            "project_recruitment",
            "review_status IN ('open', 'pending', 'approved', 'rejected')",
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if has_check_constraint(inspector, "project_recruitment", "ck_project_recruitment_review_status"):
        op.drop_constraint(
            "ck_project_recruitment_review_status",
            "project_recruitment",
            type_="check",
        )

    if has_column(inspector, "project_recruitment", "review_status"):
        op.drop_column("project_recruitment", "review_status")
