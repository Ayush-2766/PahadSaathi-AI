"""add optional GPS coordinates to citizen reports"""
from alembic import op
import sqlalchemy as sa

revision = "20261111_03"
down_revision = "20261108_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("citizen_reports", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("citizen_reports", sa.Column("longitude", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("citizen_reports", "longitude")
    op.drop_column("citizen_reports", "latitude")
