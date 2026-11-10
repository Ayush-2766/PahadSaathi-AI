"""create initial schema"""
from alembic import op
import sqlalchemy as sa
revision = "20261108_01"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("villages", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(160), nullable=False), sa.Column("district", sa.String(120), nullable=False), sa.Column("tehsil", sa.String(120), nullable=True), sa.Column("latitude", sa.Float(), nullable=True), sa.Column("longitude", sa.Float(), nullable=True), sa.Column("boundary_geojson", sa.Text(), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_villages_name", "villages", ["name"])
    op.create_index("ix_villages_district", "villages", ["district"])
    op.create_table("reports", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("source", sa.String(32), nullable=False), sa.Column("text", sa.Text(), nullable=False), sa.Column("audio_path", sa.String(500), nullable=True), sa.Column("latitude", sa.Float(), nullable=True), sa.Column("longitude", sa.Float(), nullable=True), sa.Column("village_id", sa.Integer(), sa.ForeignKey("villages.id"), nullable=True), sa.Column("status", sa.String(32), nullable=False), sa.Column("reported_at", sa.DateTime(), nullable=False))
    op.create_table("incidents", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("title", sa.String(255), nullable=False), sa.Column("incident_type", sa.String(64), nullable=False), sa.Column("severity", sa.String(32), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("village_id", sa.Integer(), sa.ForeignKey("villages.id"), nullable=True), sa.Column("latitude", sa.Float(), nullable=True), sa.Column("longitude", sa.Float(), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.create_index("ix_incidents_incident_type", "incidents", ["incident_type"])
    op.create_index("ix_incidents_severity", "incidents", ["severity"])

def downgrade() -> None:
    op.drop_index("ix_incidents_severity", table_name="incidents")
    op.drop_index("ix_incidents_incident_type", table_name="incidents")
    op.drop_table("incidents")
    op.drop_table("reports")
    op.drop_index("ix_villages_district", table_name="villages")
    op.drop_index("ix_villages_name", table_name="villages")
    op.drop_table("villages")

