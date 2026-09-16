"""add member todo requests

Revision ID: 033_todo_requests
Revises: 032_project_todo_settings
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = '033_todo_requests'
down_revision = '032_project_todo_settings'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'todo_request' in inspector.get_table_names():
        return

    op.create_table(
        'todo_request',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('text', sa.String(length=200), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('requested_by_id', sa.Integer(), nullable=False),
        sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
        sa.Column('accepted_todo_id', sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected')",
            name='ck_todo_request_status',
        ),
        sa.ForeignKeyConstraint(['accepted_todo_id'], ['todo.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['project_recruitment.id']),
        sa.ForeignKeyConstraint(['requested_by_id'], ['user.id']),
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('accepted_todo_id'),
    )
    op.create_index('ix_todo_request_project_id', 'todo_request', ['project_id'])
    op.create_index('ix_todo_request_status', 'todo_request', ['status'])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'todo_request' in inspector.get_table_names():
        op.drop_index('ix_todo_request_status', table_name='todo_request')
        op.drop_index('ix_todo_request_project_id', table_name='todo_request')
        op.drop_table('todo_request')
