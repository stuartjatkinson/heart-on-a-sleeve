from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BBox(BaseModel):
    north: float = Field(..., ge=-90, le=90)
    south: float = Field(..., ge=-90, le=90)
    east: float = Field(..., ge=-180, le=180)
    west: float = Field(..., ge=-180, le=180)


class MerchType(BaseModel):
    type: str = Field(..., pattern="^(placemat|coaster|tshirt|mug|tote|3d_print)$")
    aspect_ratio_x: int = Field(default=3)
    aspect_ratio_y: int = Field(default=4)


MERCH_SPECS = {
    "placemat": {"ratio_x": 14, "ratio_y": 10, "dpi": 300, "width_px": 4200, "height_px": 3000},
    "coaster": {"ratio_x": 1, "ratio_y": 1, "dpi": 300, "width_px": 1000, "height_px": 1000},
    "tshirt": {"ratio_x": 3, "ratio_y": 4, "dpi": 300, "width_px": 3000, "height_px": 4000},
    "mug": {"ratio_x": 9, "ratio_y": 3, "dpi": 300, "width_px": 2700, "height_px": 900},
    "tote": {"ratio_x": 2, "ratio_y": 3, "dpi": 300, "width_px": 2000, "height_px": 3000},
    "3d_print": {"ratio_x": 1, "ratio_y": 1, "dpi": 150, "width_px": 800, "height_px": 800},
}


class DesignProjectCreate(BaseModel):
    name: str
    bbox: BBox
    merch_type: str = Field(..., pattern="^(placemat|coaster|tshirt|mug|tote|3d_print)$")


class DesignProjectResponse(BaseModel):
    id: int
    name: str
    bbox: BBox
    merch_type: str
    status: str
    svg_url: Optional[str] = None
    stl_url: Optional[str] = None
    license_info: dict
    created_at: datetime


class SVGGenerationRequest(BaseModel):
    bbox: BBox
    merch_type: str
    style: str = "osm_default"
    include_labels: bool = True
    include_buildings: bool = True
    include_roads: bool = True
    include_parks: bool = True


class STLGenerationRequest(BaseModel):
    bbox: BBox
    merch_type: str = "3d_print"
    # Layer heights (mm) — all tunable from the viewer
    bldg_height: float = 4.0       # buildings + roads: 0 → bldg_height
    water_start: float = 1.0       # water layer bottom
    water_end:   float = 2.0       # water layer top  (sea level)
    land_start:  float = 2.0       # land layer bottom
    land_end:    float = 3.0       # land layer top
    # Geometry processing
    gap_close_mm:    float = 0.8   # merge buildings with gap < this
    water_expand_mm: float = 0.5   # expand water bodies by this amount
    min_bldg_mm:     float = 1.0   # minimum building height
    collar_mm:       float = 1.0   # outer collar width on base + lid
    # Legacy (ignored — kept for backward compat with old callers)
    height_mm: float = 4.0
    base_thickness_mm: float = 2.0


class LicenseCheckRequest(BaseModel):
    bbox: BBox
    data_sources: list[str]  # e.g. ["osm", "nasa_srtm", "custom_upload"]