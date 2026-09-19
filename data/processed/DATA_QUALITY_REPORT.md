# NagaraNetraAI — Dataset Quality & Audit Report

**Audit Date**: 2026-09-19  
**Target Repository**: `NethraAI (CityFlow)`  
**Auditor**: Data Engineering Specialist  
**Final Status**: **`PASS`**

---

## 1. Executive Summary

A comprehensive data engineering audit, validation, and cleaning was conducted across all 17 datasets supplied for the **NEURAX Hackathon 3.0 — NagaraNetraAI (CityFlow)** project.

- **Datasets Inspected**: 17 CSV files + `DATASET_MANIFEST.json` + `README.md`
- **Duplicate Rows / Primary Keys Detected**: `0` across all files.
- **Malformed Timestamps**: `0` across all files.
- **Train / Validation Temporal Leakage**: `None`. All training observation periods end strictly before validation begins.
- **Referential Integrity**: 100% valid. All foreign keys (`node_id`, `segment_id`, `signal_id`) map accurately to physical nodes and directed network links.
- **Numerical Bounds**: All speeds, flows, occupancies, and queues are strictly non-negative; `sensor_quality >= 1`.
- **Large Dataset Architecture Compliance**: In compliance with GitHub's 100MB file limit and the repository's documented architecture (`ARCHITECTURE.md` §3.1), raw observation files remain preserved in `data/raw/` for local Parquet partitioning, while cleaned, standardized reference/context datasets are deployed to `data/processed/`.

---

## 2. Dataset Inventory & Summary Table

| Dataset | Rows (Raw) | Rows (Cleaned) | Columns | Missing Values | Duplicate Rows | Invalid Records | Sorting Key / Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `nodes.csv` | 120 | 120 | 5 | 0 | 0 | 0 | `node_id` (Sorted) |
| `network.csv` | 436 | 436 | 13 | 111 (`signal_id`)* | 0 | 0 | `segment_id` (Sorted) |
| `signal_plans.csv` | 89 | 89 | 5 | 0 | 0 | 0 | `signal_id` (Sorted) |
| `turn_restrictions.csv` | 61 | 61 | 4 | 0 | 0 | 0 | `(node_id, from_seg, to_seg)` (Sorted) |
| `planning_candidates.csv` | 90 | 90 | 6 | 0 | 0 | 0 | `candidate_id` (Sorted) |
| `od_demand_profiles.csv` | 1,500 | 1,500 | 5 | 0 | 0 | 0 | `od_id` (Sorted) |
| `incidents_train.csv` | 49 | 49 | 7 | 0 | 0 | 0 | `incident_id` (Sorted) |
| `incidents_validation.csv` | 11 | 11 | 7 | 0 | 0 | 0 | `incident_id` (Sorted) |
| `roadworks_train.csv` | 8 | 8 | 6 | 0 | 0 | 0 | `work_id` (Sorted) |
| `roadworks_validation.csv` | 3 | 3 | 6 | 0 | 0 | 0 | `work_id` (Sorted) |
| `context_train.csv` | 4,320 | 4,320 | 8 | 4,303 (`event_id`)* | 0 | 0 | `timestamp` (Sorted) |
| `context_validation.csv` | 1,152 | 1,152 | 8 | 1,109 (`event_id`)* | 0 | 0 | `timestamp` (Sorted) |
| `scenario_examples.csv` | 30 | 30 | 8 | 0 | 0 | 0 | `scenario_id` (Sorted) |
| `traffic_train.csv` | 1,883,520 | 1,883,520 | 13 | 0 | 0 | 0 | `(timestamp, segment_id)` (Preserved in raw) |
| `traffic_validation.csv` | 502,272 | 502,272 | 13 | 0 | 0 | 0 | `(timestamp, segment_id)` (Preserved in raw) |
| `forecast_targets_train.csv` | 366,240 | 366,240 | 14 | 0 | 0 | 0 | `(timestamp, segment_id)` (Preserved in raw) |
| `forecast_targets_validation.csv` | 481,344 | 481,344 | 14 | 0 | 0 | 0 | `(timestamp, segment_id)` (Preserved in raw) |

*\*Note on Missing Values: `signal_id` in `network.csv` is null for unsignalized segments (111 segments); `event_id` in `context_*.csv` is null when `event_level == 0` (no public event). Both are legitimate schema-permitted nulls.*

---

## 3. Changes Made

1. **Standardized Integer Types in Context Tables**:
   - **Files affected**: `context_train.csv` (4,320 records) and `context_validation.csv` (1,152 records).
   - **Change**: `hour` column contained floating-point values (e.g. `0.0`, `1.0`, ..., `23.0`). Converted to standard integer string representations (`0` to `23`).
   - **Rationale**: Downstream feature extraction and API responses expect integer hours (`0-23`).

2. **Deterministic Canonical Sorting of Reference Tables**:
   - **Files affected**:
     - `planning_candidates.csv`: Sorted deterministically by `candidate_id` (`PLAN0001` to `PLAN0436`). (90 records).
     - `turn_restrictions.csv`: Sorted by composite key `(node_id, from_segment, to_segment)`. (61 records).
     - `signal_plans.csv`: Sorted by `signal_id`. (89 records).
     - `incidents_*.csv`: Sorted by `incident_id`. (49 and 11 records).
     - `roadworks_*.csv`: Sorted by `work_id`. (8 and 3 records).
   - **Rationale**: Eliminates row-shuffle noise described in `DATASET_MANIFEST.json` and guarantees deterministic graph construction and routing evaluation across runs.

3. **Preservation of Raw Data**:
   - No files under `data/raw/` were overwritten or altered. Original files serve as immutable ground truth.

---

## 4. Quality Checks & Verification

### A. Missing Values
- Verified that all core traffic metrics (`speed_kmh`, `flow_vph`, `occupancy_pct`, `travel_time_min`, `delay_min`, `queue_length_veh`, `congestion_index`, `sensor_quality`) contain **0** nulls, NaNs, or empty strings.
- All target columns in `forecast_targets_*.csv` contain **0** nulls.

### B. Duplicate Rows & Compound Keys
- Verified uniqueness of compound key `(timestamp, segment_id)` across all 1,883,520 training and 502,272 validation traffic rows.
- Verified uniqueness of primary keys in `nodes.csv` (`node_id`), `network.csv` (`segment_id`), `signal_plans.csv` (`signal_id`), `planning_candidates.csv` (`candidate_id`), and `od_demand_profiles.csv` (`od_id`).

### C. Numerical Bounds & Physical Plausibility
- **Traffic observations**:
  - Speed: 11.2 km/h to 60.0 km/h (No negative speeds, free-flow upper bound obeyed).
  - Flow: 0.0 vph to 4,502.2 vph (Plausible urban corridor volumes).
  - Occupancy: 7.0% to 98.0% (Valid percentage range).
  - Delay: 0.0 min to 4.826 min.
  - Sensor quality: 1.0 (No degraded sensors < 1).
- **Network physical attributes**:
  - Capacity: 900 vph to 3,105 vph.
  - Free-flow speed: 30 km/h to 60 km/h.
  - Length: 0.751 km to 1.791 km.
  - Lanes: 1 to 3 lanes.
- **Node coordinates**:
  - Synthetic coordinates $x \in [0, 11]$, $y \in [0, 9]$.
  - Geographical bounds: Latitude $\in [17.300, 17.462]^\circ\text{N}$, Longitude $\in [78.350, 78.548]^\circ\text{E}$ (Hyderabad urban metropolitan coordinate frame).

### D. Timestamp Validation & Train/Validation Leakage
- Timestamps strictly follow local `YYYY-MM-DD HH:MM:SS` format on a uniform 5-minute resolution.
- **Chronological Split Verification**:
  - `traffic_train.csv`: `2026-01-01 00:00:00` to `2026-01-15 23:55:00` (15 days).
  - `traffic_validation.csv`: `2026-01-16 00:00:00` to `2026-01-19 23:55:00` (4 days).
  - `forecast_targets_train.csv`: `2026-01-01 00:00:00` to `2026-01-15 22:55:00`.
  - `forecast_targets_validation.csv`: `2026-01-16 00:00:00` to `2026-01-19 22:55:00`.
  - `incidents_train.csv`: `2026-01-01 06:05:00` to `2026-01-15 20:47:00`.
  - `incidents_validation.csv`: `2026-01-16 13:13:00` to `2026-01-19 16:36:00`.
  - `roadworks_train.csv`: `2026-01-02 08:00:00` to `2026-01-12 10:00:00`.
  - `roadworks_validation.csv`: `2026-01-16 12:00:00` to `2026-01-18 15:00:00`.
- **Leakage Result**: **Zero leakage detected**. Every training sequence concludes before the validation period commences.

### E. Referential Integrity
- All 436 directed segments in `network.csv` connect valid nodes present in `nodes.csv` (0 orphan links).
- All 89 signals in `signal_plans.csv` reference valid nodes in `nodes.csv`.
- All 61 turn restrictions in `turn_restrictions.csv` reference valid nodes and segments in `network.csv`.
- All 90 planning candidates in `planning_candidates.csv` reference valid segments in `network.csv`.
- All 1,500 origin-destination pairs in `od_demand_profiles.csv` reference valid nodes in `nodes.csv`.
- All 60 combined incidents in `incidents_*.csv` reference valid segments in `network.csv`.
- All 11 combined roadworks in `roadworks_*.csv` reference valid segments in `network.csv`.
- **Referential Integrity Result**: **100% valid (0 broken references)**.

---

## 5. Machine Learning Readiness

1. **Target Separation**: Forecast targets (`target_speed_15m`, `target_flow_15m`, etc.) are isolated from observation features, preventing target leakage during lag and rolling-mean feature extraction.
2. **Standardized Encodings**: Categorical types across incident types, road classes, intervention types, and feasibility bands have discrete, stable value distributions.
3. **Reproducibility**: Preprocessing script `scripts/validate_data.py` provides deterministic verification before model training runs.

---

## 6. Unresolved Issues

- **None**. The dataset is structurally sound, clean, and ready for model training and API integration.

---

## 7. Final Validation Status

### **`PASS`**
All dataset files meet the strict quality, integrity, and non-leakage criteria required for the NagaraNetraAI project.
