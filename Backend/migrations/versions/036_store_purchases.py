"""add store purchases

Revision ID: 036_store_purchases
Revises: 035_store_products
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = '036_store_purchases'
down_revision = '035_store_products'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'store_purchase',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_name', sa.String(length=120), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('purchased_at', sa.DateTime(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.CheckConstraint('unit_price >= 0', name='ck_store_purchase_unit_price'),
        sa.ForeignKeyConstraint(['product_id'], ['store_product.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_store_purchase_product_id', 'store_purchase', ['product_id'], unique=False
    )
    op.create_index(
        'ix_store_purchase_user_id', 'store_purchase', ['user_id'], unique=False
    )


def downgrade():
    op.drop_index('ix_store_purchase_user_id', table_name='store_purchase')
    op.drop_index('ix_store_purchase_product_id', table_name='store_purchase')
    op.drop_table('store_purchase')
