"""add form settlement scheduling

Revision ID: 027_form_settlement
Revises: 026_form_submissions
Create Date: 2026-09-14
"""

from alembic import op
import sqlalchemy as sa


revision = '027_form_settlement'
down_revision = '026_form_submissions'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('form_template', sa.Column('settlement_at', sa.DateTime(), nullable=True))
    op.add_column('form_template', sa.Column('settled_at', sa.DateTime(), nullable=True))
    op.create_index(
        'ix_form_template_settlement_at', 'form_template', ['settlement_at'], unique=False
    )


def downgrade():
    op.drop_index('ix_form_template_settlement_at', table_name='form_template')
    op.drop_column('form_template', 'settled_at')
    op.drop_column('form_template', 'settlement_at')
