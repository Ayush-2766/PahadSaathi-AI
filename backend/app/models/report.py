from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(32), default="citizen")
    text: Mapped[str] = mapped_column(Text)
    audio_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    village_id: Mapped[int | None] = mapped_column(ForeignKey("villages.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="received")
    reported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    village: Mapped["Village | None"] = relationship(back_populates="reports")

