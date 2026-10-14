from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import httpx, math

app = FastAPI(title="Healthcare Intelligence API", version="0.2.0",
 description="Hospital discovery prototype. Public map data is not live clinical capacity data.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://healthcare-intelligence-eight.vercel.app"
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

class SearchRequest(BaseModel):
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    city: str | None = None
    radius_km: float = Field(default=15, ge=1, le=100)
    emergency_type: str = "General emergency"
    required_services: list[str] = []

def distance_km(a,b,c,d):
    r=6371
    p1,p2=math.radians(a),math.radians(c)
    dp=math.radians(c-a); dl=math.radians(d-b)
    x=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.asin(math.sqrt(x))

@app.get("/")
def root():
    return {"name":"Healthcare Intelligence API","status":"running","docs":"/docs",
            "notice":"Live clinical availability is unknown without a verified integration."}

@app.get("/api/health")
def health(): return {"status":"ok"}

async def geocode_city(client, city):
    try:
        r=await client.get(NOMINATIM, params={"q":city,"format":"jsonv2","limit":1,"countrycodes":"in"},
                           headers={"User-Agent":"HealthcareIntelligenceStudentPrototype/0.2 (educational project)"})
        r.raise_for_status(); data=r.json()
        if data: return float(data[0]["lat"]), float(data[0]["lon"]), data[0].get("display_name", city)
    except (httpx.HTTPError, ValueError, KeyError, IndexError): pass
    return None

@app.post("/api/hospitals/search")
async def search(req: SearchRequest):
    if req.city and req.city.strip():
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                geo=await geocode_city(client, req.city.strip())
        except httpx.HTTPError: geo=None
        if not geo:
            raise HTTPException(404, f"Could not find the location '{req.city}'. Try a city name such as Coimbatore or Chennai, or enter coordinates.")
        lat, lon, resolved_city=geo
    elif req.latitude is not None and req.longitude is not None:
        lat, lon, resolved_city=req.latitude, req.longitude, "Entered coordinates"
    else:
        raise HTTPException(422, "Enter a city name or provide both latitude and longitude.")

    radius=int(req.radius_km*1000)
    query=(f'[out:json][timeout:35];(nwr["amenity"="hospital"](around:{radius},{lat},{lon});'
           f'nwr["healthcare"="hospital"](around:{radius},{lat},{lon});'
           f'nwr["healthcare"="clinic"](around:{radius},{lat},{lon}););out center tags;')
    payload=None; last_error=None
    async with httpx.AsyncClient(
    timeout=20,
    headers={"User-Agent": "HealthcareIntelligenceStudentPrototype/0.2"}
) as client:
        for endpoint in OVERPASS_ENDPOINTS:
            try:
                resp=await client.post(endpoint, data={"data":query})
                resp.raise_for_status(); payload=resp.json(); break
            except (httpx.HTTPError, ValueError) as exc: last_error=exc
    if payload is None:
        raise HTTPException(502, "Public hospital map service is temporarily unavailable. Please retry in a minute; this does not mean there are no hospitals.") from last_error

    results=[]; seen=set()
    for el in payload.get("elements",[]):
        tags=el.get("tags",{}); name=tags.get("name") or tags.get("name:en")
        center=el.get("center",{}); hlat=el.get("lat",center.get("lat")); hlon=el.get("lon",center.get("lon"))
        if not name or hlat is None or hlon is None: continue
        key=name.strip().lower()
        if key in seen: continue
        seen.add(key)
        hlat,hlon=float(hlat),float(hlon); dist=distance_km(lat,lon,hlat,hlon)
        if dist > req.radius_km: continue
        addr=", ".join(v for v in [tags.get("addr:street"),tags.get("addr:suburb"),tags.get("addr:city"),tags.get("addr:postcode")] if v) or "Address not listed"
        mapped=[]
        if tags.get("emergency")=="yes": mapped.append("Emergency service tag listed (not live-verified)")
        spec=tags.get("healthcare:speciality") or tags.get("healthcare:specialty")
        if spec: mapped.append("Mapped specialty: "+str(spec))
        score=round(max(0,100-min(dist*2,80)),1)
        explanations=[f"Distance-based baseline: {dist:.2f} km straight-line distance.","Public map tags do not verify real-time capacity or patient acceptance."]
        results.append({"id":f'{el.get("type")}/{el.get("id")}',"name":name,"latitude":hlat,"longitude":hlon,
          "address":addr,"phone":tags.get("phone") or tags.get("contact:phone"),
          "osm_url":f'https://www.openstreetmap.org/{el.get("type")}/{el.get("id")}',
          "mapped_services":mapped,"distance_km":round(dist,2),"score":score,"score_explanation":explanations,
          "availability_status":"Unknown — not verified","live_capacity_status":"No live hospital capacity integration"})
    results.sort(key=lambda h:(h["distance_km"],-h["score"],h["name"].lower()))
    return {"count":len(results),"resolved_location":resolved_city,"center":{"latitude":lat,"longitude":lon},
      "source":"OpenStreetMap / Overpass API","data_notice":"Community map data may be incomplete. Live beds, oxygen, ventilators, specialist availability and hospital acceptance are unknown.",
      "recommendation_method":"Distance-based prototype ranking; not a trained or clinically validated model.","hospitals":results}
