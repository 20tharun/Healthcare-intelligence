from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx
import math


# --------------------------------------------------
# Configuration
# --------------------------------------------------

NOMINATIM = "https://nominatim.openstreetmap.org/search"

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

USER_AGENT = "HealthcareIntelligenceStudentPrototype/1.0"


# --------------------------------------------------
# FastAPI application
# --------------------------------------------------

app = FastAPI(
    title="Healthcare Intelligence API",
    version="1.0.0",
    description=(
        "Hospital discovery prototype using public "
        "OpenStreetMap data. Live clinical capacity "
        "is not verified by this application."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://healthcare-intelligence-eight.vercel.app",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Request model
# --------------------------------------------------

class SearchRequest(BaseModel):
    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
    )

    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
    )

    city: str | None = None

    radius_km: float = Field(
        default=15,
        ge=1,
        le=100,
    )

    emergency_type: str = "General emergency"

    required_services: list[str] = Field(
        default_factory=list,
    )


# --------------------------------------------------
# Distance calculation
# --------------------------------------------------

def distance_km(lat1, lon1, lat2, lon2):
    earth_radius = 6371.0

    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    a = max(0.0, min(1.0, a))

    return 2 * earth_radius * math.asin(math.sqrt(a))


# --------------------------------------------------
# Basic endpoints
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "name": "Healthcare Intelligence API",
        "status": "running",
        "docs": "/docs",
        "health": "/api/health",
        "notice": (
            "Live hospital capacity and patient "
            "acceptance are not verified."
        ),
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


# --------------------------------------------------
# Convert city name into coordinates
# --------------------------------------------------

async def geocode_city(
    client: httpx.AsyncClient,
    city: str,
):
    try:
        response = await client.get(
            NOMINATIM,
            params={
                "q": city,
                "format": "jsonv2",
                "limit": 1,
                "countrycodes": "in",
            },
            headers={
                "User-Agent": USER_AGENT,
            },
        )

        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list) or not data:
            return None

        latitude = float(data[0]["lat"])
        longitude = float(data[0]["lon"])
        display_name = data[0].get("display_name", city)

        return latitude, longitude, display_name

    except (
        httpx.HTTPError,
        ValueError,
        KeyError,
        IndexError,
        TypeError,
    ):
        return None


# --------------------------------------------------
# Search public map data for hospitals and clinics
# --------------------------------------------------

@app.post("/api/hospitals/search")
async def search(req: SearchRequest):

    # Step 1: Resolve the search location.

    if req.city and req.city.strip():

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(12.0),
                headers={"User-Agent": USER_AGENT},
            ) as client:
                geo = await geocode_city(
                    client,
                    req.city.strip(),
                )

        except httpx.HTTPError:
            geo = None

        if geo is None:
            if (
                req.latitude is not None
                and req.longitude is not None
            ):
                lat = req.latitude
                lon = req.longitude
                resolved_city = "Entered coordinates"
            else:
                raise HTTPException(
                    status_code=502,
                    detail=(
                        "The public geocoding service is "
                        "temporarily unavailable or could "
                        "not find this city. Try again or "
                        "provide latitude and longitude."
                    ),
                )
        else:
            lat, lon, resolved_city = geo

    elif (
        req.latitude is not None
        and req.longitude is not None
    ):
        lat = req.latitude
        lon = req.longitude
        resolved_city = "Entered coordinates"

    else:
        raise HTTPException(
            status_code=422,
            detail=(
                "Enter a city name or provide both "
                "latitude and longitude."
            ),
        )

    # Step 2: Build a valid Overpass query.

    radius_meters = int(req.radius_km * 1000)

    query = (
        '[out:json][timeout:20];('
        f'nwr["amenity"="hospital"]'
        f'(around:{radius_meters},{lat},{lon});'
        f'nwr["healthcare"="hospital"]'
        f'(around:{radius_meters},{lat},{lon});'
        f'nwr["healthcare"="clinic"]'
        f'(around:{radius_meters},{lat},{lon});'
        ');out center tags;'
    )

    # Step 3: Try the public map endpoints.

    payload = None
    last_error = None

    timeout = httpx.Timeout(
        20.0,
        connect=8.0,
    )

    async with httpx.AsyncClient(
        timeout=timeout,
        headers={"User-Agent": USER_AGENT},
    ) as client:

        for endpoint in OVERPASS_ENDPOINTS:
            try:
                response = await client.post(
                    endpoint,
                    data={"data": query},
                )

                response.raise_for_status()

                data = response.json()

                if not isinstance(data, dict):
                    raise ValueError(
                        "Unexpected map service response"
                    )

                if not isinstance(
                    data.get("elements", []),
                    list,
                ):
                    raise ValueError(
                        "Invalid hospital records response"
                    )

                payload = data
                break

            except (
                httpx.HTTPError,
                ValueError,
            ) as exc:
                last_error = exc
                print(
                    f"Map endpoint failed: {endpoint} "
                    f"({type(exc).__name__}: {exc})",
                    flush=True,
                )

    if payload is None:
        raise HTTPException(
            status_code=502,
            detail=(
                "Public hospital map services are "
                "temporarily unavailable. Please retry "
                "later. This does not mean that no "
                "hospitals exist in the area."
            ),
        ) from last_error

    # Step 4: Process hospital and clinic records.

    results = []
    seen = set()

    for element in payload.get("elements", []):
        tags = element.get("tags") or {}

        name = tags.get("name") or tags.get("name:en")

        center = element.get("center") or {}

        hospital_lat = element.get(
            "lat",
            center.get("lat"),
        )

        hospital_lon = element.get(
            "lon",
            center.get("lon"),
        )

        if (
            not name
            or hospital_lat is None
            or hospital_lon is None
        ):
            continue

        try:
            hospital_lat = float(hospital_lat)
            hospital_lon = float(hospital_lon)
        except (TypeError, ValueError):
            continue

        distance = distance_km(
            lat,
            lon,
            hospital_lat,
            hospital_lon,
        )

        if distance > req.radius_km:
            continue

        unique_key = (
            element.get("type"),
            element.get("id"),
        )

        if unique_key in seen:
            continue

        seen.add(unique_key)

        address_parts = [
            tags.get("addr:street"),
            tags.get("addr:suburb"),
            tags.get("addr:city"),
            tags.get("addr:postcode"),
        ]

        address = ", ".join(
            str(part)
            for part in address_parts
            if part
        ) or "Address not listed"

        mapped_services = []

        if tags.get("emergency") == "yes":
            mapped_services.append(
                "Emergency service tag listed; "
                "not live-verified"
            )

        specialty = (
            tags.get("healthcare:speciality")
            or tags.get("healthcare:specialty")
        )

        if specialty:
            mapped_services.append(
                f"Mapped specialty: {specialty}"
            )

        score = round(
            max(
                0,
                100 - min(distance * 2, 80),
            ),
            1,
        )

        explanations = [
            (
                f"Distance-based ranking: "
                f"{distance:.2f} km straight-line distance."
            ),
            (
                "Public map data does not verify "
                "real-time capacity or patient acceptance."
            ),
        ]

        element_type = element.get("type")
        element_id = element.get("id")

        results.append(
            {
                "id": f"{element_type}/{element_id}",
                "name": name,
                "latitude": hospital_lat,
                "longitude": hospital_lon,
                "address": address,
                "phone": (
                    tags.get("phone")
                    or tags.get("contact:phone")
                ),
                "osm_url": (
                    "https://www.openstreetmap.org/"
                    f"{element_type}/{element_id}"
                ),
                "mapped_services": mapped_services,
                "distance_km": round(distance, 2),
                "score": score,
                "score_explanation": explanations,
                "availability_status": (
                    "Unknown — not verified"
                ),
                "live_capacity_status": (
                    "No live hospital capacity integration"
                ),
            }
        )

    # Step 5: Sort results by distance.

    results.sort(
        key=lambda hospital: (
            hospital["distance_km"],
            -hospital["score"],
            hospital["name"].lower(),
        )
    )

    # Step 6: Return the response expected by the frontend.

    return {
        "count": len(results),
        "resolved_location": resolved_city,
        "center": {
            "latitude": lat,
            "longitude": lon,
        },
        "source": "OpenStreetMap / Overpass API",
        "data_notice": (
            "Community map data may be incomplete. "
            "Live beds, oxygen, ventilators, specialist "
            "availability and hospital acceptance are "
            "unknown unless confirmed by a verified "
            "hospital integration."
        ),
        "recommendation_method": (
            "Distance-based prototype ranking; not a "
            "trained or clinically validated model."
        ),
        "hospitals": results,
    }