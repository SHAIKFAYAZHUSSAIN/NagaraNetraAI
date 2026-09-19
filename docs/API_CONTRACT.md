# CityFlow — API Contract & Interface Specification

## 1. Overview & Source of Truth

This document specifies the REST API contract for the **CityFlow** urban traffic intelligence platform. The specifications herein are directly derived from and strictly aligned with [APPROACH.md](../APPROACH.md) and [README.md](../README.md).

### Core Architectural Directives
- **Zero Schema Drift**: Backend Pydantic models (`backend/app/schemas.py`) and Frontend TypeScript interfaces (`frontend/src/lib/api.ts`) must maintain exact structural parity in field names, types, and nullability.
- **Strict Unit Conventions**:
  - Speed: **$\text{km/h}$**
  - Traffic Flow: **$\text{vehicles/hour}$ ($\text{vph}$)**
  - Queue Length: **$\text{meters}$ ($\text{m}$)**
  - Delay & Travel Times: **$\text{minutes}$ ($\text{min}$)**
  - Distance: **$\text{meters}$ ($\text{m}$)**
- **Timestamp Handling**: Dataset timestamps are recorded in local format (`YYYY-MM-DD HH:MM:SS`) without explicit timezone offsets. Timestamps must be preserved and parsed as local timestamps; do not convert or append artificial UTC designations (`Z`).
- **Null Serialization**: Missing or unavailable sensor readings and prediction residuals must be serialized as standard JSON `null`. Floating-point `NaN`, `-Infinity`, or string `"NaN"` values are strictly prohibited in API responses.
- **Bounded Ingestion**: History and snapshot requests must enforce maximum query window limits (e.g., maximum 24-hour historical window) to safeguard backend memory.

---

## 2. Global Error Envelope

All error responses return a standardized JSON structure:

```json
{
  "code": "RESOURCE_NOT_FOUND",
  "detail": "Segment ID 9999 was not found in the road network.",
  "timestamp": "2026-01-16 08:30:00",
  "path": "/api/v1/forecasts/9999"
}
```

### Standard Status Codes
- `200 OK`: Request succeeded.
- `400 Bad Request`: Malformed parameters, invalid timestamp format, or out-of-range bounds.
- `404 Not Found`: Requested segment, node, or intervention candidate does not exist.
- `422 Unprocessable Entity`: Request body or query parameters failed Pydantic validation.
- `500 Internal Server Error`: Unhandled server exception.
- `503 Service Unavailable`: Required machine learning models or data partitions are not yet loaded.

---

## 3. Endpoints Specification

### 3.1 `GET /health`
**Description**: Verification probe for service readiness, memory health, and artifact availability. Polled by hosting infrastructure (Render) and the frontend on startup.

- **Request**: None
- **Response (200 OK)**:
```json
{
  "status": "ready",
  "version": "0.1.0",
  "timestamp": "2026-01-16 08:30:00",
  "artifacts": {
    "network_graph_loaded": true,
    "parquet_partitions_available": true,
    "forecast_models_loaded": {
      "15m": true,
      "30m": true,
      "45m": true,
      "60m": true
    }
  }
}
```

---

### 3.2 `GET /network`
**Description**: Fetches the static physical network topology including node coordinates, directed segments, turn restrictions, and baseline capacities. Fetched once during frontend initialization.

- **Request**: None
- **Response (200 OK)**:
```json
{
  "nodes": [
    {
      "node_id": 101,
      "x": 450.25,
      "y": 820.10
    }
  ],
  "segments": [
    {
      "segment_id": 12,
      "from_node": 101,
      "to_node": 102,
      "length_m": 450.0,
      "capacity_vph": 1800.0,
      "free_flow_speed_kph": 60.0,
      "lanes": 2
    }
  ],
  "turn_restrictions": [
    {
      "from_segment_id": 12,
      "to_segment_id": 18,
      "via_node": 102,
      "restriction_type": "no_left",
      "is_active": true
    }
  ]
}
```

---

### 3.3 `GET /traffic`
**Description**: Retrieves a network-wide dynamic traffic snapshot for a specific replay timestamp.

- **Request Query Parameters**:
  - `timestamp` (string, required): Format `YYYY-MM-DD HH:MM:SS`.
- **Response (200 OK)**:
```json
{
  "timestamp": "2026-01-16 08:30:00",
  "scope": {
    "total_segments": 436,
    "reporting_segments": 436
  },
  "segments": [
    {
      "segment_id": 12,
      "speed_kph": 24.5,
      "flow_vph": 1650.0,
      "occupancy": 0.38,
      "queue_m": 120.0,
      "delay_min": 4.2,
      "sensor_quality": 1
    }
  ]
}
```

---

### 3.4 `GET /segments/{id}/history`
**Description**: Returns a bounded chronological time series of past observations for a specified segment.

- **Request Path Parameters**:
  - `id` (integer, required): Segment ID.
- **Request Query Parameters**:
  - `start` (string, required): Format `YYYY-MM-DD HH:MM:SS`.
  - `end` (string, required): Format `YYYY-MM-DD HH:MM:SS`. (Duration between `start` and `end` cannot exceed 24 hours).
- **Response (200 OK)**:
```json
{
  "segment_id": 12,
  "start": "2026-01-16 06:00:00",
  "end": "2026-01-16 08:30:00",
  "records": [
    {
      "timestamp": "2026-01-16 06:00:00",
      "speed_kph": 55.2,
      "flow_vph": 820.0,
      "occupancy": 0.12,
      "queue_m": 0.0,
      "delay_min": 0.0
    }
  ]
}
```

---

### 3.5 `GET /alerts`
**Description**: Returns suspected traffic incidents detected at the given replay timestamp, complete with empirical trigger evidence.

- **Request Query Parameters**:
  - `timestamp` (string, required): Format `YYYY-MM-DD HH:MM:SS`.
- **Response (200 OK)**:
```json
{
  "timestamp": "2026-01-16 08:30:00",
  "alerts": [
    {
      "alert_id": "ALT-20260116-0830-12",
      "segment_id": 12,
      "severity": "high",
      "confidence_score": 0.88,
      "evidence": {
        "observed_speed_kph": 18.2,
        "typical_speed_kph": 48.0,
        "speed_drop_pct": 62.1,
        "queue_m": 180.0,
        "consecutive_intervals": 3
      },
      "advisory": "Severe congestion detected on Segment 12 (62% speed drop, 180m queue). Diversion advisory recommended."
    }
  ]
}
```

---

### 3.6 `GET /forecasts/{id}`
**Description**: Returns the 4 horizon speed forecasts ($t+15$, $t+30$, $t+45$, $t+60$ minutes) for a specified segment at a given replay timestamp, alongside baseline persistence comparison.

- **Request Path Parameters**:
  - `id` (integer, required): Segment ID.
- **Request Query Parameters**:
  - `timestamp` (string, required): Format `YYYY-MM-DD HH:MM:SS`.
- **Response (200 OK)**:
```json
{
  "segment_id": 12,
  "timestamp": "2026-01-16 08:30:00",
  "current_speed_kph": 22.4,
  "horizons": {
    "15m": {
      "horizon_min": 15,
      "predicted_speed_kph": 20.1,
      "persistence_speed_kph": 22.4
    },
    "30m": {
      "horizon_min": 30,
      "predicted_speed_kph": 18.5,
      "persistence_speed_kph": 22.4
    },
    "45m": {
      "horizon_min": 45,
      "predicted_speed_kph": 24.0,
      "persistence_speed_kph": 22.4
    },
    "60m": {
      "horizon_min": 60,
      "predicted_speed_kph": 32.8,
      "persistence_speed_kph": 22.4
    }
  },
  "metadata": {
    "model_version": "xgb_v1.0_hist",
    "training_cutoff": "2026-01-15 23:55:00",
    "features_used": ["speed_lag5", "speed_lag15", "queue", "occupancy", "hour", "dayofweek"]
  }
}
```

---

### 3.7 `POST /diversions`
**Description**: Computes a legal, turn-restriction-compliant diversion alternative between origin and destination nodes around an incident corridor.

- **Request Headers**: `Content-Type: application/json`
- **Request Body**:
```json
{
  "timestamp": "2026-01-16 08:30:00",
  "origin_node": 101,
  "destination_node": 140,
  "diverted_flow_vph": 250.0
}
```
- **Response (200 OK — Route Found)**:
```json
{
  "status": "feasible_route_found",
  "timestamp": "2026-01-16 08:30:00",
  "primary_route": {
    "segments": [12, 13, 14],
    "estimated_travel_time_min": 14.2,
    "distance_m": 2100.0,
    "bottleneck_segments": [12]
  },
  "alternative_route": {
    "segments": [105, 106, 110, 115],
    "estimated_travel_time_min": 9.8,
    "distance_m": 2450.0,
    "spare_capacity_vph": 450.0,
    "turn_restrictions_obeyed": true,
    "roadworks_active": false
  },
  "time_saved_min": 4.4
}
```
- **Response (200 OK — No Feasible Route)**:
```json
{
  "status": "no_feasible_route",
  "timestamp": "2026-01-16 08:30:00",
  "primary_route": null,
  "alternative_route": null,
  "time_saved_min": 0.0,
  "reason": "All alternative corridor paths exceed capacity or violate turn restrictions at junction 102."
}
```

---

### 3.8 `GET /planning/candidates`
**Description**: Fetches the supplied catalog of infrastructure capacity upgrade candidates alongside historical recurring bottleneck summaries.

- **Request**: None
- **Response (200 OK)**:
```json
{
  "bottlenecks": [
    {
      "segment_id": 12,
      "severity_rank": 1,
      "weekly_delay_hours": 1420.5,
      "congestion_frequency_pct": 68.4
    }
  ],
  "candidates": [
    {
      "candidate_id": "CAP-012",
      "candidate_type": "capacity_upgrade",
      "segment_id": 12,
      "capacity_delta_vph": 600.0,
      "cost_index": 4,
      "feasibility_band": "medium",
      "description": "Lane widening and signal queue clearance on Segment 12"
    }
  ]
}
```

---

### 3.9 `POST /planning/evaluate`
**Description**: Evaluates a specific infrastructure planning candidate under fixed-demand simulation assumptions.

- **Request Headers**: `Content-Type: application/json`
- **Request Body**:
```json
{
  "candidate_id": "CAP-012",
  "timestamp": "2026-01-16 08:30:00"
}
```
- **Response (200 OK)**:
```json
{
  "candidate_id": "CAP-012",
  "segment_id": 12,
  "baseline": {
    "capacity_vph": 1800.0,
    "demand_vph": 1650.0,
    "speed_kph": 24.5,
    "travel_time_min": 5.8
  },
  "scenario": {
    "capacity_vph": 2400.0,
    "demand_vph": 1650.0,
    "speed_kph": 48.0,
    "travel_time_min": 2.9
  },
  "travel_time_saved_min": 2.9,
  "delay_reduction_pct": 50.0,
  "cost_index": 4,
  "assumptions": [
    "Fixed-demand local estimate; OD reassignment not computed",
    "Standard BPR volume-delay formula calibrated to training data",
    "Active roadwork closure fractions applied consistently"
  ]
}
```

---

### 3.10 `GET /metrics`
**Description**: Serves evaluation benchmark results comparing model accuracy against baseline persistence across validation data.

- **Request**: None
- **Response (200 OK)**:
```json
{
  "evaluation_split": "traffic_validation.csv (January 16-19, 2026)",
  "observations_evaluated": 502272,
  "forecasting_mae_kph": {
    "15m": { "xgboost": 4.12, "persistence": 5.84, "improvement_pct": 29.4 },
    "30m": { "xgboost": 5.30, "persistence": 7.91, "improvement_pct": 32.9 },
    "45m": { "xgboost": 6.18, "persistence": 9.45, "improvement_pct": 34.6 },
    "60m": { "xgboost": 6.85, "persistence": 10.72, "improvement_pct": 36.1 }
  },
  "incident_detection": {
    "validation_incidents_total": 11,
    "precision": 0.82,
    "recall": 0.73,
    "f1_score": 0.77,
    "notes": "Evaluation conducted on 11 validated incident windows with binary matching rules."
  }
}
```

---

## 4. Matching Schemas: Pydantic & TypeScript

To maintain consistency across both sides of the repository, use the following paired definitions:

### 4.1 Forecast Types
**Python Pydantic (`backend/app/schemas.py`)**:
```python
from pydantic import BaseModel
from typing import Dict, List

class HorizonPrediction(BaseModel):
    horizon_min: int
    predicted_speed_kph: float
    persistence_speed_kph: float

class ForecastMetadata(BaseModel):
    model_version: str
    training_cutoff: str
    features_used: List[str]

class ForecastResponse(BaseModel):
    segment_id: int
    timestamp: str
    current_speed_kph: float
    horizons: Dict[str, HorizonPrediction]
    metadata: ForecastMetadata
```

**TypeScript Interface (`frontend/src/lib/api.ts`)**:
```typescript
export interface HorizonPrediction {
  horizon_min: number;
  predicted_speed_kph: number;
  persistence_speed_kph: number;
}

export interface ForecastMetadata {
  model_version: string;
  training_cutoff: string;
  features_used: string[];
}

export interface ForecastResponse {
  segment_id: number;
  timestamp: string;
  current_speed_kph: number;
  horizons: Record<string, HorizonPrediction>;
  metadata: ForecastMetadata;
}
```

### 4.2 Diversion Types
**Python Pydantic (`backend/app/schemas.py`)**:
```python
from pydantic import BaseModel, Field
from typing import List, Optional

class DiversionRequest(BaseModel):
    timestamp: str
    origin_node: int
    destination_node: int
    diverted_flow_vph: float = Field(..., gt=0.0)

class RouteSummary(BaseModel):
    segments: List[int]
    estimated_travel_time_min: float
    distance_m: float
    spare_capacity_vph: Optional[float] = None
    bottleneck_segments: Optional[List[int]] = None
    turn_restrictions_obeyed: bool = True
    roadworks_active: bool = False

class DiversionResponse(BaseModel):
    status: str
    timestamp: str
    primary_route: Optional[RouteSummary]
    alternative_route: Optional[RouteSummary]
    time_saved_min: float
    reason: Optional[str] = None
```

**TypeScript Interface (`frontend/src/lib/api.ts`)**:
```typescript
export interface DiversionRequest {
  timestamp: string;
  origin_node: number;
  destination_node: number;
  diverted_flow_vph: number;
}

export interface RouteSummary {
  segments: number[];
  estimated_travel_time_min: number;
  distance_m: number;
  spare_capacity_vph?: number;
  bottleneck_segments?: number[];
  turn_restrictions_obeyed: boolean;
  roadworks_active: boolean;
}

export interface DiversionResponse {
  status: 'feasible_route_found' | 'no_feasible_route';
  timestamp: string;
  primary_route: RouteSummary | null;
  alternative_route: RouteSummary | null;
  time_saved_min: number;
  reason?: string;
}
```

### 4.3 Planning Evaluation Types
**Python Pydantic (`backend/app/schemas.py`)**:
```python
from pydantic import BaseModel
from typing import List

class PlanningEvaluationRequest(BaseModel):
    candidate_id: str
    timestamp: str

class TrafficStateSummary(BaseModel):
    capacity_vph: float
    demand_vph: float
    speed_kph: float
    travel_time_min: float

class PlanningEvaluationResponse(BaseModel):
    candidate_id: str
    segment_id: int
    baseline: TrafficStateSummary
    scenario: TrafficStateSummary
    travel_time_saved_min: float
    delay_reduction_pct: float
    cost_index: int
    assumptions: List[str]
```

**TypeScript Interface (`frontend/src/lib/api.ts`)**:
```typescript
export interface PlanningEvaluationRequest {
  candidate_id: string;
  timestamp: string;
}

export interface TrafficStateSummary {
  capacity_vph: number;
  demand_vph: number;
  speed_kph: number;
  travel_time_min: number;
}

export interface PlanningEvaluationResponse {
  candidate_id: string;
  segment_id: number;
  baseline: TrafficStateSummary;
  scenario: TrafficStateSummary;
  travel_time_saved_min: number;
  delay_reduction_pct: number;
  cost_index: number;
  assumptions: string[];
}
```
