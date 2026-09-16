"""add temporary API rate-limit override

Revision ID: 031_rate_limit_override
Revises: 030_user_activity_status
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = '031_rate_limit_override'
down_revision = '030_user_activity_status'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'api_rate_limit_override' not in inspector.get_table_names():
        op.create_table(
            'api_rate_limit_override',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('activated_at', sa.DateTime(), nullable=False),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('activated_by_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(
                ['activated_by_id'], ['user.id'], ondelete='SET NULL'
            ),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(
            'ix_api_rate_limit_override_expires_at',
            'api_rate_limit_override',
            ['expires_at'],
            unique=False,
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'api_rate_limit_override' in inspector.get_table_names():
        index_names = {
            index['name']
            for index in inspector.get_indexes('api_rate_limit_override')
        }
        if 'ix_api_rate_limit_override_expires_at' in index_names:
            op.drop_index(
                'ix_api_rate_limit_override_expires_at',
                table_name='api_rate_limit_override',
            )
        op.drop_table('api_rate_limit_override')
