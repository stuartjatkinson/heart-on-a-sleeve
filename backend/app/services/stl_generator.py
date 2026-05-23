"""
3-colour STL generator — produces three interlocking pieces per print:

  buildings.stl  (grey)   — all building pillars + road ribbons, solid from Z=0
  land.stl       (green)  — flat slab (or terrain surface) with cutouts where
                             buildings and water sit, so all three pieces slot together
  water.stl      (blue)   — water body fills, slightly below land level

Two modes:
  FLAT      (coaster, placemat) — no elevation; uniform building heights; plexi-flat surface
  TOPOLOGY  (3d_print)          — SRTM elevation fetched from OpenTopoData;
                                   terrain mesh; buildings placed at their ground elevation
"""

import math
import requests
import trimesh
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, box as shapely_box
from shapely.ops import unary_union
from shapely.validation import make_valid
from io import BytesIO


PLATE_MM: dict[str, tuple[float, float]] = {
    'tshirt':   (100.0, 133.0),
    'mug':      (150.0,  50.0),
    'placemat': (150.0, 107.0),
    'coaster':  ( 95.0,  95.0),
    'tote':     (100.0, 150.0),
    '3d_print': (100.0, 100.0),
}

TOPOLOGY_TYPES = {'3d_print'}

ROAD_WIDTH_MM: dict[str, float] = {
    'motorway': 2.5, 'trunk': 2.2, 'primary': 2.0, 'secondary': 1.6,
    'tertiary': 1.2, 'residential': 0.9, 'unclassified': 0.9, 'service': 0.6,
}
WATER_POLY_TAGS = {'water', 'reservoir', 'lake', 'pond', 'basin', 'lagoon'}
WATERWAY_WIDTH_MM = {'river': 4.0, 'canal': 3.0, 'stream': 1.5}


class STLGenerator:

    def generate(
        self,
        osm_data: dict,
        merch_type: str,
        height_mm: float = 6.0,
        base_thickness_mm: float = 2.0,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> dict[str, BytesIO]:
        """Returns {'buildings': BytesIO, 'land': BytesIO, 'water': BytesIO}."""
        west, south, east, north = bbox or (-0.13, 51.50, -0.11, 51.52)
        plate_w, plate_h = PLATE_MM.get(merch_type, (100.0, 100.0))
        lon_span = east - west
        lat_span = north - south

        def proj(lon: float, lat: float) -> tuple[float, float]:
            return ((lon - west) / lon_span * plate_w,
                    (lat - south) / lat_span * plate_h)

        def way_pts(way: dict) -> list[tuple[float, float]]:
            return [proj(*nodes[nid]) for nid in way.get('nodes', []) if nid in nodes]

        nodes: dict[int, tuple[float, float]] = {}
        ways: list[dict] = []
        for el in osm_data.get('elements', []):
            t = el.get('type')
            if t == 'node':
                nodes[el['id']] = (el.get('lon', 0.0), el.get('lat', 0.0))
            elif t == 'way':
                ways.append(el)

        if merch_type in TOPOLOGY_TYPES:
            elev_grid = _fetch_elevation(west, south, east, north)
        else:
            elev_grid = None

        return self._build_3color(
            ways, nodes, way_pts, proj,
            plate_w, plate_h, base_thickness_mm, height_mm,
            elev_grid, west, south, east, north,
        )

    # ── 3-colour build ─────────────────────────────────────────────────────────

    def _build_3color(
        self, ways, nodes, way_pts, proj,
        plate_w, plate_h, base_mm, height_mm,
        elev_grid, west, south, east, north,
    ) -> dict[str, BytesIO]:
        topology = elev_grid is not None

        LAND_H   = 3.0                  # land slab height above base
        BLDG_H   = height_mm            # building pillar height above base
        ROAD_H   = 0.5                  # road height above land surface
        WATER_H  = LAND_H - 0.8        # water slightly below land (creates visible recess)

        land_z  = base_mm
        bldg_z  = base_mm  # buildings start from the absolute base (pillars)
        water_z = base_mm

        # ── Collect geometry ─────────────────────────────────────────────────
        bldg_shapes:  list[Polygon] = []
        road_shapes:  list[tuple[Polygon, float]] = []  # (shape, road_height_above_land)
        water_shapes: list[Polygon] = []
        wway_shapes:  list[tuple[Polygon, float]] = []

        for way in ways:
            tags = way.get('tags', {})
            pts  = way_pts(way)

            if tags.get('building') not in (None, 'no') and len(pts) >= 3:
                try:
                    p = make_valid(Polygon(pts))
                    if not p.is_empty and p.area > 0.2:
                        bldg_shapes.append(p)
                except Exception:
                    pass
                continue

            hw = tags.get('highway')
            if hw in ROAD_WIDTH_MM and len(pts) >= 2:
                try:
                    from shapely.geometry import LineString
                    line = LineString(pts)
                    buf  = make_valid(line.buffer(ROAD_WIDTH_MM[hw] / 2, cap_style=2, join_style=2))
                    road_shapes.append((buf, ROAD_H))
                except Exception:
                    pass
                continue

            if (tags.get('natural') == 'water' or
                    tags.get('landuse') in WATER_POLY_TAGS) and len(pts) >= 3:
                try:
                    p = make_valid(Polygon(pts))
                    if not p.is_empty and p.area > 0.5:
                        water_shapes.append(p)
                except Exception:
                    pass
                continue

            ww = tags.get('waterway')
            if ww in WATERWAY_WIDTH_MM and len(pts) >= 2:
                try:
                    from shapely.geometry import LineString
                    line = LineString(pts)
                    buf  = make_valid(line.buffer(WATERWAY_WIDTH_MM[ww] / 2, cap_style=2))
                    wway_shapes.append((buf, 0))
                except Exception:
                    pass

        # Merge all water shapes
        all_water_polys = water_shapes + [s for s, _ in wway_shapes]
        water_union = unary_union(all_water_polys) if all_water_polys else Polygon()
        bldg_union  = unary_union(bldg_shapes)     if bldg_shapes     else Polygon()
        road_union  = unary_union([s for s, _ in road_shapes]) if road_shapes else Polygon()

        # ── Buildings piece ───────────────────────────────────────────────────
        bldg_meshes: list[trimesh.Trimesh] = []

        # Base plate (all 3 pieces share the same footprint base for alignment)
        bldg_meshes.append(_box_mesh(plate_w, plate_h, base_mm, [plate_w/2, plate_h/2, base_mm/2]))

        if topology and elev_grid is not None:
            # Buildings placed at their terrain elevation
            for way in ways:
                tags = way.get('tags', {})
                if tags.get('building') in (None, 'no'):
                    continue
                pts = way_pts(way)
                if len(pts) < 3:
                    continue
                # Estimate building ground elevation from centroid
                cx_b = sum(p[0] for p in pts) / len(pts)
                cy_b = sum(p[1] for p in pts) / len(pts)
                ground_elev = _interp_elevation(elev_grid, cx_b, cy_b, plate_w, plate_h)
                levels = float(tags.get('building:levels', 2))
                raw_h  = float(tags.get('building:height', levels * 3.2))
                extrude = min(max(raw_h / 40.0 * BLDG_H, 0.5), BLDG_H)
                m = _extrude_poly(pts, base_mm + ground_elev + extrude, base_mm)
                if m: bldg_meshes.append(m)
        else:
            # Flat: all buildings same height
            for way in ways:
                tags = way.get('tags', {})
                if tags.get('building') in (None, 'no'):
                    continue
                pts = way_pts(way)
                m = _extrude_poly(pts, BLDG_H, bldg_z)
                if m: bldg_meshes.append(m)

        # Roads (sit on top of land surface)
        for poly, rh in road_shapes + wway_shapes:
            polys = list(poly.geoms) if isinstance(poly, MultiPolygon) else [poly]
            for p in polys:
                p = make_valid(p)
                if p.is_empty:
                    continue
                pts = list(zip(*p.exterior.coords.xy))
                m = _extrude_poly(pts, ROAD_H, land_z + LAND_H)
                if m: bldg_meshes.append(m)

        # ── Land piece ────────────────────────────────────────────────────────
        land_meshes: list[trimesh.Trimesh] = []
        land_meshes.append(_box_mesh(plate_w, plate_h, base_mm, [plate_w/2, plate_h/2, base_mm/2]))

        full_rect = shapely_box(0, 0, plate_w, plate_h)
        cutouts   = bldg_union
        if not water_union.is_empty:
            cutouts = cutouts.union(water_union) if not cutouts.is_empty else water_union

        if topology and elev_grid is not None:
            # Terrain mesh (variable height)
            terrain = _build_terrain_mesh(elev_grid, plate_w, plate_h, base_mm, LAND_H)
            land_meshes.append(terrain)
        else:
            # Flat slab minus cutouts
            if cutouts.is_empty:
                land_piece = full_rect
            else:
                land_piece = make_valid(full_rect.difference(cutouts))

            for poly in (_geom_parts(land_piece)):
                pts = list(zip(*poly.exterior.coords.xy))
                holes = [list(zip(*i.coords.xy)) for i in poly.interiors]
                m = _extrude_poly_with_holes(pts, holes, LAND_H, land_z)
                if m: land_meshes.append(m)

        # ── Water piece ───────────────────────────────────────────────────────
        water_meshes: list[trimesh.Trimesh] = []
        water_meshes.append(_box_mesh(plate_w, plate_h, base_mm, [plate_w/2, plate_h/2, base_mm/2]))

        for poly in _geom_parts(water_union):
            pts = list(zip(*poly.exterior.coords.xy))
            m = _extrude_poly(pts, WATER_H, water_z)
            if m: water_meshes.append(m)

        return {
            'buildings': _export(bldg_meshes),
            'land':      _export(land_meshes),
            'water':     _export(water_meshes),
        }


# ── Geometry helpers ──────────────────────────────────────────────────────────

def _box_mesh(w: float, h: float, d: float, centre: list) -> trimesh.Trimesh:
    m = trimesh.creation.box([w, h, d])
    m.apply_translation(centre)
    return m

def _extrude_poly(pts, height, z_base) -> trimesh.Trimesh | None:
    if height <= 0 or len(pts) < 3:
        return None
    try:
        poly = make_valid(Polygon(pts))
        if poly.is_empty or poly.area < 0.1:
            return None
        m = trimesh.creation.extrude_polygon(poly, height)
        m.apply_translation([0, 0, z_base])
        return m
    except Exception:
        return None

def _extrude_poly_with_holes(outer_pts, holes, height, z_base) -> trimesh.Trimesh | None:
    if height <= 0 or len(outer_pts) < 3:
        return None
    try:
        outer = Polygon(outer_pts)
        for h in holes:
            if len(h) >= 3:
                try:
                    outer = outer.difference(Polygon(h))
                except Exception:
                    pass
        outer = make_valid(outer)
        if outer.is_empty or outer.area < 0.1:
            return None
        m = trimesh.creation.extrude_polygon(outer, height)
        m.apply_translation([0, 0, z_base])
        return m
    except Exception:
        return None

def _geom_parts(geom) -> list[Polygon]:
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, MultiPolygon):
        return [p for p in geom.geoms if not p.is_empty]
    if isinstance(geom, Polygon):
        return [geom]
    return []

def _export(meshes: list) -> BytesIO:
    meshes = [m for m in meshes if m is not None]
    if not meshes:
        mesh = trimesh.creation.box([10, 10, 1])
    elif len(meshes) == 1:
        mesh = meshes[0]
    else:
        try:
            mesh = trimesh.util.concatenate(meshes)
        except Exception:
            mesh = meshes[0]
    mesh.vertices[:, 2] -= mesh.bounds[0][2]
    out = BytesIO()
    mesh.export(out, file_type='stl')
    out.seek(0)
    return out


# ── Elevation (SRTM via OpenTopoData) ─────────────────────────────────────────

def _fetch_elevation(west, south, east, north, nx=10, ny=10) -> list[list[float]] | None:
    """Fetch SRTM90m elevation for a grid. Returns [ny][nx] or None on failure."""
    lons = [west  + (east  - west)  * i / (nx - 1) for i in range(nx)]
    lats = [south + (north - south) * j / (ny - 1) for j in range(ny)]
    points = [(lat, lon) for lat in lats for lon in lons]
    locs   = '|'.join(f'{lat:.5f},{lon:.5f}' for lat, lon in points)
    try:
        r = requests.get(
            f'https://api.opentopodata.org/v1/srtm90m?locations={locs}',
            timeout=20,
        )
        data = r.json()
        elevs = [res.get('elevation') or 0.0 for res in data.get('results', [])]
        if len(elevs) != nx * ny:
            return None
        mn, mx = min(elevs), max(elevs)
        rng = mx - mn or 1.0
        # Normalise to 0–1
        norm = [(e - mn) / rng for e in elevs]
        grid = [[norm[j * nx + i] for i in range(nx)] for j in range(ny)]
        return grid
    except Exception:
        return None

def _interp_elevation(grid: list[list[float]], x, y, plate_w, plate_h) -> float:
    """Bilinear interpolation of elevation grid at (x, y) in mm."""
    ny, nx = len(grid), len(grid[0])
    fx = min(max(x / plate_w * (nx - 1), 0), nx - 1)
    fy = min(max(y / plate_h * (ny - 1), 0), ny - 1)
    ix, iy = int(fx), int(fy)
    dx, dy = fx - ix, fy - iy
    ix1, iy1 = min(ix + 1, nx - 1), min(iy + 1, ny - 1)
    v = (grid[iy][ix]   * (1-dx) * (1-dy) +
         grid[iy][ix1]  *    dx  * (1-dy) +
         grid[iy1][ix]  * (1-dx) *    dy  +
         grid[iy1][ix1] *    dx  *    dy)
    return v  # 0–1 normalised

def _build_terrain_mesh(
    grid: list[list[float]], plate_w, plate_h, base_mm, max_terrain_mm,
) -> trimesh.Trimesh:
    """Build a solid terrain block from normalised elevation grid."""
    ny, nx = len(grid), len(grid[0])
    top_verts = []
    for j in range(ny):
        for i in range(nx):
            x = i / (nx - 1) * plate_w
            y = j / (ny - 1) * plate_h
            z = base_mm + grid[j][i] * max_terrain_mm
            top_verts.append([x, y, z])

    faces = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            v0, v1 = j*nx+i, j*nx+(i+1)
            v2, v3 = (j+1)*nx+i, (j+1)*nx+(i+1)
            faces += [[v0,v1,v2],[v1,v3,v2]]

    mesh = trimesh.Trimesh(vertices=np.array(top_verts, dtype=float), faces=np.array(faces))
    return mesh
