"""add share_links table

Revision ID: 002_add_share_links
Revises: 001_add_folders
Create Date: 2026-01-01 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_add_share_links'
down_revision: Union[str, None] = '001_add_folders'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if 'share_links' table exists before creating
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'share_links' not in tables:
        op.create_table(
            'share_links',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('token', sa.String(), nullable=False),
            sa.Column('file_id', sa.Integer(), nullable=True),
            sa.Column('folder_id', sa.Integer(), nullable=True),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('password_hash', sa.String(), nullable=True),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('1')),
            sa.Column('access_count', sa.Integer(), nullable=True, server_default=sa.text('0')),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['file_id'], ['files.id'], ),
            sa.ForeignKeyConstraint(['folder_id'], ['folders.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_share_links_id'), 'share_links', ['id'], unique=False)
        op.create_index(op.f('ix_share_links_token'), 'share_links', ['token'], unique=True)
        op.create_index(op.f('ix_share_links_file_id'), 'share_links', ['file_id'], unique=False)
        op.create_index(op.f('ix_share_links_folder_id'), 'share_links', ['folder_id'], unique=False)
        op.create_index(op.f('ix_share_links_user_id'), 'share_links', ['user_id'], unique=False)
        print("Table 'share_links' created successfully.")
    else:
        print("Table 'share_links' already exists. Skipping creation.")


def downgrade() -> None:
    # Drop indexes first
    op.drop_index(op.f('ix_share_links_user_id'), table_name='share_links')
    op.drop_index(op.f('ix_share_links_folder_id'), table_name='share_links')
    op.drop_index(op.f('ix_share_links_file_id'), table_name='share_links')
    op.drop_index(op.f('ix_share_links_token'), table_name='share_links')
    op.drop_index(op.f('ix_share_links_id'), table_name='share_links')
    
    # Drop table
    op.drop_table('share_links')

