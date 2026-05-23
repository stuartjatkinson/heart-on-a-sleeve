from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from geoalchemy2 import Geometry
from .config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class DesignProject(Base):
    __tablename__ = "design_projects"
    id: int
    name: str
    bbox_north: float
    bbox_south: float
    bbox_east: float
    bbox_west: float
    merch_type: str  # placemat, coaster, tshirt, mug, tote
    aspect_ratio_x: int
    aspect_ratio_y: int
    status: str  # draft, generating, ready, submitted
    svg_path: str | None
    stl_path: str | None
    license_data: dict
    woocommerce_product_id: str | None
    created_at: datetime
    updated_at: datetime