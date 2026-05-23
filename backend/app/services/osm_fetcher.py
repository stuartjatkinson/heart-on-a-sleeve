import httpx
from datetime import datetime
from ..models.schemas import BBox


class OSMFetcher:
    """Fetches OSM data via Overpass API."""

    def __init__(self, overpass_endpoint: str):
        self.endpoint = overpass_endpoint

    async def fetch_area(self, bbox: BBox, timeout: int = 60) -> dict:
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
        async with httpx.AsyncClient(timeout=timeout + 10, headers=headers) as client:
            response = await client.post(self.endpoint, data={"data": query})
            response.raise_for_status()
            return response.json()

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
