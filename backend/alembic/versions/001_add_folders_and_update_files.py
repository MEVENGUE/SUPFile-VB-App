"""Add folders and update files table

Revision ID: 001_add_folders
Revises: 
Create Date: 2024-12-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_add_folders'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if folders table exists
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    # Create folders table only if it doesn't exist
    if 'folders' not in tables:
        op.create_table(
            'folders',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('parent_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['parent_id'], ['folders.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_folders_id'), 'folders', ['id'], unique=False)
        op.create_index(op.f('ix_folders_parent_id'), 'folders', ['parent_id'], unique=False)
        op.create_index(op.f('ix_folders_user_id'), 'folders', ['user_id'], unique=False)
    else:
        # Table exists, check if indexes exist
        indexes = [idx['name'] for idx in inspector.get_indexes('folders')]
        if 'ix_folders_id' not in indexes:
            op.create_index(op.f('ix_folders_id'), 'folders', ['id'], unique=False)
        if 'ix_folders_parent_id' not in indexes:
            op.create_index(op.f('ix_folders_parent_id'), 'folders', ['parent_id'], unique=False)
        if 'ix_folders_user_id' not in indexes:
            op.create_index(op.f('ix_folders_user_id'), 'folders', ['user_id'], unique=False)
    
    # Check if files table exists and get its columns
    if 'files' in tables:
        files_columns = [col['name'] for col in inspector.get_columns('files')]
        
        # Add folder_id column if it doesn't exist
        if 'folder_id' not in files_columns:
            op.add_column('files', sa.Column('folder_id', sa.Integer(), nullable=True))
            op.create_index(op.f('ix_files_folder_id'), 'files', ['folder_id'], unique=False)
            op.create_foreign_key('fk_files_folder_id', 'files', 'folders', ['folder_id'], ['id'])
        else:
            # Column exists, check if index and foreign key exist
            files_indexes = [idx['name'] for idx in inspector.get_indexes('files')]
            if 'ix_files_folder_id' not in files_indexes:
                op.create_index(op.f('ix_files_folder_id'), 'files', ['folder_id'], unique=False)
            
            # Check foreign keys
            fk_constraints = [fk['name'] for fk in inspector.get_foreign_keys('files')]
            if 'fk_files_folder_id' not in fk_constraints:
                op.create_foreign_key('fk_files_folder_id', 'files', 'folders', ['folder_id'], ['id'])
        
        # Add deleted_at column if it doesn't exist
        if 'deleted_at' not in files_columns:
            op.add_column('files', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove foreign key and index for folder_id
    op.drop_constraint('fk_files_folder_id', 'files', type_='foreignkey')
    op.drop_index(op.f('ix_files_folder_id'), table_name='files')
    
    # Remove columns from files table
    op.drop_column('files', 'deleted_at')
    op.drop_column('files', 'folder_id')
    
    # Drop folders table
    op.drop_index(op.f('ix_folders_user_id'), table_name='folders')
    op.drop_index(op.f('ix_folders_parent_id'), table_name='folders')
    op.drop_index(op.f('ix_folders_id'), table_name='folders')
    op.drop_table('folders')

