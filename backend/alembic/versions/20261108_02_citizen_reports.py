"""add citizen reports"""
from alembic import op
import sqlalchemy as sa

revision = "20261108_02"
down_revision = "20261108_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "citizen_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False, unique=True),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("village_name", sa.String(160), nullable=False),
        sa.Column("district", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("photo_path", sa.String(500), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_citizen_reports_public_id", "citizen_reports", ["public_id"])
    op.create_index("ix_citizen_reports_category", "citizen_reports", ["category"])
    op.create_index("ix_citizen_reports_village_name", "citizen_reports", ["village_name"])
    op.create_index("ix_citizen_reports_district", "citizen_reports", ["district"])


def downgrade() -> None:
    op.drop_index("ix_citizen_reports_district", table_name="citizen_reports")
    op.drop_index("ix_citizen_reports_village_name", table_name="citizen_reports")
    op.drop_index("ix_citizen_reports_category", table_name="citizen_reports")
    op.drop_index("ix_citizen_reports_public_id", table_name="citizen_reports")
    op.drop_table("citizen_reports")
