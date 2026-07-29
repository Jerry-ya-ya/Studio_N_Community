"""home news background url

Revision ID: 008_news_bg
Revises: 007_user_github
Create Date: 2026-07-29
"""
from alembic import op
import sqlalchemy as sa


revision = "008_news_bg"
down_revision = "007_user_github"
branch_labels = None
depends_on = None


def has_table(inspector, table_name):
    return table_name in inspector.get_table_names()


def has_column(inspector, table_name, column_name):
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if has_table(inspector, "home_news_item") and not has_column(inspector, "home_news_item", "background_url"):
        op.add_column("home_news_item", sa.Column("background_url", sa.String(length=255), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if has_table(inspector, "home_news_item") and has_column(inspector, "home_news_item", "background_url"):
        op.drop_column("home_news_item", "background_url")
