import * as Cesium from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';

Cesium.Ion.defaultAccessToken = '';

// ---------------------------------------------------------------------------
// Viewer
// ---------------------------------------------------------------------------
const viewer = new Cesium.Viewer('cesiumContainer', {
  imageryProvider: false as unknown as Cesium.ImageryProvider,
  terrainProvider: new Cesium.EllipsoidTerrainProvider(),
  baseLayerPicker: false as unknown as boolean, geocoder: false as unknown as boolean,
  homeButton: false as unknown as boolean, sceneModePicker: false as unknown as boolean,
  navigationHelpButton: false as unknown as boolean, animation: false as unknown as boolean,
  timeline: false as unknown as boolean, fullscreenButton: false as unknown as boolean,
  selectionIndicator: false as unknown as boolean, infoBox: false as unknown as boolean,
} as unknown as Cesium.Viewer.ConstructorOptions);

viewer.imageryLayers.addImageryProvider(new Cesium.UrlTemplateImageryProvider({
  url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  credit: '© OpenStreetMap contributors', maximumLevel: 19,
}));

viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString('#1a1a24');
viewer.scene.backgroundColor = Cesium.Color.fromCssColorString('#0a0a0a');
viewer.scene.globe.translucency.enabled = false;
viewer.camera.constrainedAxis = Cesium.Cartesian3.UNIT_Z;
viewer.scene.screenSpaceCameraController.maximumZoomDistance = 20_000_000;
viewer.scene.screenSpaceCameraController.minimumZoomDistance = 100;

const PITCH_MAX = -(Math.PI * 20) / 180, PITCH_MIN = -Math.PI / 2;
let _validCam = { position: viewer.camera.position.clone(), heading: viewer.camera.heading, pitch: viewer.camera.pitch };
viewer.scene.postRender.addEventListener(() => {
  const p = viewer.camera.pitch;
  if (p > PITCH_MAX || p < PITCH_MIN) {
    viewer.camera.setView({ destination: _validCam.position.clone(),
      orientation: { heading: _validCam.heading, pitch: _validCam.pitch, roll: 0 } });
  } else {
    _validCam = { position: viewer.camera.position.clone(), heading: viewer.camera.heading, pitch: p };
  }
});
viewer.camera.setView({
  destination: Cesium.Cartesian3.fromDegrees(-1.5, 52.5, 500_000),
  orientation: { heading: 0, pitch: Cesium.Math.toRadians(-50), roll: 0 },
});
_validCam = { position: viewer.camera.position.clone(), heading: viewer.camera.heading, pitch: viewer.camera.pitch };

// ---------------------------------------------------------------------------
// Selection state — rotated rectangle stored as centre + half-dims + angle
// ---------------------------------------------------------------------------
type BBox  = { north: number; south: number; east: number; west: number };
type Corner = 'nw' | 'ne' | 'se' | 'sw';
// RotSel: cx/cy = centre lon/lat, hw/hh = half-width/height in °lon/°lat, rot = radians CW from north
type RotSel = { cx: number; cy: number; hw: number; hh: number; rot: number };

const CORNERS: Corner[] = ['nw', 'ne', 'se', 'sw'];
const MERCH_RATIO: Record<string, number> = {
  tshirt: 3000/4000, mug: 2700/900, placemat: 4200/3000,
  coaster: 1, tote: 2000/3000, '3d_print': 1,
};

let confirmed: RotSel | null = null;
let _live: RotSel | null = null;
let editState: 'idle' | 'drawing' | 'editing' = 'idle';
let merchType = 'tshirt', mapStyle = 'osm_default';
let includes = { labels: true, buildings: true };

// ---------------------------------------------------------------------------
// RotSel geometry
// ---------------------------------------------------------------------------
function rotSelCorners(s: RotSel): { lon: number; lat: number }[] {
  const cosL = Math.cos(s.cy * Math.PI / 180);
  const ca = Math.cos(s.rot), sa = Math.sin(s.rot);
  return ([ [-s.hw, s.hh], [s.hw, s.hh], [s.hw, -s.hh], [-s.hw, -s.hh] ] as [number,number][])
    .map(([dx, dy]) => {
      const ix = dx * cosL, iy = dy;      // isotropic space
      const rx = ix * ca - iy * sa;       // rotate
      const ry = ix * sa + iy * ca;
      return { lon: s.cx + rx / cosL, lat: s.cy + ry }; // back to deg
    });
}

function rotSelAabb(s: RotSel): BBox {
  const c = rotSelCorners(s);
  return {
    west:  Math.min(...c.map(p => p.lon)), east:  Math.max(...c.map(p => p.lon)),
    south: Math.min(...c.map(p => p.lat)), north: Math.max(...c.map(p => p.lat)),
  };
}

function bboxToRotSel(b: BBox): RotSel {
  return { cx: (b.west+b.east)/2, cy: (b.south+b.north)/2,
           hw: (b.east-b.west)/2, hh: (b.north-b.south)/2, rot: 0 };
}

function cornerOf(c: Corner, s: RotSel): { lon: number; lat: number } {
  const idx = { nw:0, ne:1, se:2, sw:3 }[c];
  return rotSelCorners(s)[idx];
}

function enforceRatio(s: RotSel, ratio: number): RotSel {
  const cosL = Math.cos(s.cy * Math.PI / 180);
  const wM = s.hw * cosL * 111_320 * 2, hM = s.hh * 111_320 * 2;
  if (wM / hM > ratio) {
    return { ...s, hh: (wM / ratio) / 111_320 / 2 };
  } else {
    return { ...s, hw: (hM * ratio) / (cosL * 111_320) / 2 };
  }
}

// ---------------------------------------------------------------------------
// Entities
// ---------------------------------------------------------------------------
const canvas = viewer.scene.canvas;
const handler = new Cesium.ScreenSpaceEventHandler(canvas);

const selEntity = viewer.entities.add({
  show: false,
  polygon: {
    hierarchy: new Cesium.CallbackProperty(() => {
      if (!_live) return null;
      const positions = rotSelCorners(_live).map(c => Cesium.Cartesian3.fromDegrees(c.lon, c.lat));
      return new Cesium.PolygonHierarchy(positions);
    }, false),
    material: Cesium.Color.fromCssColorString('#4a9eff').withAlpha(0.15),
    height: 0,
  } as unknown as Cesium.PolygonGraphics,
  polyline: {
    positions: new Cesium.CallbackProperty(() => {
      if (!_live) return [];
      const c = rotSelCorners(_live);
      return [...c, c[0]].map(p => Cesium.Cartesian3.fromDegrees(p.lon, p.lat));
    }, false),
    width: 2,
    material: new Cesium.ColorMaterialProperty(Cesium.Color.fromCssColorString('#4a9eff')),
    clampToGround: true,
  },
});

// Hover state drives handle colours via CallbackProperty
let hovResize: Corner | null = null;
let hovRotate: Corner | null = null;

function makeResizeHandle(c: Corner): Cesium.Entity {
  return viewer.entities.add({
    show: false,
    position: new Cesium.CallbackProperty(() => {
      if (!_live) return Cesium.Cartesian3.ZERO;
      const p = cornerOf(c, _live);
      return Cesium.Cartesian3.fromDegrees(p.lon, p.lat);
    }, false) as unknown as Cesium.PositionProperty,
    point: {
      pixelSize: 11,
      color: new Cesium.CallbackProperty(() =>
        hovResize === c ? Cesium.Color.fromCssColorString('#4a9eff') : Cesium.Color.WHITE, false),
      outlineColor: Cesium.Color.fromCssColorString('#4a9eff'),
      outlineWidth: 2,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    },
  });
}

// Rotate handle: same corner position but rendered as a ring billboard, offset outward 22px
function makeRotateHandle(c: Corner): Cesium.Entity {
  return viewer.entities.add({
    show: false,
    position: new Cesium.CallbackProperty(() => {
      if (!_live) return Cesium.Cartesian3.ZERO;
      const p = cornerOf(c, _live);
      return Cesium.Cartesian3.fromDegrees(p.lon, p.lat);
    }, false) as unknown as Cesium.PositionProperty,
    billboard: {
      image: makeRotateCursorCanvas(),
      pixelOffset: new Cesium.Cartesian2(
        c.includes('e') ? 18 : -18,
        c.includes('s') ? 18 : -18,
      ),
      color: new Cesium.CallbackProperty(() =>
        hovRotate === c ? Cesium.Color.fromCssColorString('#4a9eff') : Cesium.Color.WHITE.withAlpha(0.9), false),
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
      scale: 1,
    },
  });
}

function makeRotateCursorCanvas(): HTMLCanvasElement {
  const s = 22;
  const cv = document.createElement('canvas');
  cv.width = cv.height = s;
  const ctx = cv.getContext('2d')!;
  ctx.strokeStyle = '#ffffff';
  ctx.lineWidth = 2.5;
  // Draw arc (270° arc = 3/4 circle)
  ctx.beginPath();
  ctx.arc(s/2, s/2, s/2 - 3, -Math.PI * 0.75, Math.PI * 0.5);
  ctx.stroke();
  // Arrow head
  const ex = s/2 + (s/2 - 3) * Math.cos(Math.PI * 0.5);
  const ey = s/2 + (s/2 - 3) * Math.sin(Math.PI * 0.5);
  ctx.beginPath();
  ctx.moveTo(ex - 4, ey - 4);
  ctx.lineTo(ex, ey);
  ctx.lineTo(ex + 4, ey - 4);
  ctx.stroke();
  return cv;
}

const resizeHandles = Object.fromEntries(CORNERS.map(c => [c, makeResizeHandle(c)])) as Record<Corner, Cesium.Entity>;
const rotateHandles = Object.fromEntries(CORNERS.map(c => [c, makeRotateHandle(c)])) as Record<Corner, Cesium.Entity>;

function showHandles(show: boolean): void {
  CORNERS.forEach(c => { resizeHandles[c].show = show; rotateHandles[c].show = show; });
}

// ---------------------------------------------------------------------------
// Picking & hover zones
// ---------------------------------------------------------------------------
const INNER_PX = 14, OUTER_PX = 30;

function pickLatLon(pos: Cesium.Cartesian2): { lon: number; lat: number } | null {
  const ray = viewer.camera.getPickRay(pos);
  if (!ray) return null;
  const hit = viewer.scene.globe.pick(ray, viewer.scene);
  if (!hit) return null;
  const c = Cesium.Cartographic.fromCartesian(hit);
  return { lon: Cesium.Math.toDegrees(c.longitude), lat: Cesium.Math.toDegrees(c.latitude) };
}

function worldToScreen(lon: number, lat: number): Cesium.Cartesian2 | null {
  return Cesium.SceneTransforms.worldToWindowCoordinates(viewer.scene,
    Cesium.Cartesian3.fromDegrees(lon, lat)) ?? null;
}

type HoverZone = { type: 'none' } | { type: 'inside' } | { type: 'resize'; corner: Corner } | { type: 'rotate'; corner: Corner };

function getZone(screenPos: Cesium.Cartesian2): HoverZone {
  if (!_live) return { type: 'none' };
  for (const c of CORNERS) {
    const p = cornerOf(c, _live);
    const sc = worldToScreen(p.lon, p.lat);
    if (!sc) continue;
    const d = Math.hypot(screenPos.x - sc.x, screenPos.y - sc.y);
    if (d <= INNER_PX)  return { type: 'resize', corner: c };
    if (d <= OUTER_PX)  return { type: 'rotate', corner: c };
  }
  const w = pickLatLon(screenPos);
  if (w && _live) {
    const corners = rotSelCorners(_live);
    if (pointInPolygon(w.lon, w.lat, corners)) return { type: 'inside' };
  }
  return { type: 'none' };
}

function pointInPolygon(lon: number, lat: number, poly: { lon: number; lat: number }[]): boolean {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const xi = poly[i].lon, yi = poly[i].lat, xj = poly[j].lon, yj = poly[j].lat;
    if ((yi > lat) !== (yj > lat) && lon < (xj - xi) * (lat - yi) / (yj - yi) + xi)
      inside = !inside;
  }
  return inside;
}

const CURSOR: Record<Corner, string> = { nw: 'nwse-resize', se: 'nwse-resize', ne: 'nesw-resize', sw: 'nesw-resize' };
function setCursor(c: string) { canvas.style.cursor = c; }

// ---------------------------------------------------------------------------
// Drawing
// ---------------------------------------------------------------------------
function enterDrawing(): void {
  editState = 'drawing';
  confirmed = null; _live = null;
  selEntity.show = false; showHandles(false);
  viewer.scene.screenSpaceCameraController.enableRotate = false;
  setCursor('crosshair'); updateDrawBtn();
  const genBtn = document.getElementById('generate-btn') as HTMLButtonElement;
  genBtn.disabled = true; genBtn.onclick = generate;
  document.getElementById('bbox-display')!.textContent = 'Left-drag on the map to draw your area';
  document.getElementById('status')!.textContent = '';

  let anchor: { lon: number; lat: number } | null = null;

  handler.setInputAction((e: Cesium.ScreenSpaceEventHandler.PositionedEvent) => {
    anchor = pickLatLon(e.position);
    if (anchor) selEntity.show = true;
  }, Cesium.ScreenSpaceEventType.LEFT_DOWN);

  handler.setInputAction((e: Cesium.ScreenSpaceEventHandler.MotionEvent) => {
    if (!anchor) return;
    const cur = pickLatLon(e.endPosition);
    if (!cur) return;
    const raw = bboxToRotSel({
      west: Math.min(anchor.lon, cur.lon), east: Math.max(anchor.lon, cur.lon),
      south: Math.min(anchor.lat, cur.lat), north: Math.max(anchor.lat, cur.lat),
    });
    _live = enforceRatio({ ...raw, cx: anchor.lon + (cur.lon - anchor.lon)/2,
                                   cy: anchor.lat + (cur.lat - anchor.lat)/2 }, MERCH_RATIO[merchType] ?? 1);
    updateBboxDisplay();
  }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);

  handler.setInputAction((_e: Cesium.ScreenSpaceEventHandler.PositionedEvent) => {
    if (!anchor || !_live) { anchor = null; return; }
    const result = { ..._live };
    anchor = null;
    clearHandlers();
    enterEditing(result);
  }, Cesium.ScreenSpaceEventType.LEFT_UP);
}

function clearHandlers(): void {
  handler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_DOWN);
  handler.removeInputAction(Cesium.ScreenSpaceEventType.MOUSE_MOVE);
  handler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_UP);
  viewer.scene.screenSpaceCameraController.enableRotate = true;
}

// ---------------------------------------------------------------------------
// Editing — single handler set, dragMode controls behaviour
// ---------------------------------------------------------------------------
type DragMode = 'none' | 'move' | { kind: 'resize'; corner: Corner } | { kind: 'rotate'; corner: Corner };
let dragMode: DragMode = 'none';
let dragMoveAnchor: { lon: number; lat: number } | null = null;
let dragMoveStart: RotSel | null = null;
let dragResizeFixed: { lon: number; lat: number } | null = null;
let dragRotStart: RotSel | null = null;
let dragRotAnchorAngle = 0;

function enterEditing(s: RotSel): void {
  editState = 'editing';
  confirmed = { ...s }; _live = { ...s };
  selEntity.show = true; showHandles(true);
  viewer.scene.screenSpaceCameraController.enableRotate = true;
  setCursor('default'); updateDrawBtn(); updateBboxDisplay();
  const genBtn = document.getElementById('generate-btn') as HTMLButtonElement;
  genBtn.disabled = false; genBtn.onclick = generate;

  handler.setInputAction((e: Cesium.ScreenSpaceEventHandler.MotionEvent) => {
    if (editState !== 'editing') return;

    // Active drag
    if (dragMode !== 'none') {
      const cur = pickLatLon(e.endPosition);
      if (!cur || !_live) return;

      if (dragMode === 'move' && dragMoveAnchor && dragMoveStart) {
        _live = { ...dragMoveStart,
          cx: dragMoveStart.cx + cur.lon - dragMoveAnchor.lon,
          cy: dragMoveStart.cy + cur.lat - dragMoveAnchor.lat,
        };
      } else if (typeof dragMode === 'object' && dragMode.kind === 'resize' && dragResizeFixed) {
        // Project mouse into rotated frame, compute new half-dims
        const cosL = Math.cos(_live.cy * Math.PI / 180);
        const ca = Math.cos(-_live.rot), sa = Math.sin(-_live.rot);
        const dx = (cur.lon - _live.cx) * cosL;
        const dy = cur.lat - _live.cy;
        const px = (dx * ca - dy * sa) / cosL;  // projected onto W axis
        const py = dx * sa + dy * ca;            // projected onto H axis
        let hw = Math.abs(px), hh = Math.abs(py);
        const ratio = MERCH_RATIO[merchType] ?? 1;
        const wM = hw * cosL * 111_320, hM = hh * 111_320;
        if (wM / hM > ratio) hh = wM / ratio / 111_320; else hw = hM * ratio / (cosL * 111_320);
        _live = { ..._live, hw, hh };
      } else if (typeof dragMode === 'object' && dragMode.kind === 'rotate' && dragRotStart) {
        const cosL = Math.cos(dragRotStart.cy * Math.PI / 180);
        const angle = Math.atan2((cur.lon - dragRotStart.cx) * cosL, cur.lat - dragRotStart.cy);
        _live = { ...dragRotStart, rot: dragRotStart.rot + (angle - dragRotAnchorAngle) };
        dragRotAnchorAngle = angle;
        dragRotStart = { ..._live };
      }
      updateBboxDisplay();
      return;
    }

    // Hover — update cursor and handle highlights
    const zone = getZone(e.endPosition);
    hovResize = zone.type === 'resize' ? zone.corner : null;
    hovRotate = zone.type === 'rotate' ? zone.corner : null;
    if (zone.type === 'resize')      setCursor(CURSOR[zone.corner]);
    else if (zone.type === 'rotate') setCursor('alias');
    else if (zone.type === 'inside') setCursor('move');
    else                             setCursor('default');
  }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);

  handler.setInputAction((e: Cesium.ScreenSpaceEventHandler.PositionedEvent) => {
    if (editState !== 'editing' || !_live) return;
    const zone = getZone(e.position);
    if (zone.type === 'none') return;
    viewer.scene.screenSpaceCameraController.enableRotate = false;

    if (zone.type === 'inside') {
      dragMode = 'move';
      dragMoveAnchor = pickLatLon(e.position);
      dragMoveStart = { ..._live };
    } else if (zone.type === 'resize') {
      dragMode = { kind: 'resize', corner: zone.corner };
      const opp: Corner = zone.corner === 'nw' ? 'se' : zone.corner === 'ne' ? 'sw' : zone.corner === 'se' ? 'nw' : 'ne';
      dragResizeFixed = cornerOf(opp, _live);
    } else if (zone.type === 'rotate') {
      const cosL = Math.cos(_live.cy * Math.PI / 180);
      const clicked = pickLatLon(e.position);
      if (!clicked) return;
      dragMode = { kind: 'rotate', corner: zone.corner };
      dragRotStart = { ..._live };
      dragRotAnchorAngle = Math.atan2((clicked.lon - _live.cx) * cosL, clicked.lat - _live.cy);
    }
  }, Cesium.ScreenSpaceEventType.LEFT_DOWN);

  handler.setInputAction((_e: Cesium.ScreenSpaceEventHandler.PositionedEvent) => {
    if (dragMode === 'none') return;
    confirmed = _live ? { ..._live } : null;
    dragMode = 'none'; dragMoveAnchor = null; dragMoveStart = null;
    dragResizeFixed = null; dragRotStart = null;
    viewer.scene.screenSpaceCameraController.enableRotate = true;
  }, Cesium.ScreenSpaceEventType.LEFT_UP);
}

function exitEditing(): void {
  clearHandlers();
  dragMode = 'none'; hovResize = null; hovRotate = null;
  selEntity.show = false; _live = null; showHandles(false);
  setCursor('default');
}

// ---------------------------------------------------------------------------
// Draw button
// ---------------------------------------------------------------------------
function startSelection(): void {
  if (editState === 'drawing') {
    clearHandlers(); editState = 'idle';
    selEntity.show = false; _live = null; updateDrawBtn(); return;
  }
  if (editState === 'editing') exitEditing();
  enterDrawing();
}

function updateDrawBtn(): void {
  const btn = document.getElementById('draw-btn')!;
  if (editState === 'drawing') {
    btn.textContent = '✕ Cancel'; btn.style.borderColor = '#4a9eff'; btn.style.color = '#4a9eff';
  } else {
    btn.textContent = confirmed ? '🎯 Redraw' : '🎯 Draw Selection';
    btn.style.borderColor = ''; btn.style.color = '';
  }
}

function updateBboxDisplay(): void {
  if (!_live) return;
  const b = rotSelAabb(_live);
  document.getElementById('bbox-display')!.innerHTML =
    `N:&nbsp;${b.north.toFixed(4)} &nbsp; S:&nbsp;${b.south.toFixed(4)}<br>` +
    `E:&nbsp;${b.east.toFixed(4)} &nbsp; W:&nbsp;${b.west.toFixed(4)}` +
    (_live.rot !== 0 ? ` &nbsp; ↻&nbsp;${(_live.rot * 180 / Math.PI).toFixed(1)}°` : '');
}

// ---------------------------------------------------------------------------
// UI
// ---------------------------------------------------------------------------
function selectMerch(el: HTMLElement): void {
  document.querySelectorAll('.merch-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  merchType = el.dataset.type!;
  if (_live && editState === 'editing') {
    _live = enforceRatio(_live, MERCH_RATIO[merchType] ?? 1);
    confirmed = { ..._live };
    updateBboxDisplay();
  }
}

function selectStyle(el: HTMLElement): void {
  document.querySelectorAll('.style-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  mapStyle = el.dataset.style!;
}

function toggle(el: HTMLElement): void {
  el.classList.toggle('on');
  (includes as any)[el.id.replace('tog-', '')] = el.classList.contains('on');
}

// ---------------------------------------------------------------------------
// Generate — managed entirely via onclick, no persistent addEventListener
// ---------------------------------------------------------------------------
const genBtn    = document.getElementById('generate-btn') as HTMLButtonElement;
const outputDiv = document.getElementById('output-btns') as HTMLElement;
const view2dBtn = document.getElementById('view-2d-btn') as HTMLButtonElement;
const view3dBtn = document.getElementById('view-3d-btn') as HTMLButtonElement;

function resetOutputBtns(): void {
  outputDiv.style.display = 'none';
  view2dBtn.onclick = null;
  view3dBtn.onclick = null;
}

async function generate(): Promise<void> {
  if (!confirmed) return;
  const bbox    = rotSelAabb(confirmed);
  const spinner = document.getElementById('spinner')!;
  const btnText = document.getElementById('btn-text')!;
  const status  = document.getElementById('status')!;

  genBtn.disabled = true; genBtn.onclick = null;
  resetOutputBtns();
  spinner.style.display = 'block';
  btnText.textContent = 'Generating...'; status.textContent = '';

  const start = Date.now();
  const timer = setInterval(() => {
    status.textContent = `Fetching OSM data… ${Math.round((Date.now() - start) / 1000)}s`;
  }, 1000);
  const abort = new AbortController();
  const hard  = setTimeout(() => abort.abort(), 90_000);

  try {
    status.textContent = 'Fetching OSM data…';
    const svgRes = await fetch('/api/generate/svg', {
      method: 'POST', signal: abort.signal,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bbox, merch_type: merchType, style: mapStyle,
        include_labels: includes.labels, include_buildings: includes.buildings,
        include_roads: true, include_parks: true }),
    });
    clearInterval(timer); clearTimeout(hard);
    if (!svgRes.ok) throw new Error(`Server ${svgRes.status}`);
    const svgResult = await svgRes.json();

    status.textContent = 'Generating 3D model...';
    const stlRes = await fetch('/api/generate/stl', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bbox, merch_type: merchType, height_mm: 5.0, base_thickness_mm: 2.0 }),
    });
    const stlResult = await stlRes.json();

    const licRes  = await fetch('/api/license/check', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bbox, data_sources: ['osm'] }),
    });
    const licData = await licRes.json();

    status.textContent = `Done — ${licData.attribution || '© OpenStreetMap contributors'}`;
    spinner.style.display = 'none';
    btnText.textContent = 'Regenerate';
    genBtn.disabled = false;
    genBtn.onclick = generate;

    // Show both output buttons
    outputDiv.style.display = 'flex';
    view2dBtn.onclick = () => window.open(`/svg-viewer.html?svg=${encodeURIComponent(svgResult.svg_url)}`, '_blank');
    view3dBtn.onclick = () => {
      const b = rotSelAabb(confirmed!);
      const p = new URLSearchParams({
        west:  String(b.west),  south: String(b.south),
        east:  String(b.east),  north: String(b.north),
        style: mapStyle, merch: merchType,
      });
      if (stlResult.stl_buildings_url) p.set('stl_buildings', stlResult.stl_buildings_url);
      if (stlResult.stl_land_url)      p.set('stl_land',      stlResult.stl_land_url);
      if (stlResult.stl_water_url)     p.set('stl_water',     stlResult.stl_water_url);
      window.open(`/3d-viewer.html?${p}`, '_blank');
    };

  } catch (err: any) {
    clearInterval(timer); clearTimeout(hard);
    status.textContent = err.name === 'AbortError' ? 'Timed out — try a smaller area' : `Error: ${err.message}`;
    genBtn.disabled = false; btnText.textContent = 'Retry';
    spinner.style.display = 'none';
    genBtn.onclick = generate;
  }
}

// ---------------------------------------------------------------------------
// Wire up (generate managed via onclick only — no persistent addEventListener)
// ---------------------------------------------------------------------------
genBtn.onclick = generate;
document.getElementById('draw-btn')!.addEventListener('click', startSelection);
document.querySelectorAll<HTMLElement>('.merch-btn').forEach(el => el.addEventListener('click', () => selectMerch(el)));
document.querySelectorAll<HTMLElement>('.style-btn').forEach(el => el.addEventListener('click', () => selectStyle(el)));
document.querySelectorAll<HTMLElement>('.toggle').forEach(el => el.addEventListener('click', () => toggle(el)));
