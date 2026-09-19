# CityFlow (NagaraNetraAI) — Data Quality Audit Report

**Auditor Role**: Jithendra — Data Engineering + FastAPI + Incident Detection  
**Audit Date**: 2026-09-19  
**Repository Branch**: `feature/data-preparation`  
**Source Dataset Location**: `data/raw/`  
**Audit Scope**: Pre-cleaning evidence-based audit of raw organizer data files.  
**Audit Status**: **`PASS WITH WARNINGS`** (Clean baseline observations; schema and type anomalies documented for Phase 2 cleaning rules).

---

## 1. Dataset Inventory

All 17 expected datasets and metadata files were located under `data/raw/`.

| File | File Size (Bytes) | Row Count | Column Count | Primary Key / Index |
| :--- | :--- | :--- | :--- | :--- |
| `nodes.csv` | 2,734 | 120 | 5 | `node_id` |
| `network.csv` | 35,549 | 436 | 13 | `segment_id` |
| `signal_plans.csv` | 2,234 | 89 | 5 | `signal_id` |
| `turn_restrictions.csv` | 1,661 | 61 | 4 | `(node_id, from_segment, to_segment)` |
| `planning_candidates.csv` | 3,740 | 90 | 6 | `candidate_id` |
| `od_demand_profiles.csv` | 43,413 | 1,500 | 5 | `od_id` |
| `incidents_train.csv` | 3,918 | 49 | 7 | `incident_id` |
| `incidents_validation.csv` | 940 | 11 | 7 | `incident_id` |
| `roadworks_train.csv` | 680 | 8 | 6 | `work_id` |
| `roadworks_validation.csv` | 303 | 3 | 6 | `work_id` |
| `context_train.csv` | 183,206 | 4,320 | 8 | `timestamp` |
| `context_validation.csv` | 49,389 | 1,152 | 8 | `timestamp` |
| `scenario_examples.csv` | 4,593 | 30 | 8 | `scenario_id` |
| `traffic_train.csv` | 162,767,823 | 1,883,520 | 13 | `(timestamp, segment_id)` |
| `traffic_validation.csv` | 43,390,023 | 502,272 | 13 | `(timestamp, segment_id)` |
| `forecast_targets_train.csv` | 37,325,445 | 366,240 | 14 | `(timestamp, segment_id)` |
| `forecast_targets_validation.csv` | 49,015,422 | 481,344 | 14 | `(timestamp, segment_id)` |
| `DATASET_MANIFEST.json` | 910 | N/A | N/A | Manifest metadata |
| `README.md` | 829 | N/A | N/A | Organizer dataset readme |

---

## 2. Schema Validation

1. **Columns and Formats**:
   - `traffic_train.csv` & `traffic_validation.csv` share identical 13 columns: `timestamp`, `segment_id`, `source_node`, `target_node`, `speed_kmh`, `flow_vph`, `occupancy_pct`, `travel_time_min`, `free_flow_time_min`, `delay_min`, `queue_length_veh`, `congestion_index`, `sensor_quality`.
   - `forecast_targets_train.csv` & `forecast_targets_validation.csv` share identical 14 columns: `timestamp`, `segment_id`, and target pairs for 15m, 30m, 45m, 60m (`target_speed_*`, `target_flow_*`, `target_congestion_*`).
   - `context_train.csv` & `context_validation.csv` share 8 columns: `timestamp`, `temperature_c`, `rain_intensity`, `event_level`, `event_id`, `holiday_flag`, `day_of_week`, `hour`.
   - `incidents_train.csv` & `incidents_validation.csv` share 7 columns: `incident_id`, `start_time`, `end_time`, `segment_id`, `incident_type`, `severity`, `lanes_blocked`.
   - `roadworks_train.csv` & `roadworks_validation.csv` share 6 columns: `work_id`, `segment_id`, `start_time`, `end_time`, `closure_fraction`, `work_type`.

2. **Schema Inconsistencies (WARNING)**:
   - In `context_train.csv` and `context_validation.csv`, the `hour` column is serialized as floating-point strings (e.g. `0.0`, `1.0`, ..., `23.0`) rather than integer strings (`0` to `23`).
   - In `planning_candidates.csv`, candidate IDs follow the pattern `PLANxxxx` while `docs/API_CONTRACT.md` uses illustrative `CAP-xxx`.
   - In `incidents_*.csv`, severity is numeric (`1`, `2`, `3`), while API contract examples use qualitative strings (`"high"`, `"medium"`).

---

## 3. Missing Values

- **`traffic_train.csv`**: `0` missing values across all 1,883,520 rows.
- **`traffic_validation.csv`**: `0` missing values across all 502,272 rows.
- **`forecast_targets_train.csv`**: `0` missing values across all 366,240 rows.
- **`forecast_targets_validation.csv`**: `0` missing values across all 481,344 rows.
- **`network.csv`**: 111 missing `signal_id` entries out of 436 segments. This is **valid and expected**; exactly 111 road segments are unsignalized links.
- **`context_train.csv`**: 4,303 missing `event_id` entries out of 4,320 rows.
- **`context_validation.csv`**: 1,109 missing `event_id` entries out of 1,152 rows.
  - This is **valid and expected**; when `event_level == 0` (no public event), `event_id` is null.
- **All other files**: `0` missing values.

---

## 4. Duplicate Records & Keys

- **Exact Duplicate Rows**: `0` duplicate rows across all 17 datasets.
- **Duplicate Primary Keys**:
  - `nodes.csv` (`node_id`): `0` duplicates (120 unique nodes).
  - `network.csv` (`segment_id`): `0` duplicates (436 unique segments).
  - `signal_plans.csv` (`signal_id`): `0` duplicates (89 unique signals).
  - `planning_candidates.csv` (`candidate_id`): `0` duplicates (90 unique candidates).
  - `od_demand_profiles.csv` (`od_id`): `0` duplicates (1,500 unique profiles).
  - `incidents_train.csv` & `incidents_validation.csv`: `0` duplicates (49 and 11 unique incidents).
  - `roadworks_train.csv` & `roadworks_validation.csv`: `0` duplicates (8 and 3 unique roadworks).
- **Compound Key Uniqueness**:
  - `(timestamp, segment_id)` in `traffic_train.csv`: `0` duplicates across 1,883,520 records.
  - `(timestamp, segment_id)` in `traffic_validation.csv`: `0` duplicates across 502,272 records.
  - `(node_id, from_segment, to_segment)` in `turn_restrictions.csv`: `0` duplicates across 61 records.

---

## 5. Timestamp & Five-Minute Resolution Validation

1. **Format and Parsing**:
   - All timestamps parse strictly with `%Y-%m-%d %H:%M:%S` with `0` malformed timestamps.
   - Timestamps are local timestamps without explicit timezone offsets (consistent with `docs/API_CONTRACT.md`).
2. **Chronological Ordering**:
   - `traffic_train.csv`: Strictly sorted chronologically by `timestamp` then `segment_id`. `0` out-of-order records.
   - `traffic_validation.csv`: Strictly sorted chronologically by `timestamp` then `segment_id`. `0` out-of-order records.
   - `context_train.csv` & `context_validation.csv`: Strictly sorted chronologically.
3. **Five-Minute Resolution & Grid Completeness**:
   - `traffic_train.csv`:
     - Range: `2026-01-01 00:00:00` to `2026-01-15 23:55:00` = exactly 15 full days = 4,320 5-minute time steps.
     - Expected observations: $436 \text{ segments} \times 4,320 \text{ steps} = 1,883,520 \text{ rows}$.
     - Actual observations: $1,883,520 \text{ rows}$.
     - **Missing 5-minute intervals**: **0**. The time grid is 100% complete for all segments.
   - `traffic_validation.csv`:
     - Range: `2026-01-16 00:00:00` to `2026-01-19 23:55:00` = exactly 4 full days = 1,152 5-minute time steps.
     - Expected observations: $436 \text{ segments} \times 1,152 \text{ steps} = 502,272 \text{ rows}$.
     - Actual observations: $502,272 \text{ rows}$.
     - **Missing 5-minute intervals**: **0**. The time grid is 100% complete for all segments.

---

## 6. Train / Validation Separation & Leakage

- **Traffic**: Training concludes at `2026-01-15 23:55:00`. Validation commences at `2026-01-16 00:00:00`. Temporal gap: exactly 5 minutes (next step). **No overlap**.
- **Forecast Targets**: Training ends at `2026-01-15 22:55:00` (allowing 60-minute target window to conclude by `23:55:00` without crossing validation boundary). Validation starts at `2026-01-16 00:00:00`. **No overlap / leakage**.
- **Context**: Training concludes at `2026-01-15 23:55:00`. Validation begins at `2026-01-16 00:00:00`. **No overlap**.
- **Incidents & Roadworks**: Cleanly partitioned with zero date overlap.
- **Leakage Result**: **PASS**. Zero data leakage between training and validation sets.

---

## 7. Referential Integrity

- **Network $\to$ Nodes**: All 436 directed segments in `network.csv` have `source_node` and `target_node` in `nodes.csv` (100% valid, 0 orphans).
- **Signals $\to$ Nodes**: All 89 signal records in `signal_plans.csv` reference valid nodes in `nodes.csv`.
- **Turns $\to$ Nodes & Network**: All 61 turn restrictions in `turn_restrictions.csv` reference valid nodes and segments in `network.csv`.
- **Planning $\to$ Network**: All 90 planning candidates in `planning_candidates.csv` reference valid `target_segment` IDs in `network.csv`.
- **OD Profiles $\to$ Nodes**: All 1,500 origin-destination pairs reference valid nodes in `nodes.csv`.
- **Traffic $\to$ Network**: All 436 segment IDs present in traffic observations exist in `network.csv`.
- **Incidents & Roadworks $\to$ Network**: All incident and roadwork segments exist in `network.csv`.
- **Referential Integrity Result**: **PASS (0 broken foreign keys)**.

---

## 8. Numeric & Physical Bound Validation

- **Speed (`speed_kmh`)**: $11.2 \text{ km/h} \le v \le 60.0 \text{ km/h}$. `0` negative speeds; speeds do not exceed free-flow physical limits.
- **Flow (`flow_vph`)**: $0.0 \le q \le 4,502.2 \text{ vph}$. `0` negative flows.
- **Occupancy (`occupancy_pct`)**: $7.0\% \le \text{occ} \le 98.0\%$. `0` negative occupancies.
- **Delay (`delay_min`)**: $0.0 \le \text{delay} \le 4.826 \text{ min}$. `0` negative delays.
- **Queue (`queue_length_veh`)**: $0.0 \le \text{queue} \le 1,047.9 \text{ veh}$. `0` negative queues.
- **Congestion Index**: $0.0 \le \text{CI} \le 0.7207$.
- **Sensor Quality**: Strictly $1.0$ across all rows. `0` rows with degraded sensor quality $< 1$.
- **Road Capacities**: $900.0 \text{ vph} \le C \le 3,105.0 \text{ vph}$.
- **Node Coordinates**: $x \in [0, 11]$, $y \in [0, 9]$, $\text{lat} \in [17.300, 17.462]$, $\text{lon} \in [78.350, 78.548]$ (Hyderabad metropolitan coordinate frame).

---

## 9. Potential Leakage Risks & Forecast Integrity

1. **Forecast Target Columns**:
   - `target_speed_15m`, `target_speed_30m`, `target_speed_45m`, `target_speed_60m` (along with corresponding flow and congestion targets) in `forecast_targets_*.csv` must be treated strictly as **supervised training labels** and never ingested as feature columns.
2. **Structural Bottleneck Oracle Flag**:
   - `network.csv` contains `structural_bottleneck` (16 segments marked as `1`). In accordance with `APPROACH.md`, models and alert rules must discover bottlenecks dynamically from observed delay rather than treating this supplied flag as a runtime feature.
3. **Ground-Truth Incident Labels**:
   - `incidents_train.csv` and `incidents_validation.csv` provide evaluation ground truth and must not be fed to operational detection endpoints.

---

## 10. Issues Requiring Cleaning (Phase 2)

1. **Context Table Hour Typing**: Convert `hour` column from float string (`0.0`-`23.0`) to canonical integer string (`0`-`23`).
2. **Reference Table Canonical Sorting**: Sort `planning_candidates.csv` by `candidate_id` and `turn_restrictions.csv` by `(node_id, from_segment, to_segment)` to remove row-shuffle noise.

---

## 11. Issues That Should NOT Be Automatically Cleaned

1. **Missing `signal_id` in `network.csv`**: Unsignalized segments naturally have no signal controller. Do not impute with `0` or fake IDs.
2. **Missing `event_id` in `context_*.csv`**: Non-event intervals have no event ID. Do not fabricate event IDs.
3. **Turn Restriction Time Windows**: `time_window` restrictions lack hour bounds. As documented in `docs/TEAM_CONTEXT.md`, they must be treated as permanently active restrictions, not deleted or modified.
4. **Outlier Queue Spikes**: Extreme queues (> 1,000 veh) correspond to major incident periods (e.g. stalled vehicles or lane closures). They represent genuine congestion dynamics and must NOT be smoothed or clipped.

---

## 12. Recommended Cleaning Rules & Parquet Structure

### Cleaning Rules
1. Preserve immutable raw data in `data/raw/`.
2. Normalize all data types (integer hour, float32 metrics).
3. Reindex to uniform 5-minute grid (already 100% complete in source data).
4. Join contextual weather and events strictly on `timestamp`.
5. Join static road network attributes strictly on `segment_id`.

### Recommended Parquet Structure (`data/processed/`)
To fit within Render's 512 MB memory limit and satisfy GitHub's 100 MB file limit:
```text
data/processed/
├── network/
│   └── network.parquet (436 segments, snappy-compressed)
├── nodes/
│   └── nodes.parquet (120 nodes)
├── traffic/
│   ├── date=2026-01-01/part-0.parquet
│   ├── ...
│   └── date=2026-01-19/part-0.parquet
├── context/
│   └── context.parquet
└── reference/
    ├── signals.parquet
    ├── turn_restrictions.parquet
    └── planning_candidates.parquet
```

---

## 13. Final Audit Status

### **`PASS WITH WARNINGS`**
- **Data Integrity**: **PASS**. Zero corrupt records, zero negative values, zero sensor quality degradation, zero duplicate keys.
- **Temporal Quality**: **PASS**. 100% complete 5-minute resolution across 19 days.
- **Referential Integrity**: **PASS**. All foreign keys valid.
- **Warnings**: Minor formatting inconsistencies (`hour` float in context) and row-shuffle in static tables, to be resolved deterministically during Phase 2 Parquet pipeline execution.
