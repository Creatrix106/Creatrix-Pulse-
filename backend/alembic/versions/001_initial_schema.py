"""Initial schema for Creatrix Pulse PostgreSQL 15+

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-05 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), server_default="admin", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_users_email", "users", ["email"], unique=True)

    # Datasets
    op.create_table(
        "datasets",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_size", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("row_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("column_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("columns", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("date_range", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("filter_options", postgresql.JSONB(astext_type=sa.Text()), server_default='{"categories": [], "regions": []}', nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("schema_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.BigInteger(), nullable=True),
    )
    op.create_index("idx_datasets_status", "datasets", ["status"])
    op.create_index("idx_datasets_user_id", "datasets", ["user_id"])

    # Dataset Rows
    op.create_table(
        "dataset_rows",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("dataset_id", sa.String(length=64), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id", sa.String(length=128), nullable=True),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("product_id", sa.String(length=128), nullable=True),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("product_category", sa.String(length=128), nullable=True),
        sa.Column("region", sa.String(length=128), nullable=True),
        sa.Column("customer_identifier", sa.String(length=128), nullable=True),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column("unit_price", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("revenue", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("cost", sa.Float(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index("idx_dataset_rows_dataset_date", "dataset_rows", ["dataset_id", "transaction_date"])
    op.create_index("idx_dataset_rows_category", "dataset_rows", ["dataset_id", "product_category"])
    op.create_index("idx_dataset_rows_region", "dataset_rows", ["dataset_id", "region"])
    op.create_index("idx_dataset_rows_customer", "dataset_rows", ["dataset_id", "customer_identifier"])
    op.create_index("idx_dataset_rows_product", "dataset_rows", ["dataset_id", "product_id"])

    # Dataset Mappings
    op.create_table(
        "dataset_mappings",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("dataset_id", sa.String(length=64), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_column", sa.String(length=255), nullable=False),
        sa.Column("target_dimension", sa.String(length=128), nullable=False),
        sa.Column("data_type", sa.String(length=64), server_default="string", nullable=False),
    )

    # Reports
    op.create_table(
        "reports",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("dataset_id", sa.String(length=64), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(length=64), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("format", sa.String(length=50), server_default="csv", nullable=False),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("row_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("download_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_reports_dataset_id", "reports", ["dataset_id"])

def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("dataset_mappings")
    op.drop_table("dataset_rows")
    op.drop_table("datasets")
    op.drop_table("users")
