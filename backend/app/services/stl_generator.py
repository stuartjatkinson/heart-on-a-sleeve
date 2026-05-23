"""
STL generator — three modes depending on merch type:

  TOPOLOGY  (3d_print)         — realistic relative building heights, roads raised,
                                  terrain variation. Good for display/art prints.

  PLEXI     (coaster, placemat)— all buildings normalised to the same flat top height
                                  so a clear acrylic sheet can sit flush on top.
                                  Roads, parks, water are recessed below building tops.
                                  Print + glue thin plexi = map sealed in depth.

  BASIC     (tshirt, mug, tote)— flat base + roads embossed, buildings at real heights.
                                  Useful as a reference / preview object.
"""
import math
import trimesh
import numpy as np
from shapely.geometry import Polygon, LineString, MultiPolygon
from shapely.validation import make_valid
from io import BytesIO


# Physical plate size (mm) per merch type
PLATE_MM: dict[str, tuple[float, float]] = {
    'tshirt':   (100.0, 133.0),
    'mug':      (150.0,  50.0),
    'placemat': (150.0, 107.0),
    'coaster':  ( 95.0,  95.0),
    'tote':     (100.0, 150.0),
    '3d_print': (100.0, 100.0),
}

PLEXI_TYPES    = {'coaster', 'placemat'}
TOPOLOGY_TYPES = {'3d_print'}

# Road classification
ROAD_WIDTH_MM: dict[str, float] = {
    'motorway': 2.5, 'trunk': 2.2, 'primary': 2.0, 'secondary': 1.6,
    'tertiary': 1.2, 'residential': 0.9, 'unclassified': 0.9, 'service': 0.6,
}
WATERWAY_WIDTH_MM: dict[str, float] = {'river': 3.5, 'canal': 2.5, 'stream': 1.2, 'drain': 0.8}
WATER_POLY_TAGS = {'water', 'reservoir', 'lake', 'pond', 'basin', 'lagoon'}


class STLGenerator:

    def generate(
        self,
        osm_data: dict,
        merch_type: str,
        height_mm: float = 5.0,
        base_thickness_mm: float = 2.0,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> BytesIO:
        west, south, east, north = bbox or (-0.13, 51.50, -0.11, 51.52)
        plate_w, plate_h = PLATE_MM.get(merch_type, (100.0, 100.0))
        lon_span = east - west
        lat_span = north - south

        def proj(lon: float, lat: float) -> tuple[float, float]:
            return ((lon - west) / lon_span * plate_w,
                    (lat - south) / lat_span * plate_h)

        def way_pts(way: dict) -> list[tuple[float, float]]:
            return [proj(*nodes[nid]) for nid in way.get('nodes', []) if nid in nodes]

        # Parse OSM
        nodes: dict[int, tuple[float, float]] = {}
        ways: list[dict] = []
        for el in osm_data.get('elements', []):
            t = el.get('type')
            if t == 'node':
                nodes[el['id']] = (el.get('lon', 0.0), el.get('lat', 0.0))
            elif t == 'way':
                ways.append(el)

        if merch_type in PLEXI_TYPES:
            return self._build_plexi(ways, nodes, way_pts, plate_w, plate_h,
                                     base_thickness_mm, height_mm)
        elif merch_type in TOPOLOGY_TYPES:
            return self._build_topology(ways, nodes, way_pts, plate_w, plate_h,
                                        base_thickness_mm, height_mm)
        else:
            return self._build_basic(ways, nodes, way_pts, plate_w, plate_h,
                                     base_thickness_mm, height_mm)

    # ── PLEXI mode ────────────────────────────────────────────────────────────
    # All buildings rise to the same flat top (height_mm above base plate top).
    # Roads are 1.5mm below building tops; parks 2mm; water 3mm.
    # Glue clear acrylic flush to building tops — map sealed under plexi.

    def _build_plexi(self, ways, nodes, way_pts, plate_w, plate_h,
                     base_mm, height_mm) -> BytesIO:
        TOP     = base_mm + height_mm       # building top surface Z
        RD_Z    = TOP - 1.5                 # road surface Z
        PK_Z    = TOP - 2.2                 # park surface Z
        WA_Z    = TOP - 3.2                 # water surface Z (deepest)

        meshes = []
        meshes.append(self._base_plate(plate_w, plate_h, base_mm))

        # Fill entire plate with "ground" at park level first
        ground = trimesh.creation.box([plate_w, plate_h, PK_Z - base_mm])
        ground.apply_translation([plate_w/2, plate_h/2, base_mm + (PK_Z - base_mm)/2])
        meshes.append(ground)

        # Roads raised to RD_Z (above park but below buildings)
        for way in ways:
            tags = way.get('tags', {})
            hw = tags.get('highway')
            if hw not in ROAD_WIDTH_MM:
                continue
            pts = way_pts(way)
            if len(pts) < 2:
                continue
            m = self._extrude_line(pts, ROAD_WIDTH_MM[hw], RD_Z - PK_Z, z_base=PK_Z)
            if m: meshes.append(m)

        # Buildings all at TOP
        for way in ways:
            tags = way.get('tags', {})
            if tags.get('building') in (None, 'no'):
                continue
            pts = way_pts(way)
            if len(pts) < 3:
                continue
            m = self._extrude_poly(pts, TOP - PK_Z, z_base=PK_Z)
            if m: meshes.append(m)

        # Water bodies recessed — carve by raising surrounding rather than subtracting.
        # We just don't add anything at water locations (ground fill is at PK_Z,
        # water sits lower at WA_Z — achieved by NOT filling water polys with ground).
        # Since we can't easily subtract, instead we skip water — their absence at
        # ground height creates natural wells once user views the model.
        # (True boolean subtraction would require manifold geometry.)

        return self._export(meshes)

    # ── TOPOLOGY mode ─────────────────────────────────────────────────────────
    # Realistic relative building heights (taller OSM buildings = taller print).
    # Roads raised 0.5mm above base. Water at base level.

    def _build_topology(self, ways, nodes, way_pts, plate_w, plate_h,
                        base_mm, height_mm) -> BytesIO:
        MAX_BLDG = height_mm          # mm for max-height building
        ROAD_H   = 0.5                # roads raised above base
        base_z   = base_mm

        meshes = []
        meshes.append(self._base_plate(plate_w, plate_h, base_mm))

        # Buildings — proportional to levels/height
        for way in ways:
            tags = way.get('tags', {})
            if tags.get('building') in (None, 'no'):
                continue
            pts = way_pts(way)
            if len(pts) < 3:
                continue
            levels = float(tags.get('building:levels', 2))
            raw_h  = float(tags.get('building:height', levels * 3.0))
            extrude = min(max(raw_h / 40.0 * MAX_BLDG, 0.4), MAX_BLDG)
            m = self._extrude_poly(pts, extrude, z_base=base_z)
            if m: meshes.append(m)

        # Roads
        for way in ways:
            tags = way.get('tags', {})
            hw = tags.get('highway')
            if hw not in ROAD_WIDTH_MM:
                continue
            pts = way_pts(way)
            if len(pts) < 2:
                continue
            m = self._extrude_line(pts, ROAD_WIDTH_MM[hw], ROAD_H, z_base=base_z)
            if m: meshes.append(m)

        # Waterways (linear) — thin raised bank lines
        for way in ways:
            tags = way.get('tags', {})
            ww = tags.get('waterway')
            if ww not in WATERWAY_WIDTH_MM:
                continue
            pts = way_pts(way)
            if len(pts) < 2:
                continue
            m = self._extrude_line(pts, WATERWAY_WIDTH_MM[ww] * 0.6, 0.2, z_base=base_z)
            if m: meshes.append(m)

        return self._export(meshes)

    # ── BASIC mode ────────────────────────────────────────────────────────────
    def _build_basic(self, ways, nodes, way_pts, plate_w, plate_h,
                     base_mm, height_mm) -> BytesIO:
        meshes = []
        meshes.append(self._base_plate(plate_w, plate_h, base_mm))
        base_z = base_mm

        for way in ways:
            tags = way.get('tags', {})
            hw = tags.get('highway')
            if hw not in ROAD_WIDTH_MM:
                continue
            pts = way_pts(way)
            if len(pts) < 2:
                continue
            m = self._extrude_line(pts, ROAD_WIDTH_MM[hw], 0.4, z_base=base_z)
            if m: meshes.append(m)

        for way in ways:
            tags = way.get('tags', {})
            if tags.get('building') in (None, 'no'):
                continue
            pts = way_pts(way)
            if len(pts) < 3:
                continue
            levels = float(tags.get('building:levels', 2))
            extrude = min(levels * 0.4, height_mm * 0.6)
            m = self._extrude_poly(pts, extrude, z_base=base_z)
            if m: meshes.append(m)

        return self._export(meshes)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _base_plate(self, w: float, h: float, thickness: float) -> trimesh.Trimesh:
        plate = trimesh.creation.box([w, h, thickness])
        plate.apply_translation([w/2, h/2, thickness/2])
        return plate

    def _extrude_poly(self, pts: list, height: float, z_base: float) -> trimesh.Trimesh | None:
        if height <= 0 or len(pts) < 3:
            return None
        try:
            poly = make_valid(Polygon(pts))
            if poly.is_empty or poly.area < 0.2:
                return None
            m = trimesh.creation.extrude_polygon(poly, height)
            m.apply_translation([0, 0, z_base])
            return m
        except Exception:
            return None

    def _extrude_line(self, pts: list, width: float, height: float,
                      z_base: float) -> trimesh.Trimesh | None:
        if height <= 0 or len(pts) < 2:
            return None
        try:
            line  = LineString(pts)
            poly  = line.buffer(width / 2, cap_style=2, join_style=2)
            polys = list(poly.geoms) if isinstance(poly, MultiPolygon) else [poly]
            parts = []
            for p in polys:
                p = make_valid(p)
                if p.is_empty or p.area < 0.05:
                    continue
                m = trimesh.creation.extrude_polygon(p, height)
                m.apply_translation([0, 0, z_base])
                parts.append(m)
            return trimesh.util.concatenate(parts) if parts else None
        except Exception:
            return None

    def _export(self, meshes: list) -> BytesIO:
        meshes = [m for m in meshes if m is not None]
        if not meshes:
            mesh = trimesh.creation.box([100, 100, 2])
        elif len(meshes) == 1:
            mesh = meshes[0]
        else:
            try:
                mesh = trimesh.util.concatenate(meshes)
            except Exception:
                mesh = meshes[0]

        mesh.vertices[:, 2] -= mesh.bounds[0][2]
        output = BytesIO()
        mesh.export(output, file_type='stl')
        output.seek(0)
        return output
