# Healthcare Intelligence v2

This version adds city search and more resilient hospital lookup. It searches public OpenStreetMap tags and can fall back to another Overpass endpoint. Public map tags do NOT confirm beds, oxygen, ventilators, specialists, opening status, or acceptance. Those remain unknown until verified through an authorized hospital integration.

## Start backend (terminal 1)
```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```
If you already have the backend venv, activate it and run `pip install -r requirements.txt` only if needed.

## Start frontend (terminal 2)
```powershell
cd frontend
npm install
npm run dev
```
Open the Vite URL shown in the terminal, usually http://localhost:5173.

## How to use
Choose a city (Coimbatore, Chennai, Madurai, Salem, Tiruchirappalli, Erode, Bengaluru, or another place), then search. You can also use GPS or enter coordinates. If the city lookup fails, the app reports that instead of silently pretending there are no hospitals.

## Data limits
OpenStreetMap is community-maintained and some hospitals or facility details may be missing. The recommendation score is a simple distance-based prototype, not trained/validated medical AI. Call the hospital/ambulance control room to verify suitability and current capacity. Do not delay emergency care to use this app.
