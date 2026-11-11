from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CitizenReport(Base):
    __tablename__ = "citizen_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, default=lambda: str(uuid4()))
    category: Mapped[str] = mapped_column(String(32), index=True)
    village_name: Mapped[str] = mapped_column(String(160), index=True)
    district: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="submitted")
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
