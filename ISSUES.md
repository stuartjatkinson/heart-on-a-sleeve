# Issues — Heart on a Sleeve

## Open

- [ ] **Cloud Run auth/sign-in broken — database tables never created** — `lifespan` in router.py is empty; no `create_all` or migration runner; Cloud Run doesn't use docker-compose so the PostgreSQL init SQL never runs; Cloud SQL instance and GitHub secrets may also be missing *(found 2026-05-26)*

## Resolved

- [x] **2D transition zoom starts during progress bar** — `fitBounds` moved before phase 3; loop lerps pixelated sel → fitBounds using same fake-asymptotic curve as the bar; phase 4 snaps remaining gap *(resolved 2026-05-23)*
- [x] **2D transition flicker (page navigation)** — merged map-selector + SVG viewer into one page; after transition phases complete the canvas fades out over the already-displayed inline SVG panel; "← Map" button returns to Cesium view without reload *(resolved 2026-05-23)*
- [x] **3D fabric preview: SVG becomes the canvas** — `tickEntry` auto-triggers fabric preview click after entry animation completes for non-3D merch types; user sees wireframe → solid OSM animation then SVG texture + buildings appear automatically *(resolved 2026-05-23)*

- [x] **SVG viewer: fabric types show "Export SVG" not "View 3D →"** — `is3dMerch` check hides btn-3d and highlights download button for tshirt/mug/tote *(resolved 2026-05-23)*
- [x] **3D viewer: SVG as base layer (fabric preview)** — `fabricGroup` + `loadFabricPreview()` load SVG as `TextureLoader` plane + buildings-only OSM render; `btn-mode` shows "🖼 Fabric Preview" for non-3D types *(resolved 2026-05-23)*
- [x] **3D viewer: layered STL print animation** — `printLayers` sub-groups per STL part; `runPrintAnimation()` phases: buildings wireframe fade-in → solid fill → water descends from above → land lid descends from above *(resolved 2026-05-23)*

- [x] **3D viewer road/waterway misalignment** — `roadMesh` built raw vertex buffers with `Z = +latProj`; `polyMesh`/`buildingMesh` use `rotateX(-π/2)` giving `Z = -latProj`; roads were north-south mirrored relative to all polygon features and faced downward (dark from the overhead sun). Fixed: negate all Z components in `roadMesh` vertex push *(resolved 2026-05-23)*

## Resolved

- [x] **3D viewer floating progress bar** — CSS override in 3d-viewer.html; render loop starts before OSM await; pre-load fake-asymptotic bar (0→50%, bbox-area tau); 3 s minimum pre-load; post-load 5 s wireframe entry drives bar 50→100%; bar hides on completion *(resolved 2026-05-23)*
- [x] **Auto-draw on merch click** — draw button removed; clicking any product type enters draw mode; re-clicking active type redraws; clicking different type while editing enforces new ratio without restarting *(resolved 2026-05-23)*
- [x] **Transition zoom to SVG-viewer fit bounds** — `getSvgViewerFitBounds(W,H,ratio)` computes exact landing rect (272 px panel + margins + merch ratio); phases 4+5 animate to that rect instead of full screen *(resolved 2026-05-23)*
- [x] **Progress bar tau from bbox-area estimate** — `estimateGenMs(bbox)` = 1000 + km²×1200 ms, capped 30 s; tau = estimatedMs/3; faster for tiny areas, slower for large cities *(resolved 2026-05-23)*
- [x] **Circle/hex coaster globe shapes** — `selCirclePoints`, `selHexagonPoints`, `selShapePoints` added to app.ts; polygon entity, polyline, `getZone` point-in-polygon check, and `getSelAabb` screen-space AABB all use `selShapePoints`; coaster circle/hexagon now draws the correct shape on the Cesium globe *(resolved 2026-05-23)*
- [x] **Transition redesign — trailing phase + zoom + dissolve** — `runTransition` in app.ts rewritten: phase 1 darken, phase 2 pixelate, phase 3 fake-asymptotic progress bar while awaiting SVG (min 300 ms), phase 4 zoom pixelated selection → fill screen (400 ms), phase 5 cross-dissolve pixelated → SVG (500 ms); `drawProgressBar` helper added *(resolved 2026-05-23)*
- [x] **Merch section order + emoji consistency** — Merch Type moved above Select Area; section numbering removed; tote 👜, placemat 🟫, relief ⛰, draw button ✜; `updateDrawBtn` now uses ✜ instead of 🎯 *(resolved 2026-05-23)*
- [x] **Colour swatches for map style** — 7-category colour picker (Canvas/Water/Fields/Parks/Urban/Buildings/Roads), 6 swatches each; palette_overrides sent to backend; urban_ind/road_other derived automatically *(resolved 2026-05-23)*
- [x] **Coaster shape cycling** — ‹ › buttons on coaster button cycle square/circle/hexagon; shape flows to SVG clipPath and STL plate outline *(resolved 2026-05-23)*
- [x] **SVG generator AttributeError** — `Group` has no attribute `path`; fixed by accessing elements correctly *(resolved 2026-05-23)*
- [x] **Camera north-lock** — postRender heading-snap to 0; heading no longer stored in _validCam *(resolved 2026-05-23)*
- [x] **Wakefield default + perpendicular start** — camera starts at Wakefield council area, pitch −90° (flat Google Maps view), 50 km altitude *(resolved 2026-05-23)*
- [x] **Place resolver (Nominatim)** — debounced search input calling Nominatim OSM geocoder; results dropdown flies camera to place bbox *(resolved 2026-05-23)*
- [x] **Mouse controls hint on selector** — floating hint bottom-right of map showing left/right/middle/scroll controls *(resolved 2026-05-23)*
- [x] **Merch type icons** — emoji icons added to all 6 merch buttons *(resolved 2026-05-23)*
- [x] **3D params explained + expandable** — each STL parameter has a description line; panel split into two collapsible `<details>` groups *(resolved 2026-05-23)*
