"""
Geocoding service with embedded US city database.
Falls back to Nominatim for cities not in the database.
"""
import logging
import httpx
from cachetools import TTLCache
import asyncio

logger = logging.getLogger(__name__)

_geo_cache = TTLCache(maxsize=500, ttl=86400)

# Top US cities with lat/lng
US_CITIES = {
    "new york": (40.7128, -74.0060),
    "new york city": (40.7128, -74.0060),
    "nyc": (40.7128, -74.0060),
    "los angeles": (34.0522, -118.2437),
    "la": (34.0522, -118.2437),
    "chicago": (41.8781, -87.6298),
    "houston": (29.7604, -95.3698),
    "phoenix": (33.4484, -112.0740),
    "philadelphia": (39.9526, -75.1652),
    "san antonio": (29.4241, -98.4936),
    "san diego": (32.7157, -117.1611),
    "dallas": (32.7767, -96.7970),
    "san jose": (37.3382, -121.8863),
    "austin": (30.2672, -97.7431),
    "jacksonville": (30.3322, -81.6557),
    "fort worth": (32.7555, -97.3308),
    "columbus": (39.9612, -82.9988),
    "charlotte": (35.2271, -80.8431),
    "indianapolis": (39.7684, -86.1581),
    "san francisco": (37.7749, -122.4194),
    "sf": (37.7749, -122.4194),
    "seattle": (47.6062, -122.3321),
    "denver": (39.7392, -104.9903),
    "washington": (38.9072, -77.0369),
    "washington dc": (38.9072, -77.0369),
    "dc": (38.9072, -77.0369),
    "nashville": (36.1627, -86.7816),
    "oklahoma city": (35.4676, -97.5164),
    "el paso": (31.7619, -106.4850),
    "boston": (42.3601, -71.0589),
    "portland": (45.5152, -122.6784),
    "las vegas": (36.1699, -115.1398),
    "vegas": (36.1699, -115.1398),
    "memphis": (35.1495, -90.0490),
    "louisville": (38.2527, -85.7585),
    "baltimore": (39.2904, -76.6122),
    "milwaukee": (43.0389, -87.9065),
    "albuquerque": (35.0844, -106.6504),
    "tucson": (32.2226, -110.9747),
    "fresno": (36.7378, -119.7871),
    "sacramento": (38.5816, -121.4944),
    "mesa": (33.4152, -111.8315),
    "kansas city": (39.0997, -94.5786),
    "atlanta": (33.7490, -84.3880),
    "omaha": (41.2565, -95.9345),
    "colorado springs": (38.8339, -104.8214),
    "raleigh": (35.7796, -78.6382),
    "long beach": (33.7701, -118.1937),
    "virginia beach": (36.8529, -75.9780),
    "miami": (25.7617, -80.1918),
    "oakland": (37.8044, -122.2712),
    "minneapolis": (44.9778, -93.2650),
    "tulsa": (36.1540, -95.9928),
    "tampa": (27.9506, -82.4572),
    "arlington": (32.7357, -97.1081),
    "new orleans": (29.9511, -90.0715),
    "cleveland": (41.4993, -81.6944),
    "bakersfield": (35.3733, -119.0187),
    "aurora": (39.7294, -104.8319),
    "anaheim": (33.8366, -117.9143),
    "honolulu": (21.3069, -157.8583),
    "santa ana": (33.7455, -117.8677),
    "riverside": (33.9806, -117.3755),
    "corpus christi": (27.8006, -97.3964),
    "lexington": (38.0406, -84.5037),
    "pittsburgh": (40.4406, -79.9959),
    "anchorage": (61.2181, -149.9003),
    "stockton": (37.9577, -121.2908),
    "cincinnati": (39.1031, -84.5120),
    "saint paul": (44.9537, -93.0900),
    "st paul": (44.9537, -93.0900),
    "toledo": (41.6528, -83.5379),
    "newark": (40.7357, -74.1724),
    "greensboro": (36.0726, -79.7920),
    "buffalo": (42.8864, -78.8784),
    "plano": (33.0198, -96.6989),
    "lincoln": (40.8258, -96.6852),
    "henderson": (36.0395, -114.9817),
    "fort wayne": (41.0793, -85.1394),
    "jersey city": (40.7178, -74.0431),
    "st louis": (38.6270, -90.1994),
    "saint louis": (38.6270, -90.1994),
    "chula vista": (32.6401, -117.0842),
    "norfolk": (36.8508, -76.2859),
    "orlando": (28.5383, -81.3792),
    "chandler": (33.3062, -111.8413),
    "laredo": (27.5036, -99.5076),
    "madison": (43.0731, -89.4012),
    "lubbock": (33.5779, -101.8552),
    "winston-salem": (36.0999, -80.2442),
    "baton rouge": (30.4515, -91.1871),
    "durham": (35.9940, -78.8986),
    "garland": (32.9126, -96.6389),
    "glendale": (33.5387, -112.1860),
    "reno": (39.5296, -119.8138),
    "hialeah": (25.8576, -80.2781),
    "chesapeake": (36.7682, -76.2875),
    "scottsdale": (33.4942, -111.9261),
    "irving": (32.8140, -96.9489),
    "fremont": (37.5485, -121.9886),
    "irvine": (33.6846, -117.8265),
    "birmingham": (33.5186, -86.8104),
    "richmond": (37.5407, -77.4360),
    "spokane": (47.6588, -117.4260),
    "rochester": (43.1566, -77.6088),
    "san bernardino": (34.1083, -117.2898),
    "tacoma": (47.2529, -122.4443),
    "salt lake city": (40.7608, -111.8910),
    "slc": (40.7608, -111.8910),
    "des moines": (41.5868, -93.6250),
    "detroit": (42.3314, -83.0458),
    "savannah": (32.0809, -81.0912),
    "charleston": (32.7765, -79.9311),
    "asheville": (35.5951, -82.5515),
    "boulder": (40.0150, -105.2705),
    "ann arbor": (42.2808, -83.7430),
    "athens": (33.9519, -83.3576),
    "knoxville": (35.9606, -83.9207),
    "chattanooga": (35.0456, -85.3097),
    "roanoke": (37.2710, -79.9414),
    "harrisonburg": (38.4496, -78.8689),
    "lynchburg": (37.4138, -79.1422),
    "charlottesville": (38.0293, -78.4767),
    "blacksburg": (37.2296, -80.4139),
    "brooklyn": (40.6782, -73.9442),
    "manhattan": (40.7831, -73.9712),
    "queens": (40.7282, -73.7949),
    "bronx": (40.8448, -73.8648),
    "staten island": (40.5795, -74.1502),
    "hoboken": (40.7440, -74.0324),
    "williamsburg": (40.7081, -73.9571),
    "santa monica": (34.0195, -118.4912),
    "silver lake": (34.0869, -118.2702),
    "echo park": (34.0782, -118.2606),
    "hollywood": (34.0928, -118.3287),
    "west hollywood": (34.0900, -118.3617),
    "venice": (33.9850, -118.4695),
    "pasadena": (34.1478, -118.1445),
    "tempe": (33.4255, -111.9400),
    "berkeley": (37.8716, -122.2727),
    "santa cruz": (36.9741, -122.0308),
    "eugene": (44.0521, -123.0868),
    "boise": (43.6150, -116.2023),
    "columbia": (34.0007, -81.0348),
    "greenville": (34.8526, -82.3940),
    "wilmington": (34.2257, -77.9447),
    "providence": (41.8240, -71.4128),
    "hartford": (41.7658, -72.6734),
    "new haven": (41.3083, -72.9279),
    "burlington": (44.4759, -73.2121),
    "ithaca": (42.4440, -76.5019),
    "saratoga springs": (43.0831, -73.7846),
    "albany": (42.6526, -73.7562),
    "syracuse": (43.0481, -76.1474),
    "santa fe": (35.6870, -105.9378),
    "taos": (36.4072, -105.5731),
    "jackson": (32.2988, -90.1848),
    "little rock": (34.7465, -92.2896),
    "pensacola": (30.4213, -87.2169),
    "gainesville": (29.6516, -82.3248),
    "tallahassee": (30.4383, -84.2807),
    "st petersburg": (27.7676, -82.6403),
    "fort lauderdale": (26.1224, -80.1373),
    "west palm beach": (26.7153, -80.0534),
    "dayton": (39.7589, -84.1916),
    "akron": (41.0814, -81.5190),
    "youngstown": (41.0998, -80.6495),
    "springfield": (39.9242, -83.8088),
    "wichita": (37.6872, -97.3301),
    "sioux falls": (43.5446, -96.7311),
    "fargo": (46.8772, -96.7898),
    "duluth": (46.7867, -92.1005),
    "grand rapids": (42.9634, -85.6681),
    "lansing": (42.7325, -84.5555),
    "kalamazoo": (42.2917, -85.5872),
    "traverse city": (44.7631, -85.6206),
    "milwaukee": (43.0389, -87.9065),
    "madison": (43.0731, -89.4012),
    "eau claire": (44.8113, -91.4985),
    "missoula": (46.8721, -113.9940),
    "billings": (45.7833, -108.5007),
    "flagstaff": (35.1983, -111.6513),
    "sedona": (34.8697, -111.7610),
    "mobile": (30.6954, -88.0399),
    "huntsville": (34.7304, -86.5861),
    "montgomery": (32.3792, -86.3077),
    "myrtle beach": (33.6891, -78.8867),
    "hilton head": (32.2163, -80.7526),
    "key west": (24.5551, -81.7800),
    "napa": (38.2975, -122.2869),
    "sonoma": (38.2920, -122.4580),
    "paso robles": (35.6267, -120.6910),
    "newport": (41.4901, -71.3128),
    "cape cod": (41.6688, -70.2962),
    "portland me": (43.6591, -70.2568),
    "bar harbor": (44.3876, -68.2039),
    "bloomington": (39.1653, -86.5264),
    "lawrence": (38.9717, -95.2353),
}


def _normalize_city(city: str) -> str:
    """Normalize city name for lookup."""
    city = city.lower().strip()
    # Remove common suffixes
    for suffix in [", usa", ", us", ", united states"]:
        city = city.replace(suffix, "")
    city = city.strip().rstrip(",").strip()
    return city


def _lookup_city(city: str) -> dict:
    """Look up city in embedded database."""
    normalized = _normalize_city(city)

    # Direct match
    if normalized in US_CITIES:
        lat, lng = US_CITIES[normalized]
        return {"lat": lat, "lng": lng, "display_name": city}

    # Try without state
    parts = [p.strip() for p in normalized.split(",")]
    if len(parts) >= 1:
        city_only = parts[0]
        if city_only in US_CITIES:
            lat, lng = US_CITIES[city_only]
            return {"lat": lat, "lng": lng, "display_name": city}

    # Fuzzy: check if any key starts with or contains the city name
    for key, (lat, lng) in US_CITIES.items():
        if key.startswith(parts[0]) or parts[0] in key:
            return {"lat": lat, "lng": lng, "display_name": city}

    return None


async def _nominatim_geocode(city: str) -> dict:
    """Fallback geocoding via Nominatim."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": city, "format": "json", "limit": "1", "countrycodes": "us"},
                headers={"User-Agent": "PAM/1.0 (concert-discovery)"},
                timeout=10.0,
            )
            if resp.status_code == 200:
                results = resp.json()
                if results:
                    return {
                        "lat": float(results[0]["lat"]),
                        "lng": float(results[0]["lon"]),
                        "display_name": results[0].get("display_name", city),
                    }
    except Exception as e:
        logger.warning(f"Nominatim fallback failed: {e}")
    return None


async def geocode(city: str) -> dict:
    """Convert city name to lat/lng. Uses embedded DB first, Nominatim as fallback."""
    cache_key = city.lower().strip()
    if cache_key in _geo_cache:
        return _geo_cache[cache_key]

    # Try embedded database first
    result = _lookup_city(city)
    if result:
        _geo_cache[cache_key] = result
        return result

    # Fallback to Nominatim
    result = await _nominatim_geocode(city)
    if result:
        _geo_cache[cache_key] = result
        return result

    logger.warning(f"Could not geocode '{city}'")
    return None
