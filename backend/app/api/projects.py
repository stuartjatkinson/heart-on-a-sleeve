from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.models.db_models import DesignProject, User
from app.api.auth import get_current_user

router = APIRouter(prefix="/api/projects", tags=["projects"])


class SaveProjectRequest(BaseModel):
    name: str
    merch_type: str
    bbox_west: float
    bbox_south: float
    bbox_east: float
    bbox_north: float
    style: str = "osm_default"
    coaster_shape: str | None = None
    palette_overrides: dict | None = None
    include_labels: bool = True
    include_buildings: bool = True
    svg_url: str | None = None
    stl_buildings_url: str | None = None
    stl_land_url: str | None = None
    stl_water_url: str | None = None


@router.get("")
async def list_projects(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DesignProject)
        .where(DesignProject.user_id == user.id)
        .order_by(DesignProject.created_at.desc())
    )
    return [
        {
            "id": p.id,
            "name": p.name,
            "merch_type": p.merch_type,
            "bbox": {"west": p.bbox_west, "south": p.bbox_south, "east": p.bbox_east, "north": p.bbox_north},
            "svg_url": p.svg_url,
            "stl_buildings_url": p.stl_buildings_url,
            "stl_land_url": p.stl_land_url,
            "stl_water_url": p.stl_water_url,
            "created_at": p.created_at.isoformat(),
        }
        for p in result.scalars().all()
    ]


@router.post("", status_code=201)
async def save_project(
    req: SaveProjectRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = DesignProject(
        user_id=user.id,
        name=req.name,
        merch_type=req.merch_type,
        bbox_west=req.bbox_west,
        bbox_south=req.bbox_south,
        bbox_east=req.bbox_east,
        bbox_north=req.bbox_north,
        style=req.style,
        coaster_shape=req.coaster_shape,
        palette_overrides=req.palette_overrides,
        include_labels=req.include_labels,
        include_buildings=req.include_buildings,
        svg_url=req.svg_url,
        stl_buildings_url=req.stl_buildings_url,
        stl_land_url=req.stl_land_url,
        stl_water_url=req.stl_water_url,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return {"id": project.id, "name": project.name, "created_at": project.created_at.isoformat()}


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DesignProject).where(DesignProject.id == project_id, DesignProject.user_id == user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
    await db.commit()
