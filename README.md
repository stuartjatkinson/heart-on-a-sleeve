# Heart on a Sleeve

A map-to-merch platform. Select any area on an interactive OSM globe, choose a product, and generate print-ready SVG artwork and 3D-printable STL files from real OpenStreetMap data — with a live 3D preview that renders buildings, roads, and water directly from Overpass.

---

## What it does

1. **Draw a selection** on the CesiumJS globe — left-drag to draw, then move, resize (corner handles), or rotate (outer corner ring) the area. The bounding box is aspect-ratio locked to the chosen merch type.
2. **Choose merch** — Fabrics & Transfers (T-Shirt, Mug, Tote) or 3D Prints (Coaster, Placemat, Relief).
3. **Choose a style** — OSM Default (warm cartographic), Minimalist (greyscale + railways), or Vibrant (saturated).
4. **Generate** — backend fetches OSM vector data from Overpass, renders a print-ready SVG and a 3D-printable STL.
5. **Preview** — SVG opens in a pan/zoom viewer; 3D opens a live Three.js renderer (buildings extruded from real OSM `building:levels`/`building:height` tags, roads, water, parks) with scheme-matched solid colours and per-type neon wireframe mode.

---

## Architecture

```
heart-on-a-sleeve/
├── backend/                        FastAPI (Python 3.14)
│   ├── app/
│   │   ├── api/router.py           REST endpoints
│   │   ├── services/
│   │   │   ├── osm_fetcher.py      Async Overpass API client (httpx)
│   │   │   ├── svg_generator.py    OSM → print-ready SVG (svgwrite)
│   │   │   ├── stl_generator.py    OSM → 3D-printable STL (trimesh + shapely)
│   │   │   └── license_tracker.py  ODbL attribution
│   │   ├── models/schemas.py       Pydantic models
│   │   └── core/config.py          Settings
│   ├── main.py
│   └── requirements.txt
│
└── frontend/cesium/                Vite + TypeScript + CesiumJS
    ├── src/app.ts                  Globe selector, bbox drawing, merch panel
    └── public/
        ├── 3d-viewer.html          Live Three.js OSM 3D renderer
        └── svg-viewer.html         Pan/zoom SVG viewer
```

---

## Running locally

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app.api.router:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```powershell
cd frontend/cesium
npm install
npm run dev          # → http://localhost:5173
```

The Vite dev server proxies `/api` and `/output` to the backend at port 8000.

---

## API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/generate/svg` | Fetch OSM data + render SVG |
| `POST` | `/api/generate/stl` | Fetch OSM data + generate STL |
| `POST` | `/api/license/check` | ODbL attribution info |
| `GET` | `/output/svg_output/{file}` | Download generated SVG |
| `GET` | `/output/stl_output/{file}` | Download generated STL |

---

## Merch types

| Product | Category | Aspect ratio | Print size |
|---|---|---|---|
| T-Shirt | Fabric | 3:4 | 3000×4000 px @300 dpi |
| Mug | Fabric | 9:3 | 2700×900 px @300 dpi |
| Tote Bag | Fabric | 2:3 | 2000×3000 px @300 dpi |
| Coaster | 3D Print | 1:1 | 95×95 mm plate |
| Placemat | 3D Print | 14:10 | 150×107 mm plate |
| Relief | 3D Print | 1:1 | 100×100 mm plate |

---

## Map styles

| Style | Roads | Buildings | Railways | Labels |
|---|---|---|---|---|
| OSM Default | Main + other | Yes | No | Place names |
| Minimalist | Main only | No | Yes (black) | No |
| Vibrant | Main + other | Yes | Yes (dark) | Place names |

Place labels: city (bold uppercase) → town → village → suburb → neighbourhood, sized by hierarchy.

---

## 3D print modes

| Merch | Mode | Description |
|---|---|---|
| **Relief** | Topology | Buildings at real OSM heights, roads raised 0.5 mm |
| **Coaster / Placemat** | Plexi-flat | All buildings normalised to same flat-top height — glue clear acrylic flush to building tops to seal the map beneath |
| **Fabrics** | Basic | Flat base + roads + gentle building extrusions (reference object) |

---

## 3D viewer

The 3D viewer (`/3d-viewer.html`) fetches OSM data live from Overpass for the selected bbox and renders directly in Three.js — no file conversion:

- Buildings extruded by `building:levels` × 3.2 m (or `building:height` tag)
- Three height tiers: low / mid / high with distinct shading
- Roads as hand-built ribbon geometry, width by road class
- Water and parks as flat coloured polygons
- Solid colours follow the selected 2D style scheme
- Wireframe colours are fixed per feature type: parks=green, water=blue, roads=orange/yellow, buildings=cyan/purple/white

---

## Tech stack

| Layer | Technology |
|---|---|
| Globe selector | CesiumJS 1.141 — OSM tiles, no Ion token required |
| Frontend build | Vite 8 + TypeScript |
| 3D preview | Three.js 0.160 + OrbitControls |
| SVG viewer | Vanilla JS inline SVG, pan/zoom |
| Backend API | FastAPI 0.136 + Uvicorn |
| OSM data | Overpass API (overpass-api.de) via httpx async |
| SVG generation | svgwrite |
| STL generation | trimesh + shapely |
| Licence compliance | ODbL — attribution embedded in all SVG outputs |

---

## Data & licence

OpenStreetMap data © OpenStreetMap contributors, licensed under [ODbL](https://opendatacommons.org/licenses/odbl/). Attribution is required in all generated outputs and is embedded automatically.

See [docs/ROADMAP.md](docs/ROADMAP.md) for the full build plan.
