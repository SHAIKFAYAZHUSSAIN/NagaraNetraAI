# CityFlow — System Architecture

## 1. System Overview

**CityFlow** is an advisory urban traffic flow and incident intelligence application developed for the NeuraX Hackathon. It ingests traffic sensor observations and road network topology, detects unusual congestion anomalies, predicts short-term segment speeds (15–60 minutes ahead), computes turn-compliant diversion routes, and evaluates infrastructure capacity interventions.

The system is architected as a lightweight, decoupled web application composed of a **Next.js (React/TypeScript)** frontend and a **FastAPI (Python 3.12)** backend, underpinned by local data preparation pipelines, local machine learning training, and in-memory graph models.

```
+-------------------------------------------------------------------------------+
|                                Offline Pipelines                              |
|                                                                               |
|  Organizer CSVs (Raw Data)                                                    |
|         │                                                                     |
|         ▼ [scripts/prepare_data.py]                                           |
|  Partitioned Parquet Files (data/processed/) ──┐                              |
|         │                                      │                              |
|         ▼ [scripts/train_forecasts.py]         │                              |
|  Trained Models & Metadata (models/*.json) ────┤                              |
+────────────────────────────────────────────────┼──────────────────────────────+
                                                 │
                                                 ▼ (Packaged Artifacts)
+-------------------------------------------------------------------------------+
|                            Backend Service (Render)                           |
|                                                                               |
|  FastAPI + Uvicorn (app/main.py)                                              |
|  ├── In-Memory NetworkX Graph (nodes, directed segments, turn restrictions)   |
|  ├── Read-Only Parquet Data Store (PyArrow / pandas slice engine)             |
|  ├── XGBoost CPU Inference Engine (4 horizon regressors: 15m, 30m, 45m, 60m)  |
|  ├── Incident Detection Service (threshold & rolling anomaly engine)          |
|  └── Diversion & Planning Evaluator (turn-aware routing & BPR/delay functions)|
+───────────────────────────────────────────────────────────────────────────────+
                                       ▲
                                       │ HTTPS / JSON (REST)
                                       ▼
+-------------------------------------------------------------------------------+
|                            Frontend Client (Vercel)                           |
|                                                                               |
|  Next.js 14+ (App Router, React, TypeScript, Tailwind CSS)                   |
|  ├── Leaflet / React Leaflet (Map overlays, offline node-to-node topology)    |
|  ├── Recharts (Speed trend history & 4-horizon forecast curves)               |
|  ├── Operations Dashboard (Replay selector, segment inspector, alert panel)   |
|  └── Planning & Evaluation Studio (Intervention comparison & error metrics)   |
+-------------------------------------------------------------------------------+
```

---

## 2. Technology Stack

| Layer | Component | Selection | Architectural Rationale |
| :--- | :--- | :--- | :--- |
| **Frontend UI** | Framework | Next.js (React, TypeScript) | Component-driven architecture, static asset bundling, type safety with backend schemas. |
| **Styling** | CSS Utility | Tailwind CSS | Rapid, modern UI development with utility classes. |
| **Mapping** | Geospatial Engine | Leaflet & React Leaflet | Lightweight client-rendered vector/overlay map. Runs with OpenStreetMap tiles or standalone node-coordinate fallback without external API keys. |
| **Charts** | Data Visualization | Recharts | Reactive SVG charts for forecast curves, residuals, and bottleneck distributions. |
| **Backend API** | Web Framework | FastAPI (Python 3.12) | High-performance asynchronous JSON endpoints, automatic OpenAPI documentation, native Pydantic validation. |
| **Server** | ASGI Server | Uvicorn | Production-standard ASGI runner; configured with single worker for free-tier memory safety. |
| **Data Engine** | Tabular Processing | pandas, NumPy, PyArrow | Fast vectorized feature calculations, reindexing, and efficient columnar Parquet queries. |
| **Storage Format**| File Format | Partitioned Apache Parquet | Snappy-compressed columnar storage partitioned by date/segment for low-latency range queries without an active database. |
| **Machine Learning**| Forecasting & Baselines | XGBoost (`XGBRegressor`), scikit-learn | Fast histogram-based gradient boosting (`tree_method="hist"`) optimized for CPU inference. Scikit-learn for evaluation metrics and preprocessing. |
| **Graph Network** | Routing Engine | NetworkX | Directed graph modeling of nodes, segment connectivity, and turn penalty/restriction logic. |
| **Database** | Database Engine | **None initially** | Read-only local file artifacts suffice for hackathon scope. Eliminates connection pool overhead, latency, and hosting complexity. |
| **LLM / RAG** | Explanations | **None initially** | Evidence-based deterministic templates ensure zero hallucination, zero API costs, and sub-millisecond explanation generation. |
| **Frontend Host** | Static/SSR Hosting | Vercel (Hobby Tier) | Free tier deployment with automated Git integration. |
| **Backend Host** | Container/App Hosting | Render (Free Web Service) | Free container hosting with custom health check support. |

---

## 3. Component Architecture & Data Flow

### 3.1 Data Preparation Pipeline (`scripts/prepare_data.py`)
- **Inputs**: Raw organizer CSV files located in `data/raw/` (`traffic_train.csv`, `traffic_validation.csv`, `context_*.csv`, `network.csv`, `nodes.csv`, `roadworks_*.csv`, `turn_restrictions.csv`).
- **Processing**:
  - Validates `(timestamp, segment_id)` composite primary keys.
  - Reindexes temporal observations to a strict 5-minute grid per segment. Missing readings are preserved with explicit quality indicators; no future data is ever backward-filled.
  - Joins contextual weather and event data strictly on `timestamp`.
  - Joins road geometry, capacity, and lane counts on `segment_id`.
  - Computes past-only lags (5, 15, 30 minutes) and rolling means.
  - Casts numerical features to `float32` to minimize memory footprint.
- **Outputs**: Partitioned Parquet tables in `data/processed/` partitioned by date ranges.

### 3.2 Forecasting Pipeline (`scripts/train_forecasts.py`)
- **Training Strategy**:
  - Local CPU execution using XGBoost histogram algorithm (`tree_method="hist"`).
  - Four distinct models are trained for the 4 forecast horizons:
    - Horizon 15m (`target_speed_15m`)
    - Horizon 30m (`target_speed_30m`)
    - Horizon 45m (`target_speed_45m`)
    - Horizon 60m (`target_speed_60m`)
  - Target labels (`forecast_targets_train.csv`) are used strictly as training ground truth and are purged before feature extraction to eliminate data leakage.
  - A baseline **Persistence Model** ($v_{t+h} = v_t$) is fitted and evaluated as an essential benchmark.
- **Artifact Serialization**:
  - Models exported as standard XGBoost JSON / Universal Binary JSON (`.ubj`) files.
  - Feature ordering lists and normalization parameters saved alongside model artifacts in `models/` or `backend/artifacts/models/`.

### 3.3 Routing & Planning Engine (NetworkX)
- **Graph Topology**:
  - Built as a directed graph $\mathcal{G} = (\mathcal{V}, \mathcal{E})$ from `nodes.csv` and `network.csv`.
  - Vertices $\mathcal{V}$ represent intersections with spatial coordinates $(x, y)$.
  - Directed edges $\mathcal{E}$ represent directional road segments with attributes: `length_m`, `capacity_vph`, `free_flow_speed_kph`, and `lanes`.
- **Turn Restrictions & Constraints**:
  - Incorporates restrictions from `turn_restrictions.csv`. Segments marked with `no_turn` or `no_left` prohibit transitions $(s_i \to s_j)$ where segment $s_i$ enters node $u$ and $s_j$ exits node $u$.
  - Time-window restrictions lacking explicit hour bounds are conservatively enforced (permanently blocked) with clear audit labeling.
- **Dynamic Cost Evaluation**:
  - Segment traversal cost is derived dynamically from current or forecasted speed: $\tau(s) = \frac{\text{length\_m}(s)}{v(s) \cdot (1000/60)}$ minutes.
  - Active roadworks reduce segment effective capacity: $C_{\text{eff}} = C \cdot (1 - \text{closure\_fraction})$.
  - Evaluates diversion paths by transferring a specified diverted volume ($\Delta q_{\text{vph}}$) and recalculating link delays.
  - Planning interventions simulate capacity deltas from `planning_candidates.csv` using standard volume-delay functions.

### 3.4 API Layer (`backend/app/main.py`)
- FastAPI initializes with lifespan handlers that load:
  1. Processed road network topology and NetworkX graph.
  2. Bounded Parquet data partitions into memory/cache.
  3. Pretrained XGBoost model artifacts and feature descriptors.
- Configures `CORSMiddleware` with explicit origins (`http://localhost:3000` and Vercel production URLs).
- Serves read-only REST endpoints. Incoming requests are validated through Pydantic schemas.

### 3.5 Frontend Dashboard (`frontend/src/`)
- Client-side Next.js application built with TypeScript and Tailwind CSS.
- **Leaflet Integration**: Leaflet map components are loaded dynamically via React Client Components with SSR disabled (`dynamic(() => import(...), { ssr: false })`) to avoid window object reference errors in Node.js.
- **Map Fallback**: Renders coordinate-based vectors between nodes even if tile servers are unreachable or offline.
- **Recharts Integration**: Renders historic 5-minute speed timeseries alongside predicted speed points at $t+15$, $t+30$, $t+45$, and $t+60$ minutes.
- **State Management**: Central replay controller managing selected `timestamp`, active `segment_id`, and selected planning candidate.

---

## 4. End-to-End Request/Response Flow

```
[ User Browser ]
       │
       │ 1. Initial Page Load
       ▼
[ Next.js on Vercel ]
       │
       │ 2. Fetch Network Topology (once on startup)
       ├─────────────────────────────────────────────► [ GET /network ]
       │ ◄──────────────────────────────────────────── (Nodes, Links, Coordinates)
       │
       │ 3. User Selects Replay Timestamp (e.g., 2026-01-16 08:30:00)
       ├─────────────────────────────────────────────► [ GET /traffic?timestamp=... ]
       │ ◄──────────────────────────────────────────── (Snapshot: speeds, flow, queues)
       │
       ├─────────────────────────────────────────────► [ GET /alerts?timestamp=... ]
       │ ◄──────────────────────────────────────────── (Suspected incidents & evidence)
       │
       │ 4. User Selects a Congested Segment
       ├─────────────────────────────────────────────► [ GET /forecasts/{id}?timestamp=... ]
       │ ◄──────────────────────────────────────────── (15m, 30m, 45m, 60m predictions)
       │
       ├─────────────────────────────────────────────► [ GET /segments/{id}/history?start=...&end=... ]
       │ ◄──────────────────────────────────────────── (Recent observed speed/flow series)
       │
       │ 5. User Requests Feasible Diversion Around Incident
       ├─────────────────────────────────────────────► [ POST /diversions ]
       │ ◄──────────────────────────────────────────── (Primary route, alternative route, travel times)
       │
       │ 6. User Evaluates Infrastructure Upgrade
       ├─────────────────────────────────────────────► [ POST /planning/evaluate ]
       │ ◄──────────────────────────────────────────── (Baseline vs scenario delay & travel times)
```

---

## 5. Training, Inference, and Artifact Strategy

1. **Strict Offline Training**: Model training is an offline, local batch activity. The FastAPI production server never executes training routines, grid searches, or heavy dataset transformations.
2. **Compact Artifact Bundling**:
   - Model files (`.json` or `.ubj`) are compact (~few megabytes).
   - Only demonstration-relevant processed Parquet data slices (`backend/artifacts/data/`) are packaged for hosted deployment, remaining well within Render's free memory ceiling (512 MB).
3. **Bounded Inference Memory**:
   - Pre-loaded models perform CPU-based inference in sub-10ms latency.
   - Batch feature construction utilizes vectorized slice operations on pre-indexed tabular data.

---

## 6. Hosting & Deployment Topology

### 6.1 Frontend (Vercel Hobby Tier)
- **Deployment**: Automatic continuous deployment from the GitHub repository (`frontend` directory root).
- **Environment Variable**: `NEXT_PUBLIC_API_BASE_URL` pointing to the live Render backend HTTPS endpoint.
- **Constraints**: Hobby tier permits personal, non-commercial use. Production bundle built with `npm run build`.

### 6.2 Backend (Render Free Web Service)
- **Deployment**: Configured with root directory `backend`.
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`
- **Health Check Path**: `/health` (actively polled by Render to confirm operational readiness).
- **Environment Variables**:
  - `CORS_ORIGINS`: JSON list of allowed frontend origins (e.g. `["http://localhost:3000", "https://cityflow.vercel.app"]`).
  - `DATA_DIR`: `artifacts/data` (relative to backend).
  - `MODEL_DIR`: `artifacts/models` (relative to backend).
- **Resource Constraints**:
  - 512 MB RAM limit strictly respected by pre-filtering demo data and running a single worker.
  - Sleep mode occurs after 15 minutes of inactivity; spin-up takes ~50–60 seconds. Handled gracefully in frontend with retry/loading indicators.

---

## 7. Explicit Architecture Boundaries

1. **No External Database**:
   No PostgreSQL, MongoDB, SQLite, or Redis instance is deployed. Parquet files and serialized models provide immutable, fast, file-based persistence for read-only replay.
2. **No LLM / External AI Service**:
   All alerts, incident summaries, and intervention advisories are generated via deterministic, rule-anchored string templates using verified numerical thresholds (e.g., speed drop percentage, queue surge, duration). No OpenAI, Gemini, or external API keys are required.
3. **No Dynamic OpenStreetMap Bulk Tile Scraping**:
   Map displays rely on client-side Leaflet tiles. If tile downloads are blocked or offline, the UI renders direct vector links between coordinate nodes.
