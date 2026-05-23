# Heart on a Sleeve — Build Roadmap

## Overview
A platform where users select a location on a stylised OSM map, choose a merch product (placemat, coaster, t-shirt, mug, tote, 3D print), and the system generates print-ready SVG or STL files — with live 2D and 3D preview, handling licences, WooCommerce product creation, and POD fulfillment automatically.

---

## Phase 1 — Core Backend ✅ Done

- [x] FastAPI app with uvicorn, all imports clean
- [x] `__init__.py` in all subpackages
- [x] Pydantic v2 schemas — `BBox`, `SVGGenerationRequest`, `STLGenerationRequest`, `LicenseCheckRequest`, `MERCH_SPECS`
- [x] CORS configured for `localhost:5173`
- [x] `POST /api/generate/svg` — fetches OSM, renders SVG, saves to `/output/svg_output/`
- [x] `POST /api/generate/stl` — fetches OSM, generates STL, saves to `/output/stl_output/`
- [x] `POST /api/license/check` — returns ODbL attribution
- [x] `GET /health`
- [x] StaticFiles mount serving generated outputs at `/output`
- [x] Async Overpass client (`httpx`) with correct `User-Agent` header (overpass-api.de requires non-default UA)
- [ ] Postgres/PostGIS — project storage, caching, user records *(deferred — running file-based for now)*
- [ ] Alembic migrations
- [ ] Rate limiting on Overpass calls

---

## Phase 2 — SVG Generation ✅ Done

- [x] Real OSM vector data → print-ready SVG via `svgwrite`
- [x] Three style presets: `osm_default`, `minimalist`, `vibrant`
- [x] Draw order: landuse → water → buildings → roads → railways → labels
- [x] Landuse groups: agriculture, parks/managed green, residential/civic, industrial
- [x] Water: polygon fills (lakes, reservoirs) + line widths (rivers, canals, streams)
- [x] Roads: two tiers (main/other), no casings, width by road class
- [x] Buildings: footprint polygons, toggleable
- [x] Railways: black lines in minimalist + vibrant
- [x] Place labels: city/town/village/suburb/neighbourhood from OSM `place=*` nodes, sized by hierarchy
- [x] ODbL attribution embedded in SVG
- [x] `include_buildings` and `include_labels` toggles
- [x] Correct Y-axis projection (lat increases N, SVG y increases down)
- [x] Bbox passed from request (not derived from node spread)
- [x] Merch-spec dimensions used (not hardcoded to tshirt)
- [ ] Proper coordinate projection (pyproj EPSG:27700 for UK)
- [ ] Bleed margins
- [ ] Mug wrap perspective
- [ ] SVG validation

---

## Phase 3 — STL / 3D Generation ✅ Done (v1)

- [x] Three generation modes by merch type:
  - **Topology** (`3d_print`): buildings at real OSM heights, roads raised 0.5 mm
  - **Plexi-flat** (coaster, placemat): all buildings normalised to same flat top height — designed for clear acrylic overlay
  - **Basic** (fabrics): flat base + roads + gentle building extrusions
- [x] Physical plate sizes per merch type
- [x] Building heights from `building:levels` and `building:height` OSM tags
- [x] Road ribbons (shapely buffer + trimesh extrude)
- [x] Waterway outlines
- [x] shapely `make_valid` for degenerate polygons
- [ ] SRTM terrain elevation
- [ ] Watertightness check
- [ ] Hollowing for large prints

---

## Phase 4 — Licence Tracker ✅ Done (v1)

- [x] ODbL attribution returned on every generate request
- [x] Attribution embedded in SVG `<text>` element
- [ ] SVG `<metadata>` block with CC namespace
- [ ] PDF licence report export
- [ ] User-uploaded asset licence detection

---

## Phase 5 — CesiumJS Frontend ✅ Done

- [x] CesiumJS 1.141 with OSM tiles — no Ion token required
- [x] Left-drag bbox drawing — aspect-ratio locked to merch type
- [x] Move handle (drag inside shape)
- [x] Corner resize handles (inner zone, maintains ratio)
- [x] Corner rotate handles (outer ring, billboard entities with arc-arrow icon)
- [x] Rotation in geographic space (correct cos(lat) scaling)
- [x] Globe rotation disabled during draw/drag; scroll-zoom and middle-tilt always on
- [x] Merch panel split: Fabrics & Transfers / 3D Prints (3-column grid)
- [x] Style selector: OSM Default / Minimalist / Vibrant
- [x] Include toggles: Place labels, Buildings
- [x] Generate button with elapsed timer and 90 s abort
- [x] Post-generate: View SVG + View 3D buttons (both always shown)
- [x] Camera pitch constraints (20°–90° from horizon)
- [x] Initial view: England centred
- [x] Merch type change re-fits existing bbox (centre-preserved, ratio-adjusted)
- [ ] Preset location dropdown
- [ ] Scale bar
- [ ] Geolocation ("centre on me")
- [ ] EPSG:27700 coordinate display

---

## Phase 5b — SVG Viewer ✅ Done

- [x] `/svg-viewer.html` — standalone pan/zoom SVG viewer
- [x] Fetches SVG as text, parses `viewBox` for reliable dimensions
- [x] Scroll to zoom (towards cursor), left-drag to pan
- [x] Fit-to-window (with margin) and Actual Size buttons
- [x] Download link
- [x] Dark background, matches app aesthetic

---

## Phase 5c — 3D Map Viewer ✅ Done

- [x] `/3d-viewer.html` — live Three.js OSM renderer (no STL required for preview)
- [x] Fetches OSM directly from Overpass for selected bbox
- [x] Buildings: `ExtrudeGeometry` from OSM footprints + real heights
- [x] Three building height tiers (lo/mid/hi) with distinct shading
- [x] Roads: hand-built ribbon geometry, width by road class
- [x] Parks + water: flat coloured polygons
- [x] Solid colours follow selected 2D style scheme (osm_default / minimalist / vibrant)
- [x] Wireframe colours fixed per feature type: parks=green, water=blue, roads=orange/yellow, buildings=cyan/purple/white
- [x] Black background in wireframe mode, scheme background in solid mode
- [x] Grid: light blue solid / bright blue wireframe
- [x] ACESFilmic tone mapping, directional sun + hemisphere + ambient lights, soft shadows
- [x] OrbitControls — no auto-rotate by default
- [x] Load progress bar (fetch → parse → render)
- [x] Building + road count in overlay
- [x] STL download link (from generated file)
- [ ] Terrain elevation (SRTM)
- [ ] Roof shapes
- [ ] Street-level textures

---

## Phase 6 — SVG Editor App 📋 Planned

- [ ] Load generated SVG into an editable panel
- [ ] Layer toggles per OSM category
- [ ] Per-layer colour picker and opacity slider
- [ ] Road width slider, label size slider, saturation slider
- [ ] "Reset to style preset" button
- [ ] Re-render at 300 DPI and download

---

## Phase 7 — WooCommerce Integration 📋 Planned

- [ ] WooCommerce REST API client
- [ ] Create product from design project (SVG as product image)
- [ ] Price calculation: base cost + configurable markup
- [ ] Order submission to POD provider
- [ ] Webhook handlers: order paid → trigger POD, shipment → notify user

---

## Phase 8 — POD Providers (Prodigi + Printful) 📋 Planned

- [ ] Prodigi API: POST /orders, GET /orders/{id}, upload print file
- [ ] Printful API: fallback/DTG coverage
- [ ] Map merch types to provider product IDs
- [ ] Fulfillment webhook → update order status in DB

---

## Phase 9 — User Auth & Dashboard 📋 Planned

- [ ] JWT auth (fastapi-users or custom)
- [ ] Save/reload design projects
- [ ] Order history
- [ ] Re-order past designs
- [ ] Share design (public view-only link)

---

## Phase 10 — Deployment 📋 Planned

- [ ] `backend/Dockerfile` (Python 3.14, multi-stage)
- [ ] `frontend/Dockerfile` (Nginx + API proxy)
- [ ] `docker-compose.prod.yml` with Traefik labels
- [ ] Routing: `heart.stuartjatkinson.co.uk` → frontend, `/api/*` → backend
- [ ] TLS via Cloudflare
- [ ] Uptime Kuma monitors
- [ ] Structured JSON logging
- [ ] GitHub Actions: lint → test → build → push → deploy

---

## Priority order

| Phase | Priority | Status |
|---|---|---|
| 1. Core Backend | P0 | ✅ Done |
| 2. SVG Generation | P0 | ✅ Done |
| 3. STL Generation | P0 | ✅ Done (v1) |
| 4. Licence Tracker | P1 | ✅ Done (v1) |
| 5. CesiumJS Frontend | P0 | ✅ Done |
| 5b. SVG Viewer | P0 | ✅ Done |
| 5c. 3D Map Viewer | P0 | ✅ Done |
| 6. SVG Editor | P1 | 📋 Planned |
| 7. WooCommerce | P1 | 📋 Planned |
| 8. POD Providers | P1 | 📋 Planned |
| 9. Auth + Dashboard | P2 | 📋 Planned |
| 10. Deployment | P1 | 📋 Planned |
