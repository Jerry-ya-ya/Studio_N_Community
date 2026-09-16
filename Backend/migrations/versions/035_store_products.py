"""add store products

Revision ID: 035_store_products
Revises: 034_user_levels
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = '035_store_products'
down_revision = '034_user_levels'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'store_product',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('description', sa.Text(), nullable=False, server_default=''),
        sa.Column('price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('stock', sa.Integer(), nullable=False),
        sa.Column('is_limited', sa.Boolean(), nullable=False),
        sa.Column('is_published', sa.Boolean(), nullable=False),
        sa.Column('image_type', sa.String(length=20), nullable=False),
        sa.Column('image_value', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.CheckConstraint('price >= 0', name='ck_store_product_price'),
        sa.CheckConstraint('stock >= 0', name='ck_store_product_stock'),
        sa.CheckConstraint(
            "image_type IN ('default', 'upload')",
            name='ck_store_product_image_type',
        ),
        sa.ForeignKeyConstraint(['created_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_store_product_is_published',
        'store_product',
        ['is_published'],
        unique=False,
    )
    op.create_index(
        'ix_store_product_created_by_id',
        'store_product',
        ['created_by_id'],
        unique=False,
    )


def downgrade():
    op.drop_index('ix_store_product_created_by_id', table_name='store_product')
    op.drop_index('ix_store_product_is_published', table_name='store_product')
    op.drop_table('store_product')
