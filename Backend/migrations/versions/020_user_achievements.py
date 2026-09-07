"""server verified user achievements

Revision ID: 020_user_achievements
Revises: 019_user_schedule
Create Date: 2026-09-08
"""

from alembic import op
import sqlalchemy as sa


revision = '020_user_achievements'
down_revision = '019_user_schedule'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'user_achievement' in inspector.get_table_names():
        return

    op.create_table(
        'user_achievement',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('achievement_key', sa.String(length=50), nullable=False),
        sa.Column('unlocked_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'achievement_key', name='uq_user_achievement_key'),
    )
    op.create_index('ix_user_achievement_user_id', 'user_achievement', ['user_id'])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'user_achievement' in inspector.get_table_names():
        op.drop_index('ix_user_achievement_user_id', table_name='user_achievement')
        op.drop_table('user_achievement')
