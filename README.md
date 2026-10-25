# WindWatch – UK wind forecast monitor

Web app for a day-ahead power buying team. It shows (1) the latest wind forecast available at decision time and (2) how accurate those forecasts have been, using Elexon FUELHH (actuals) and WINDFOR (forecasts) for January 2026.

**Live app:** <[ADD VERCEL LINK](https://windwatch-irf2.vercel.app/)>
**Demo video:** <[ADD YOUTUBE LINK](https://youtu.be/W4TBmBLq-78)>

## AI tools used
Claude (Anthropic) was used to help write and review parts of this code, and I checked and tested the result.

## Key idea
For a target half-hour T on day D, the buyer decides on D-1 around 09:00. So the "decision forecast" for T is the **latest forecast with publishTime <= D-1 09:00**. The decision time is adjustable in the UI. Error = actual - forecast (negative means wind fell short).

## Files
- `scripts/fetch_data.py` – downloads Elexon data into `data/` (run once)
- `data/actuals.csv`, `data/forecasts.csv` – saved snapshot (forecasts limited to horizon 0-48h)
- `api/index.py` – FastAPI backend: data loading, analysis (decision forecast, error metrics), routes
- `frontend/` – React (Vite) app: Decision view and Accuracy tab, charts with Recharts
- `Dockerfile.backend`, `frontend/Dockerfile`, `docker-compose.yml` – Docker setup
- `vercel.json` – Vercel config (static frontend + Python function)

## Run
1. `pip install -r requirements.txt && python scripts/fetch_data.py` (skip if `data/*.csv` already exist)
2. Docker: `docker compose up --build` then open http://localhost:3000
3. Without Docker: `uvicorn api.index:app --port 8000` and in `frontend/`: `npm install && npm run dev`

## API
`/api/meta`, `/api/decision?date=2026-01-15&cutoff_hour=9`, `/api/accuracy?cutoff_hour=9`, `/api/horizon`

## Deploy
`npm i -g vercel && vercel --prod` from the repo root.
