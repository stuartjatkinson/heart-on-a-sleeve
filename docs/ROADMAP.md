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
- [x] `POST /api/generate/stl` — fetches OSM, generates 3 STL parts, saves to `/output/stl_output/`
- [x] `POST /api/license/check` — returns ODbL attribution
- [x] `GET /api/osm/features` — Overpass proxy for 3D viewer (avoids browser CORS + User-Agent issues)
- [x] `GET /health`
- [x] StaticFiles mount serving generated outputs at `/output`
- [x] Async Overpass client (`httpx`) with `User-Agent: heart-on-a-sleeve/1.0` (required by overpass-api.de)
- [x] CPU-bound generators (SVG + STL) run in thread pool executor — event loop stays responsive
- [ ] Postgres/PostGIS — project storage, caching, user records *(deferred)*
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
- [x] Place labels: city/town/village/suburb/neighbourhood from OSM `place=*` nodes
- [x] ODbL attribution embedded in SVG
- [x] `include_buildings` and `include_labels` toggles
- [x] **cosLat projection** — east-west features scale correctly (no ~1.7× stretch at UK latitudes)
- [x] **Edge clipping** — `<clipPath>` cuts roads/buildings at the canvas boundary
- [x] Bbox passed from request (not derived from node spread)
- [ ] Proper coordinate projection (pyproj EPSG:27700 for UK)
- [ ] Bleed margins
- [ ] Mug wrap perspective
- [ ] SVG validation

---

## Phase 3 — STL / 3D Generation ✅ Done (v2)

Three interlocking pieces per print:

- [x] **buildings.stl** (grey) — building pillars + road ribbons, Z=0→bldg_h
  - Flat mode: extrudes fully merged `urban_union` (terrace rows → single block)
  - Topology mode: individual buildings at proportional heights from OSM tags
  - Outer collar walls (collar_mm wide) frame the assembly
  - Polygon simplification (Douglas-Peucker) + gap closing (dilate→union→erode)
- [x] **water.stl** (blue) — water bodies + buffered waterways, Z=water_start→water_end
  - Building/road shapes punched out (pillars slot through)
  - Water bodies expanded by `water_expand_mm` (printable minimum width)
- [x] **land.stl** (green, locking lid) — Z=land_start→land_end
  - Same outer footprint as grey base (collar_mm on all sides)
  - Building holes so protrusions pierce through and clamp the stack
  - Flat for coaster/placemat; SRTM terrain mesh for topology/relief mode
- [x] All 8 parameters exposed in API and live viewer panel:
  `bldg_height`, `water_start`, `water_end`, `land_start`, `land_end`, `gap_close_mm`, `water_expand_mm`, `min_bldg_mm`, `collar_mm`
- [x] SRTM elevation via OpenTopoData (topology mode, 10×10 grid)
- [x] shapely `make_valid` for degenerate polygons
- [x] mapbox-earcut installed for trimesh triangulation
- [ ] Watertight mesh validation
- [ ] Hollowing for large prints
- [ ] Terrain side walls (fully closed solid)

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
- [x] Left-drag bbox drawing — aspect-ratio locked with cos(lat) correction
- [x] Move handle (drag inside shape)
- [x] Corner resize handles (inner zone, maintains ratio)
- [x] Corner rotate handles (outer billboard ring with arc-arrow icon)
- [x] Rotation in geographic space (correct cos(lat) scaling)
- [x] Globe controls: rotate=disabled during draw, scroll-zoom + middle-tilt always on
- [x] Merch panel split: Fabrics & Transfers (3 col) / 3D Prints (3 col)
- [x] **Auto-draw on merch click** — clicking any product type immediately enters draw mode (no separate Draw button); re-clicking the active type redraws; clicking a different type while editing just re-ratios the existing selection
- [x] **Circle + hexagon coaster shapes** — globe polygon renders as circle (64-pt) or hexagon when those coaster shapes are active; all hit-tests and screen AABB use the correct shape
- [x] **Generate transition** — pixelation phases → fake-asymptotic progress bar (tau from bbox-area estimate) → zoom to SVG-viewer fit bounds → pixel-to-SVG cross-dissolve
- [x] Camera pitch constraints (20°–90° from horizon)
- [x] **Fabric/transfer types** — "View 3D →" hidden; "↓ Download SVG" highlighted as primary action
- [ ] Preset location dropdown
- [ ] Scale bar
- [ ] Geolocation
- [ ] EPSG:27700 coordinate display
- [ ] **SSE streaming progress** from SVG/STL generators so transition bar tracks real server progress *(deferred — requires backend chunked-response endpoint)*

---

## Phase 5b — SVG Viewer ✅ Done

- [x] `/svg-viewer.html` — standalone pan/zoom viewer
- [x] Fetches SVG as text, parses `viewBox` for reliable dimensions (img.naturalWidth = 0 for SVGs)
- [x] Scroll to zoom (towards cursor), left-drag to pan
- [x] Fit-to-window (with margin) and Actual Size buttons
- [x] Download link, dark background

---

## Phase 5c — 3D Map Viewer ✅ Done

- [x] `/3d-viewer.html` — live Three.js OSM renderer
- [x] Fetches OSM via `/api/osm/features` backend proxy (no browser CORS issues)
- [x] 60 s AbortController timeout with clear error message
- [x] Buildings: `ExtrudeGeometry` from OSM footprints + real heights (3 tiers)
- [x] Roads: hand-built ribbon geometry, width by road class
- [x] Parks + water: flat coloured polygons
- [x] Mouse controls match Cesium (left=orbit, right=zoom, middle=pan)
- [x] **Solid colours**: fixed print-material scheme (grey/blue/green) — not scheme-dependent
- [x] **Wireframe**: per-type neon colours — parks=green, water=blue, roads=orange/yellow, buildings=cyan/purple/white; black background
- [x] Grid: light blue solid / bright blue wireframe
- [x] **Floating progress bar** — render loop starts before OSM fetch; `#loading` is a translucent bottom bar; pre-load fake-asymptotic fill (0→50%, tau from bbox area); 3 s minimum pre-load; post-load 5 s wireframe entry drives bar 50→100%; bar hides when animation completes
- [x] **Print Preview** — loads all 3 STL parts in correct print colours, spatially aligned
- [x] **⟳ Regenerate STL** panel — 9 tunable parameters, calls API, updates downloads + Print Preview in-place
- [x] STL download links for all 3 parts
- [x] **Fabric Preview** — SVG as `TextureLoader` ground plane + buildings-only OSM; hides roads/water/parks (SVG covers them)
- [x] **Layered print animation** — buildings wireframe fade-in → solid fill; water plate descends from above; land lid descends from above; ease-out cubic on descent phases
- [ ] Terrain elevation in live render (SRTM)
- [ ] Roof shapes
- [ ] Street-level textures

---

## Phase 5d — Design System ✅ Done

- [x] `public/app.css` — single CSS file shared by all three pages
- [x] 24 CSS custom properties (`--bg-*`, `--border-*`, `--text-*`, `--accent-*`, `--toggle-*`, `--radius-*`)
- [x] Shared components: `.panel`, `.btn`, `.btn-primary`, `.divider`, `.section-label`, `.dl-label`, `.param-row`, `.toggle-row`, `.toggle`, `#loading`, `.hint`, `.spinner`
- [x] Page-specific styles reduced to layout + unique components only

---

## Phase 5e — Client-side SVG Renderer ✅ Done

Moved SVG generation from the Python backend to the browser for Cloud Run scalability:

- [x] `frontend/cesium/src/svg-renderer.ts` — full TypeScript port of Python `svg_generator.py`
  - All three style presets (osm_default, minimalist, vibrant) with identical colour palettes
  - cosLat projection exactly matching backend formula
  - Same draw order: landuse → water → buildings → roads → railways → labels → attribution
  - Clip-path support (square/circle/hexagon for coasters)
- [x] `generate()` in `app.ts` — fetches `/api/osm/features` then calls `renderSvg()` client-side; no `/api/generate/svg` call
- [x] `svgRegen()` — uses cached OSM data (`_cachedOsmData`), re-renders with new palette/toggles at ~0 ms (no API call)
- [x] `POST /api/save-svg` — backend endpoint to persist client-rendered SVG text to `/output/svg_output/` for dashboard thumbnails
- [x] `saveProject()` — POSTs SVG text to `/api/save-svg` before saving project (blob: URL → stable /output/ URL)
- [x] Backend `/api/generate/svg` still available for server-side use (PDF export, server batch)

**Why:** Python GIL limits SVG parallelism to ~2 concurrent generations per Cloud Run instance. With client-side rendering, the backend only handles I/O-bound Overpass proxy calls — zero CPU per generation, trivially scales to hundreds of concurrent users.

---

## Phase 6 — SVG Editor App ✅ Done

- [x] Load generated SVG into an editable panel (pan/zoom viewport + side panel)
- [x] Layer toggles — Buildings + Place Labels (intentionally scoped; roads/parks always included)
- [x] Per-layer colour picker — 6 categories × 6 swatches, live regeneration
- [x] Re-render at 300 DPI — all merch types auto-generate at print resolution (300 DPI)
- [x] Download SVG button

---

## Phase 7 — WooCommerce Integration 📋 Planned

- [ ] WooCommerce REST API client
- [ ] Create product from design project
- [ ] Price calculation: base cost + configurable markup
- [ ] Order submission to POD provider
- [ ] Webhook handlers

---

## Phase 8 — POD Providers 📋 Planned

- [ ] Prodigi API: POST /orders, upload print file
- [ ] Printful API: fallback/DTG coverage
- [ ] Fulfillment webhook → update order status

---

## Phase 9 — User Auth & Dashboard ✅ Done

- [x] JWT auth — register + login endpoints, bcrypt passwords, access/refresh tokens (30 min / 7 day)
- [x] Save design projects — POST /api/projects stores bbox, merch type, SVG/STL URLs, palette, toggles
- [x] List + delete saved projects — GET/DELETE /api/projects with user ownership check
- [x] Login/register page — `/login.html` with tab toggle, localStorage token storage
- [x] Dashboard — `/dashboard.html` grid of saved projects with thumbnail, open + delete
- [x] Save button in SVG viewer (both inline and standalone) — prompts login if unauthenticated
- [x] User nav (Login / My Designs / Logout) in all SVG panels
- [ ] Order history + re-order *(deferred to Phase 7/8)*
- [ ] Share design (public view-only link) *(future)*

---

## Phase 10 — Deployment 🔄 In Progress

- [x] `backend/Dockerfile` — Python 3.12-slim, thread pool, SIGTERM-safe
- [x] `frontend/Dockerfile` — node:20-alpine build → nginx:alpine serve
- [x] `docker-compose.yml` — dev compose (DB + backend + nginx)
- [x] `docker-compose.prod.yml` — production compose (no pgadmin, env-validated secrets, restart policies)
- [x] `frontend/nginx.conf` — fixed /api/ proxy, SPA routing
- [x] GitHub Actions CI — lint-backend (ruff), build-backend image, build-frontend + image
- [ ] `heart.stuartjatkinson.co.uk` routing + TLS via Cloudflare
- [ ] GitHub Actions CD — push images to registry → deploy
- [ ] Rate limiting on Overpass calls

---

## Current status summary

| Phase | Status | Key deliverables |
|---|---|---|
| 1. Core Backend | ✅ Done | FastAPI, Overpass proxy, thread pool, all endpoints |
| 2. SVG Generation | ✅ Done | 3 styles, cosLat projection, edge clipping, place labels |
| 3. STL Generation | ✅ Done | 3-piece interlock, gap closing, topology mode, 9 tunable params |
| 4. Licence Tracker | ✅ Done (v1) | ODbL attribution in every output |
| 5. CesiumJS Frontend | ✅ Done | Draw/move/resize/rotate, merch panel, style selector |
| 5b. SVG Viewer | ✅ Done | Pan/zoom, fit, download |
| 5c. 3D Map Viewer | ✅ Done | Live OSM render, Print Preview, live regenerate |
| 5d. Design System | ✅ Done | Unified CSS, variables, shared components |
| 5e. Client SVG Renderer | ✅ Done | TS port of svg_generator.py, client-side regen, save-svg endpoint |
| 6. SVG Editor | ✅ Done | Side panel, colour picker, layer toggles, live regen, 300 DPI output |
| 7. WooCommerce | 📋 Planned | |
| 8. POD Providers | 📋 Planned | |
| 9. Auth + Dashboard | ✅ Done | JWT auth, register/login, save/dashboard, user nav |
| 10. Deployment | 🔄 In Progress | Docker, prod compose, CI — CD + domain pending |
