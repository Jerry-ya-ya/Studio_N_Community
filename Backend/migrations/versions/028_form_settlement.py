"""add form settlement scheduling

Revision ID: 028_form_settlement
Revises: 027_form_submissions
Create Date: 2026-09-14
"""

from alembic import op
import sqlalchemy as sa


revision = '028_form_settlement'
down_revision = '027_form_submissions'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column_names = {
        column['name'] for column in inspector.get_columns('form_template')
    }
    if 'settlement_at' not in column_names:
        op.add_column(
            'form_template', sa.Column('settlement_at', sa.DateTime(), nullable=True)
        )
    if 'settled_at' not in column_names:
        op.add_column(
            'form_template', sa.Column('settled_at', sa.DateTime(), nullable=True)
        )

    inspector = sa.inspect(bind)
    index_names = {index['name'] for index in inspector.get_indexes('form_template')}
    if 'ix_form_template_settlement_at' not in index_names:
        op.create_index(
            'ix_form_template_settlement_at',
            'form_template',
            ['settlement_at'],
            unique=False,
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    index_names = {index['name'] for index in inspector.get_indexes('form_template')}
    if 'ix_form_template_settlement_at' in index_names:
        op.drop_index('ix_form_template_settlement_at', table_name='form_template')

    column_names = {
        column['name'] for column in inspector.get_columns('form_template')
    }
    if 'settled_at' in column_names:
        op.drop_column('form_template', 'settled_at')
    if 'settlement_at' in column_names:
        op.drop_column('form_template', 'settlement_at')
