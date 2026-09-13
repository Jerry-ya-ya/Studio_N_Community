"""merge migration heads

Revision ID: 024_merge_heads
Revises: 022_refresh_token_rotation, 023_user_pm_experience
Create Date: 2026-09-13
"""


revision = '024_merge_heads'
down_revision = ('022_refresh_token_rotation', '023_user_pm_experience')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
