"""user schedule

Revision ID: 019_user_schedule
Revises: 018_tokens_experience
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa


revision = '019_user_schedule'
down_revision = '018_tokens_experience'
branch_labels = None
depends_on = None


def has_table(inspector, table_name):
    return table_name in inspector.get_table_names()


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not has_table(inspector, 'user_schedule'):
        op.create_table(
            'user_schedule',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('blocks', sa.JSON(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['user.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', name='uq_user_schedule_user_id'),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if has_table(inspector, 'user_schedule'):
        op.drop_table('user_schedule')
