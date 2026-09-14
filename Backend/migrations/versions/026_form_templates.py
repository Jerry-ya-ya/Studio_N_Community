"""add JSONB-backed admin form templates

Revision ID: 026_form_templates
Revises: 025_user_profile_capabilities
Create Date: 2026-09-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '026_form_templates'
down_revision = '025_user_profile_capabilities'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'form_template' in inspector.get_table_names():
        index_names = {index['name'] for index in inspector.get_indexes('form_template')}
        if 'ix_form_template_created_by_id' not in index_names:
            op.create_index(
                'ix_form_template_created_by_id',
                'form_template',
                ['created_by_id'],
                unique=False,
            )
        return

    definition_type = sa.JSON().with_variant(postgresql.JSONB(), 'postgresql')
    op.create_table(
        'form_template',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=120), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('definition', definition_type, nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_form_template_created_by_id', 'form_template', ['created_by_id'], unique=False
    )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'form_template' in inspector.get_table_names():
        index_names = {index['name'] for index in inspector.get_indexes('form_template')}
        if 'ix_form_template_created_by_id' in index_names:
            op.drop_index('ix_form_template_created_by_id', table_name='form_template')
        op.drop_table('form_template')
