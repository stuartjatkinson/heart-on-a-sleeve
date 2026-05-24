from datetime import datetime
from sqlalchemy import String, Float, Boolean, JSON, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    projects: Mapped[list["DesignProject"]] = relationship(back_populates="user", lazy="select")


class DesignProject(Base):
    __tablename__ = "design_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    merch_type: Mapped[str] = mapped_column(String(50))
    bbox_west: Mapped[float] = mapped_column(Float)
    bbox_south: Mapped[float] = mapped_column(Float)
    bbox_east: Mapped[float] = mapped_column(Float)
    bbox_north: Mapped[float] = mapped_column(Float)
    style: Mapped[str] = mapped_column(String(50), server_default="osm_default")
    coaster_shape: Mapped[str | None] = mapped_column(String(50), nullable=True)
    palette_overrides: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    include_labels: Mapped[bool] = mapped_column(Boolean, server_default="true")
    include_buildings: Mapped[bool] = mapped_column(Boolean, server_default="true")
    svg_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    stl_buildings_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    stl_land_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    stl_water_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    user: Mapped["User | None"] = relationship(back_populates="projects")
