from datetime import datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    severity: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    affected_service: Mapped[str] = mapped_column(String(100))
    started_at: Mapped[datetime] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    trigger: Mapped[str | None] = mapped_column(String(50), nullable=True)
    observed_value: Mapped[float | None] = mapped_column(Float, nullable=True)


class Deployment(Base):
    __tablename__ = "deployments"

    id: Mapped[int] = mapped_column(primary_key=True)
    service: Mapped[str] = mapped_column(String(100), index=True)
    previous_version: Mapped[str] = mapped_column(String(50))
    version: Mapped[str] = mapped_column(String(50))
    configuration_change: Mapped[str] = mapped_column(String(500))
    deployed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
