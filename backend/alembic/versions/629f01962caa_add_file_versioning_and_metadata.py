"""add_file_versioning_and_metadata

Revision ID: 629f01962caa
Revises: 003_add_oauth_accounts
Create Date: 2026-01-02 15:30:45.118229

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '629f01962caa'
down_revision: Union[str, None] = '003_add_oauth_accounts'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "file_versions" not in tables:
        op.create_table(
            "file_versions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("file_id", sa.Integer(), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("blob_name", sa.String(), nullable=False),
            sa.Column("file_size", sa.BigInteger(), nullable=False),
            sa.Column("content_type", sa.String(), nullable=True),
            sa.Column("created_by", sa.Integer(), nullable=False),
            sa.Column("change_description", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=True,
            ),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["file_id"], ["files.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_file_versions_id"), "file_versions", ["id"], unique=False)
        op.create_index(
            op.f("ix_file_versions_file_id"), "file_versions", ["file_id"], unique=False
        )

    if "file_metadata" not in tables:
        op.create_table(
            "file_metadata",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("file_id", sa.Integer(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("tags", sa.String(), nullable=True),
            sa.Column("custom_metadata", sa.JSON(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=True,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["file_id"], ["files.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("file_id"),
        )
        op.create_index(op.f("ix_file_metadata_id"), "file_metadata", ["id"], unique=False)
        op.create_index(
            op.f("ix_file_metadata_file_id"), "file_metadata", ["file_id"], unique=False
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_file_metadata_file_id"), table_name="file_metadata")
    op.drop_index(op.f("ix_file_metadata_id"), table_name="file_metadata")
    op.drop_table("file_metadata")

    op.drop_index(op.f("ix_file_versions_file_id"), table_name="file_versions")
    op.drop_index(op.f("ix_file_versions_id"), table_name="file_versions")
    op.drop_table("file_versions")

