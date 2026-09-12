"""refresh token rotation and revocation

Revision ID: 022_refresh_token_rotation
Revises: 021_project_levels
Create Date: 2026-09-12
"""

from alembic import op
import sqlalchemy as sa


revision = '022_refresh_token_rotation'
down_revision = '021_project_levels'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'refresh_token' in inspector.get_table_names():
        return

    op.create_table(
        'refresh_token',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('jti', sa.String(length=36), nullable=False),
        sa.Column('family_id', sa.String(length=36), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('replaced_by_jti', sa.String(length=36), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_refresh_token_jti', 'refresh_token', ['jti'], unique=True)
    op.create_index('ix_refresh_token_user_id', 'refresh_token', ['user_id'])
    op.create_index(
        'ix_refresh_token_family_revoked',
        'refresh_token',
        ['family_id', 'revoked_at'],
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'refresh_token' in inspector.get_table_names():
        op.drop_index('ix_refresh_token_family_revoked', table_name='refresh_token')
        op.drop_index('ix_refresh_token_user_id', table_name='refresh_token')
        op.drop_index('ix_refresh_token_jti', table_name='refresh_token')
        op.drop_table('refresh_token')
