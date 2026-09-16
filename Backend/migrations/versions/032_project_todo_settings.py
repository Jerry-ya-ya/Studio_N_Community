"""add project todo leader self-completion setting

Revision ID: 032_project_todo_settings
Revises: 031_rate_limit_override
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = '032_project_todo_settings'
down_revision = '031_rate_limit_override'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column_names = {
        column['name'] for column in inspector.get_columns('project_recruitment')
    }
    if 'leader_self_completion_blocked' not in column_names:
        op.add_column(
            'project_recruitment',
            sa.Column(
                'leader_self_completion_blocked',
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column_names = {
        column['name'] for column in inspector.get_columns('project_recruitment')
    }
    if 'leader_self_completion_blocked' in column_names:
        op.drop_column('project_recruitment', 'leader_self_completion_blocked')
