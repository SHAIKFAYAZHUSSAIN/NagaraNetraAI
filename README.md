# CityFlow

## Urban traffic flow and incident intelligence

CityFlow is a planned software-only traffic decision-support application for NeuraX Hackathon. Using organizer-provided data, it will detect unusual congestion, forecast speeds 15–60 minutes ahead, recommend feasible diversions and compare infrastructure interventions. All actions remain advisory or simulated.

## Checkpoint 01 status

Completed: problem analysis, dataset inspection, architecture and an 18-hour implementation plan. Application code, trained models and deployment are not yet implemented or verified. This package contains documentation, not a runnable application. See [APPROACH.md](APPROACH.md) for the technical approach.

## Selected free stack

| Layer | Technology | Purpose |
| --- | --- | --- |
| Frontend | Next.js, React, TypeScript, Tailwind CSS | Dashboard and typed API integration |
| Maps | Leaflet and React Leaflet | Network and route overlays |
| Charts | Recharts | Forecast and scenario charts |
| Backend | Python 3.12, FastAPI, Uvicorn | JSON endpoints and inference |
| Data | pandas, NumPy, PyArrow | Preparation and partitioned Parquet files |
| ML | XGBoost, scikit-learn | CPU forecasting, baselines and metrics |
| Network | NetworkX | Directed, turn-aware routing |
| Database | None initially | Read-only local artifacts |
| LLM/RAG | None initially | Evidence-based template explanations |
| Frontend hosting | Vercel Hobby, if eligible | Free personal, non-commercial hosting |
| API hosting | Render Free | Small demonstration backend |

The selected software does not require paid software licenses for this implementation. Hosting is free only within eligibility and usage limits. This is a practical selection for the chosen stack, not a guarantee of universally best accuracy or performance.

## Dataset findings

The network contains 436 directed segments and 120 nodes. Traffic resolution is five minutes.

| Files | Contents and use |
| --- | --- |
| traffic_train.csv | 1,883,520 observations, January 1–15, 2026; training/history |
| traffic_validation.csv | 502,272 observations, January 16–19; final evaluation |
| forecast_targets_train.csv and forecast_targets_validation.csv | Labels for speed, flow and congestion at 15/30/45/60 minutes; never input features |
| incidents_train.csv and incidents_validation.csv | 49 training and 11 validation incidents; labels/evaluation |
| context_train.csv and context_validation.csv | Weather, events and calendar context |
| network.csv and nodes.csv | Directed connectivity, capacities, attributes and coordinates |
| roadworks_train.csv and roadworks_validation.csv | Work intervals and closure fractions |
| turn_restrictions.csv | 61 segment-transition restrictions |
| planning_candidates.csv | 90 interventions with capacity changes and cost indices |
| od_demand_profiles.csv | Origin/destination demand for an optional reassignment extension |
| signal_plans.csv | Junction timing context |
| scenario_examples.csv | 30 incident example windows |

Both traffic files were timestamp-sorted with no missing cells, duplicate timestamp/segment keys, negative numeric values or sensor_quality below 1. This does not establish that every value is correct. The manifest lists noise types, so robustness handling remains necessary for hidden tests.

## Minimum product

1. Operations: replay time, colored network, road details, suspected incidents, four speed forecasts and a diversion comparison.
2. Planning: recurring bottlenecks and a supplied capacity-upgrade comparison.
3. Evaluation: horizon errors versus persistence, incident metrics and robustness results.

Map links connect supplied node coordinates; they are dataset network links, not verified street shapes. Preserve an offline network-only view using x/y coordinates.

## Architecture

```text
Organizer CSVs -> local preparation -> partitioned Parquet
Training labels -> local XGBoost training -> JSON/UBJ models

Next.js browser UI on Vercel
           | HTTPS JSON
           v
FastAPI on Render
  -> bounded snapshots and history
  -> detection and forecast inference
  -> NetworkX routing and scenario calculations
  -> compact read-only data/model artifacts
```

Train locally. Never train on API requests or load all raw CSVs on each request. Load compact models once and only needed data partitions. Label hosted demo-window limits explicitly; keep complete evaluation locally. Both frontend and API must also run on a laptop.

## Setup

Install Node.js 24 LTS, Python 3.12, Git and VS Code. Scaffold the frontend once from the project root:

```powershell
npx create-next-app@latest frontend --ts --tailwind --eslint --app --src-dir --use-npm
cd frontend
npm install leaflet react-leaflet recharts
npm install -D @types/leaflet
```

Commit package-lock.json; teammates use npm ci after cloning. Next.js already uses React. Load Leaflet through a browser-only component, dynamically imported with server rendering disabled from a Client Component, and include Leaflet CSS.

From the repository root, create the backend:

```powershell
mkdir backend
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install fastapi "uvicorn[standard]" pandas numpy pyarrow xgboost scikit-learn networkx pydantic-settings pytest httpx
```

Record tested versions in backend/requirements.txt. Copy organizer files into data/raw/ at the root, outside frontend/public/. Keep originals and follow organizer redistribution rules.

### Planned environment configuration

frontend/.env.local:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

backend/.env:

```dotenv
CORS_ORIGINS=["http://localhost:3000"]
DATA_DIR=../data/processed
MODEL_DIR=../models
```

Implement loading with pydantic-settings and env_file=".env" when starting from backend/. Configure FastAPI CORSMiddleware with explicit origins. NEXT_PUBLIC_ values are public, never secrets. Commit sanitized .env.example files and ignore local environment files, raw data and virtual environments.

After implementing the code, run separate terminals:

```powershell
# Inside backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

```powershell
# Inside frontend
npm run dev
```

Expected endpoints after implementation: http://localhost:3000, http://127.0.0.1:8000/health and http://127.0.0.1:8000/docs. They are not supplied by this documentation alone.

## Free deployment

### Render

- Create a Free Python web service with root directory backend.
- Build command: pip install -r requirements.txt.
- Start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1.
- Implement /health and configure it as the health-check path.
- Bundle compact, permitted artifacts under backend/artifacts/data and backend/artifacts/models.
- Set DATA_DIR=artifacts/data and MODEL_DIR=artifacts/models.
- Set CORS_ORIGINS to a JSON list of exact frontend origins. Add preview origins explicitly when needed.
- Measure memory usage and verify real snapshot/forecast requests before judging.

Free services sleep after 15 idle minutes and can take about a minute to wake. Runtime filesystem changes are ephemeral. Bundle artifacts for each deployment; runtime uploads are not durable storage. Train locally and start with one worker.

### Vercel

- Select an eligible repository, root directory frontend and the Next.js preset.
- Set NEXT_PUBLIC_API_BASE_URL to the Render HTTPS URL before building.
- Run npm run build locally; deploy and verify browser-to-API requests.
- Rebuild after changing the public API URL.

Hobby is restricted to personal, non-commercial use. Check eligibility and repository restrictions: Vercel documents that Hobby cannot connect Git-organization-owned repositories. Use a permitted personal repository with collaborators if appropriate; do not share credentials.

Verify the hosted API before presenting and retain local execution as a fallback. No hosting setup has been performed for this documentation task.

### Basemap

Leaflet requires no API key. Optional OpenStreetMap standard tiles are best-effort shared infrastructure: keep attribution visible and obey the tile policy. Do not bulk-download tiles for offline use. The supplied coordinates support a network-only fallback.

## Planned repository

```text
cityflow/
  README.md
  APPROACH.md
  frontend/
    src/app/
    src/components/
    src/lib/api.ts
    package.json
    package-lock.json
    .env.example
  backend/
    app/main.py
    app/schemas.py
    app/services/
    artifacts/data/
    artifacts/models/
    requirements.txt
    .env.example
  scripts/
    prepare_data.py
    train_forecasts.py
    evaluate.py
  data/raw/
  data/processed/
  models/
  reports/
```

## Team and schedule

| Member | Ownership | First handoff |
| --- | --- | --- |
| Sohana | Next.js, Leaflet, charts and Vercel | UI against agreed sample API responses |
| Jithendra | FastAPI, preparation, detection and Render | Health/snapshot endpoints and alert rules |
| Bhavana | XGBoost, inference and evaluation | Saved models, inference wrapper and horizon errors |
| Fayaz | NetworkX, planning and integration tests | Legal diversion and capacity comparison |

Sohana and Jithendra own the API contract. Bhavana and Fayaz supply callable modules so Jithendra does not implement every algorithm. Each member maintains their module documentation.

| Hours | Milestone |
| --- | --- |
| 0–1 | Setup, repository, interfaces and demo window |
| 1–4 | UI shell, health/snapshot API, baseline and graph; deploy basic services early |
| 4–6 | Real browser/API integration and CORS verified |
| 6–10 | All core features connected |
| 10–13 | Evaluation, robustness and hosted memory checks |
| 13–15 | Freeze features, fix defects, finish documentation |
| 15–17 | Demo rehearsal and local fallback |
| 17–18 | Submission and contingency |

If behind, retain baseline forecasts, one diversion and one planning comparison. At least one member must remain at the venue throughout the event; arrange explicit handoffs for breaks and follow organizer checkpoint instructions.

## References

Hosting/setup guidance checked September 19, 2026. Verify eligibility and limits before deployment.

- [Next.js setup](https://nextjs.org/docs/app/getting-started/installation)
- [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/)
- [XGBoost parameters](https://xgboost.readthedocs.io/en/stable/parameter.html)
- [Vercel Hobby](https://vercel.com/docs/plans/hobby)
- [Vercel limits](https://vercel.com/docs/limits)
- [Render Free](https://render.com/docs/free)
- [OpenStreetMap tile policy](https://operations.osmfoundation.org/policies/tiles/)
