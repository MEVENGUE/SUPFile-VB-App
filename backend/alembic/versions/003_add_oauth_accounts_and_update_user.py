"""add oauth_accounts table and update users table

Revision ID: 003_add_oauth_accounts
Revises: 002_add_share_links
Create Date: 2026-01-01 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003_add_oauth_accounts'
down_revision: Union[str, None] = '002_add_share_links'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if 'oauth_accounts' table exists before creating
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'oauth_accounts' not in tables:
        op.create_table(
            'oauth_accounts',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('provider', sa.String(), nullable=False),
            sa.Column('provider_user_id', sa.String(), nullable=False),
            sa.Column('provider_email', sa.String(), nullable=True),
            sa.Column('access_token', sa.String(), nullable=True),
            sa.Column('refresh_token', sa.String(), nullable=True),
            sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('provider', 'provider_user_id', name='uq_oauth_provider_user')
        )
        op.create_index(op.f('ix_oauth_accounts_id'), 'oauth_accounts', ['id'], unique=False)
        op.create_index(op.f('ix_oauth_accounts_user_id'), 'oauth_accounts', ['user_id'], unique=False)
        print("Table 'oauth_accounts' created successfully.")
    else:
        print("Table 'oauth_accounts' already exists. Skipping creation.")

    # Update users.hashed_password to be nullable (for OAuth2 users)
    columns = inspector.get_columns('users')
    column_names = [col['name'] for col in columns]
    
    if 'hashed_password' in column_names:
        # Check if column is already nullable
        hashed_password_col = next(col for col in columns if col['name'] == 'hashed_password')
        if hashed_password_col['nullable'] is False:
            op.alter_column('users', 'hashed_password', nullable=True)
            print("Column 'users.hashed_password' updated to nullable.")
        else:
            print("Column 'users.hashed_password' is already nullable. Skipping update.")


def downgrade() -> None:
    # Make hashed_password NOT NULL again (may fail if OAuth users exist)
    op.alter_column('users', 'hashed_password', nullable=False)
    
    # Drop indexes
    op.drop_index(op.f('ix_oauth_accounts_user_id'), table_name='oauth_accounts')
    op.drop_index(op.f('ix_oauth_accounts_id'), table_name='oauth_accounts')
    
    # Drop table
    op.drop_table('oauth_accounts')

