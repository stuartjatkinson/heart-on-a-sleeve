import asyncio
import time
import httpx
from datetime import datetime
from ..models.schemas import BBox


class OverpassError(Exception):
    """Raised when the Overpass API cannot be reached or returns an error."""
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


# Mirror endpoints tried in order on failure
_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


class OSMFetcher:
    """Fetches OSM data via Overpass API with retry + fallback."""

    def __init__(self, overpass_endpoint: str):
        self.primary_endpoint = overpass_endpoint
        # Put the configured endpoint first, then any mirrors not already listed
        self._endpoints = [overpass_endpoint] + [e for e in _ENDPOINTS if e != overpass_endpoint]
        self._cache: dict[tuple, tuple[dict, float]] = {}
        self._cache_ttl = 300  # 5-minute TTL so colour regens are instant

    async def fetch_area(self, bbox: BBox, timeout: int = 60) -> dict:
        key = (round(bbox.west, 5), round(bbox.south, 5),
               round(bbox.east, 5), round(bbox.north, 5))
        cached = self._cache.get(key)
        if cached and (time.time() - cached[1] < self._cache_ttl):
            return cached[0]

        bb = f"{bbox.south},{bbox.west},{bbox.north},{bbox.east}"
        query = f"""
        [out:json][timeout:{timeout}];
        (
          way["highway"]({bb});
          way["landuse"]({bb});
          way["leisure"]({bb});
          way["natural"]({bb});
          way["building"]({bb});
          way["waterway"]({bb});
          way["railway"]({bb});
          relation["natural"]({bb});
          relation["landuse"]({bb});
          node["place"~"city|town|village|hamlet|suburb|neighbourhood|quarter|island"]({bb});
        );
        out body;
        >;
        out skel qt;
        """
        headers = {"User-Agent": "heart-on-a-sleeve/1.0", "Accept": "*/*"}
        last_error: OverpassError | None = None

        for endpoint in self._endpoints:
            for attempt in range(2):  # 2 attempts per endpoint before trying next
                if attempt > 0:
                    await asyncio.sleep(3)
                try:
                    async with httpx.AsyncClient(
                        timeout=httpx.Timeout(connect=10, read=timeout + 5, write=10, pool=5),
                        headers=headers,
                    ) as client:
                        response = await client.post(endpoint, data={"data": query})

                    if response.status_code == 429:
                        last_error = OverpassError(
                            "Overpass rate limit — wait a moment and try again", 429)
                        await asyncio.sleep(5)
                        continue
                    if response.status_code in (503, 504):
                        last_error = OverpassError(
                            f"Overpass service unavailable ({response.status_code})", response.status_code)
                        continue
                    if not response.is_success:
                        last_error = OverpassError(
                            f"Overpass returned HTTP {response.status_code}", response.status_code)
                        break  # non-transient — skip remaining attempts on this endpoint

                    data = response.json()
                    self._cache[key] = (data, time.time())
                    return data

                except httpx.TimeoutException:
                    last_error = OverpassError(
                        f"Overpass timed out after {timeout}s — try a smaller area", 504)
                except httpx.ConnectError:
                    last_error = OverpassError(
                        "Cannot reach Overpass API — check network connection", 503)
                except httpx.HTTPError as e:
                    last_error = OverpassError(f"Overpass network error: {e}", 502)

        raise last_error or OverpassError("Overpass fetch failed after retries", 502)

    async def get_license_info(self, bbox: BBox) -> dict:
        return {
            "license": "ODbL",
            "url": "https://www.openstreetmap.org/copyright",
            "attribution_required": True,
            "attribution": "© OpenStreetMap contributors",
            "data_sources": ["OpenStreetMap contributors"],
            "fetched_at": datetime.utcnow().isoformat(),
            "bbox": bbox.model_dump(),
        }
