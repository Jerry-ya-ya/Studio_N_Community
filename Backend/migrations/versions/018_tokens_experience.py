"""tokens and experience

Revision ID: 018_tokens_experience
Revises: 017_activity_time
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa


revision = '018_tokens_experience'
down_revision = '017_activity_time'
branch_labels = None
depends_on = None


def has_column(inspector, table_name, column_name):
    return column_name in [column['name'] for column in inspector.get_columns(table_name)]


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not has_column(inspector, 'user', 'experience'):
        op.add_column('user', sa.Column('experience', sa.Integer(), nullable=True))
        op.execute(sa.text('UPDATE "user" SET experience = 0 WHERE experience IS NULL'))
        op.alter_column('user', 'experience', nullable=False, server_default='0')

    if not has_column(inspector, 'project_recruitment', 'token_budget'):
        op.add_column('project_recruitment', sa.Column('token_budget', sa.Integer(), nullable=True))
        op.execute(sa.text('UPDATE project_recruitment SET token_budget = 100 WHERE token_budget IS NULL'))
        op.alter_column('project_recruitment', 'token_budget', nullable=False, server_default='100')

    if not has_column(inspector, 'project_recruitment', 'token_used'):
        op.add_column('project_recruitment', sa.Column('token_used', sa.Integer(), nullable=True))
        op.execute(sa.text('UPDATE project_recruitment SET token_used = 0 WHERE token_used IS NULL'))
        op.alter_column('project_recruitment', 'token_used', nullable=False, server_default='0')


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if has_column(inspector, 'project_recruitment', 'token_used'):
        op.drop_column('project_recruitment', 'token_used')

    if has_column(inspector, 'project_recruitment', 'token_budget'):
        op.drop_column('project_recruitment', 'token_budget')

    if has_column(inspector, 'user', 'experience'):
        op.drop_column('user', 'experience')
