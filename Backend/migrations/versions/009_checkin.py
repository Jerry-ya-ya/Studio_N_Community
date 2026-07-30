"""daily check in

Revision ID: 009_checkin
Revises: 008_news_bg
Create Date: 2026-07-30
"""
from alembic import op
import sqlalchemy as sa


revision = "009_checkin"
down_revision = "008_news_bg"
branch_labels = None
depends_on = None


def has_table(inspector, table_name):
    return table_name in inspector.get_table_names()


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not has_table(inspector, "daily_check_in"):
        op.create_table(
            "daily_check_in",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("checkin_date", sa.Date(), nullable=False),
            sa.Column("points", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
            sa.UniqueConstraint("user_id", "checkin_date", name="uq_daily_check_in_user_date"),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if has_table(inspector, "daily_check_in"):
        op.drop_table("daily_check_in")
