# Heart on a Sleeve - Frontend (CesiumJS Map Selector)

## Overview
Three separate frontend apps sharing a common design language, all talking to the FastAPI backend via REST:

```
/frontend
├── /cesium        Map viewer — CesiumJS globe with OSM tiles, area selector
├── /svg-generator SVG preview & manipulation — loads generated SVG, lets user tweak styles
└── /3d-generator  3D preview — loads STL files, shows 3D render, sends to POD
```

## Cesium Map App (`/cesium`)
- CesiumJS globe with OpenStreetMap tile layer
- Click-to-draw bounding box selector (two clicks = bounding box)
- Merch type selector (grid of 6 types: tshirt, mug, placemat, coaster, tote, 3d_print)
- Map style selector (osm_default, minimalist, vibrant)
- Include toggles (labels, roads, parks)
- Generate button → calls backend → returns SVG/STL paths
- Location search via CesiumJS geocoder

## SVG Generator App (`/svg-generator`)
- Loads SVG output from backend
- Preview at actual merch dimensions
- Style tweaking (colors, line weights, label visibility)
- SVG layer editor (hide/show road/park/building layers)
- License attribution display
- Export at print resolution (300 DPI)
- Submit to WooCommerce

## 3D Generator App (`/3d-generator`)
- Loads STL from backend
- 3D preview (Three.js based viewer)
- Rotation/zoom inspection
- Customisation: base thickness, height, shape (circle/square for coasters)
- Download STL
- Submit to POD API (Prodigi/Printful)

## Shared
- `/shared/css/design-system.css` — common styles
- `/shared/js/api.js` — API client

## API Endpoints (FastAPI backend)
```
POST /api/osm/fetch           { bbox } → OSM JSON
POST /api/osm/license-info    { bbox } → license attribution
POST /api/generate/svg        { bbox, merch_type, style, includes } → { svg_path }
POST /api/generate/stl        { bbox, merch_type, height_mm, base_thickness_mm } → { stl_path }
POST /api/license/check       { bbox, data_sources } → compliance info
GET  /health                  → { status: ok }
GET  /output/svg_output/...   → static SVG files
GET  /output/stl_output/...   → static STL files
```