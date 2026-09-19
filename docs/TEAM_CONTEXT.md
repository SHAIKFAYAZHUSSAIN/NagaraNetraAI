# CityFlow — Team Context & Operations Guide

## Project
**CityFlow — Urban Traffic Flow & Incident Intelligence**

CityFlow is a software-only traffic decision-support application built for the NeuraX Hackathon. Utilizing organizer-provided network and traffic sensor datasets, CityFlow detects anomalous congestion, forecasts corridor speeds 15–60 minutes ahead, recommends turn-compliant diversion routes, and evaluates infrastructure capacity interventions.

---

## Team & Responsibilities

| Team Member | Core Focus & Responsibilities | Key Handoffs |
| :--- | :--- | :--- |
| **Sohana** | **Frontend Engineering & Hosting**<br>• Next.js (App Router, React, TypeScript, Tailwind CSS)<br>• Leaflet & React Leaflet mapping (client-only dynamic rendering, coordinate fallback)<br>• Recharts forecast curve and history visualizations<br>• Typed API client matching backend Pydantic schemas<br>• Vercel Hobby continuous deployment | Interactive UI shell hooked to mock/real API responses; error and loading state handling |
| **Jithendra**| **Data Preparation, API Core & Hosting**<br>• Raw CSV ingestion, 5-minute grid reindexing, and Parquet partitioning<br>• FastAPI server setup, lifespan artifact loading, and Uvicorn runner<br>• Rule-based incident detection engine with trigger evidence generation<br>• CORS middleware configuration for local and Vercel origins<br>• Render Free Web Service deployment with `/health` monitor | Clean Parquet tables; runnable FastAPI service; validated health, snapshot, history, and alert endpoints |
| **Bhavana**  | **Machine Learning & Model Evaluation**<br>• XGBoost multi-horizon regressors (`target_speed_15m/30m/45m/60m`)<br>• Baseline Persistence model implementation and comparison<br>• Feature engineering (past-only lags, rolling statistics, context features)<br>• Offline local training pipeline (`scripts/train_forecasts.py`)<br>• Model serialization (JSON/UBJ) and standalone inference module<br>• Formal evaluation reporting (MAE vs persistence on validation split) | Serialized model files in `models/`; Python inference wrapper for FastAPI; benchmark metrics table |
| **Fayaz**    | **Network Analysis, Routing & Integration**<br>• NetworkX directed graph construction from nodes and segment links<br>• Strict turn-restriction enforcement (`no_turn`, `no_left`, conservative time windows)<br>• Active roadwork closure fraction application<br>• Diversion route generator with travel time and capacity checks<br>• Infrastructure planning candidate evaluator (BPR volume-delay formula)<br>• End-to-end integration and smoke test suite | Callable NetworkX routing/planning module; route verification tests; candidate evaluation function |

---

## Current Status

**Status**: **Checkpoint 1 documentation and architecture stage.**
Problem analysis, dataset inspection, technical architecture, and implementation planning are complete. Application code, trained models, and cloud deployments are not yet verified.

---

## Locked Stack

The technology stack is locked to maintain focus, eliminate license barriers, and ensure seamless interoperability within free-tier resource limits:

- **Frontend**: Next.js, React, TypeScript, Tailwind CSS
- **Maps**: Leaflet (with React Leaflet)
- **Charts**: Recharts
- **Backend**: Python 3.12, FastAPI, Uvicorn
- **Data**: pandas, NumPy, PyArrow, Parquet
- **Machine Learning**: XGBoost (`tree_method="hist"`), scikit-learn
- **Network**: NetworkX
- **Database**: **None initially** (Immutable partitioned Parquet files and local serialized model files)
- **LLM / RAG**: **None initially** (Evidence-based deterministic explanation templates)
- **Hosting**: Vercel (Frontend) + Render (Backend)

---

## Important Rule

> **CRITICAL RULE**:
> The problem statement, dataset analysis, [README.md](../README.md), and [APPROACH.md](../APPROACH.md) are the single source of truth.
>
> Any architecture, API, or data-schema change must be explicitly documented and communicated to all four team members before implementation begins.

---

## 18-Hour Implementation Milestones

```
+-----------------------------------------------------------------------------------------+
| H 0-1   | Setup, repository structure, API contracts, team alignment                    |
| H 1-4   | UI shell, baseline models, graph parser, health/snapshot API; initial deploys |
| H 4-6   | Live browser-to-API integration; verify CORS and data flow                   |
| H 6-10  | All core features connected (forecasts, diversions, planning evaluations)    |
| H 10-13 | System evaluation, robustness testing, Render hosted memory profiling         |
| H 13-15 | Feature freeze; bug fixes; documentation completion                           |
| H 15-17 | Demo rehearsal; contingency verification (offline/local fallback)             |
| H 17-18 | Final submission packaging and buffer                                         |
+-----------------------------------------------------------------------------------------+
```

---

## Known Constraints & Assumptions

1. **Render Free Tier Resource Ceiling**:
   - Web service provides 512 MB RAM. Exceeding this triggers SIGKILL.
   - Mitigation: Run a single Uvicorn worker (`--workers 1`). Do not hold raw CSVs in memory; slice pre-partitioned Parquet files on demand. Package only demonstration-window data under `backend/artifacts/data/`.
   - Free services sleep after 15 minutes of inactivity (50–60 second wake-up latency). The frontend must show explicit cold-start loading indicators.
2. **Vercel Hobby Tier Boundaries**:
   - Restricted to personal, non-commercial hackathon use.
   - Do not attempt to link Git organization accounts if prohibited by Hobby rules.
3. **Turn Restriction Data Limits**:
   - `turn_restrictions.csv` contains rows with `time_window` restrictions that omit explicit hour boundaries.
   - Decision: Conservatively enforce them as active (permanently blocked) movements and document this assumption explicitly in routing output.
4. **Map Coordinates vs Real Streets**:
   - Provided coordinates $(x, y)$ in `nodes.csv` are synthetic/dataset connections, not verified geographical OpenStreetMap road geometries.
   - Decision: Treat links as topological connections. Ensure the Leaflet view renders vector links between nodes cleanly even when internet tile access is unavailable.
5. **Small Ground-Truth Incident Count**:
   - Training split contains only 49 incidents; validation has 11.
   - Decision: Limit detection to binary suspected incidents. Do not attempt multi-class cause classification with unvalidated statistical significance.
6. **Fixed-Demand Planning Assumption**:
   - Infrastructure candidate evaluation uses local volume-delay relationships with constant demand.
   - Decision: Clearly disclose in UI and API output that planning estimates are local fixed-demand approximations, not citywide equilibrium traffic assignments.

---

## Important Architectural Decisions

- **Local CPU Training Only**: All XGBoost models are trained locally on developer machines and serialized to JSON/UBJ. The backend web server strictly performs read-only inference.
- **Persistence Model Benchmark**: Always evaluate and display the Persistence baseline ($v_{t+h} = v_t$). If XGBoost underperforms Persistence at a given horizon, fall back to Persistence.
- **Deterministic Alert Advisories**: Incident alerts generate advisories via structured string interpolation using observed quantitative anomalies (e.g. `speed_drop_pct`, `queue_m`).
- **No Active Database**: Eliminating PostgreSQL/MongoDB simplifies local setup, eliminates connection pooling bugs, and fits within hosting memory limits.

---

## Pending Work & Immediate Next Steps (Hours 1–4)

### Sohana (Frontend)
- [ ] Scaffold Next.js application in `frontend/` using TypeScript, Tailwind CSS, and App Router.
- [ ] Install `leaflet`, `react-leaflet`, `recharts`, and `@types/leaflet`.
- [ ] Create `src/lib/api.ts` defining all TypeScript interfaces from [API_CONTRACT.md](API_CONTRACT.md).
- [ ] Implement client-side dynamic Leaflet container (`ssr: false`) with sample node markers and segment polylines.
- [ ] Connect initial UI to mock data matching API schemas and verify basic build (`npm run build`).

### Jithendra (Backend & Data)
- [ ] Create Python 3.12 virtual environment and setup `backend/requirements.txt`.
- [ ] Implement `scripts/prepare_data.py` to index raw CSVs to 5-minute grids and output partitioned Parquet in `data/processed/`.
- [ ] Scaffold FastAPI in `backend/app/main.py` with `CORSMiddleware` and `pydantic-settings`.
- [ ] Implement `GET /health`, `GET /network`, and `GET /traffic` endpoints.
- [ ] Verify Render deployment builds and responds at `/health`.

### Bhavana (ML & Forecasting)
- [ ] Build baseline persistence forecast function.
- [ ] Implement feature extraction script (`past lags`, `rolling means`, `hour`, `dayofweek`, `lanes`, `capacity`).
- [ ] Train preliminary 4-horizon XGBoost models (`target_speed_15m/30m/45m/60m`) via `scripts/train_forecasts.py`.
- [ ] Export model artifacts to `models/` in JSON format with metadata.
- [ ] Package standalone inference function `predict_speed(segment_id, timestamp)`.

### Fayaz (Routing & Network)
- [ ] Implement network loader script building a NetworkX `DiGraph` from `nodes.csv` and `network.csv`.
- [ ] Implement turn-restriction filter based on `turn_restrictions.csv`.
- [ ] Implement shortest-path routing algorithm with dynamic travel times derived from segment speeds.
- [ ] Implement candidate evaluation logic applying capacity deltas from `planning_candidates.csv`.
- [ ] Write initial pytest unit tests verifying restricted turns are never routed.
