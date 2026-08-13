"""add post like table

Revision ID: 015_post_like
Revises: 014_activity
Create Date: 2026-08-13
"""

from alembic import op
import sqlalchemy as sa


revision = '015_post_like'
down_revision = '014_activity'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'post_like' not in inspector.get_table_names():
        op.create_table(
            'post_like',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('post_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['post_id'], ['post.id']),
            sa.ForeignKeyConstraint(['user_id'], ['user.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('post_id', 'user_id', name='uq_post_like_post_user')
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'post_like' in inspector.get_table_names():
        op.drop_table('post_like')
