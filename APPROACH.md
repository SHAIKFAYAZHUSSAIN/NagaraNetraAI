# CityFlow implementation approach

## Goal

Complete one connected workflow in 18 hours: inspect traffic, flag a suspected incident, forecast speed, compare a legal diversion and evaluate a supplied capacity intervention. Use Next.js and FastAPI with local CPU training. This is a plan; application results have not yet been measured.

## Interface

Operations has a large Leaflet network view, replay-time selector, road details and a forecast horizon selector. The details panel shows observed speed, queue, alert evidence and an advisory. Recharts shows past observations and four forecast points. Keep future ground truth in Evaluation, separate from operational evidence. Display missing data, pending requests, cold starts and no-route results explicitly. Use labels alongside colors. Map links represent supplied connections, not verified street shapes.

Planning shows recurring bottlenecks, a candidate selector, before/after travel times, cost index and assumptions. Evaluation shows horizon-specific errors versus persistence, incident metrics and labeled stress-test results.

## Data preparation

Validate timestamp/segment keys, units and network references. Join context on timestamp and road attributes on segment_id. Sort per segment and reindex to a five-minute grid before row-based lags; otherwise missing readings change a lag's meaning. Preserve quality flags. Use limited past-only gap handling, never backward fill from the future.

Compute features once and save partitioned Parquet files. Use float32 where precision is adequate and bounded caches on the API. Do not send millions of records to the browser. Audit oracle-like columns such as structural_bottleneck before model use. Discover recurring bottlenecks from observed history rather than presenting a supplied flag as a discovery.

## Detection

Start with sustained speed drops supported by increasing queue or occupancy, relative to recent and training-derived usual conditions. Tune thresholds on development data. Explain alerts using actual values and thresholds. A rule score is not a calibrated incident probability. Missing readings must not imply free-flow traffic.

Match reference incidents by segment over start_time <= timestamp < end_time. Incident files are labels for training/evaluation, not live inputs. With only 49 independent training incidents, start with binary suspected-incident detection. Cause classification is optional. Simply displaying the supplied congestion_index does not demonstrate independent detection accuracy.

## Forecasting

Implement persistence first: future speed equals current speed. Train four XGBRegressor models for target_speed_15m, target_speed_30m, target_speed_45m and target_speed_60m. Use tree_method="hist", CPU execution and bounded n_jobs. A first experiment can use 200 trees, max_depth=4 and learning_rate=0.05; these are unvalidated starting settings, not optimal values.

Features: current speed, flow, occupancy, queue and delay; 5/15/30-minute speed lags; past-only rolling means; hour/day; current rain/event level; road capacity, lanes and free-flow speed. Add upstream speed only after integration. Exclude targets, future actual context and incident ground truth from features.

Join labels on timestamp and segment_id with cardinality checks. Fit preprocessing only on training data. Use January 13–15 for internal development and January 16–19 for final reporting. Purge training examples whose target times cross evaluation boundaries. Compute chronological features before subsampling rows for faster experiments.

Save XGBoost JSON/UBJ models with feature order, preprocessing metadata and training cutoff. Supply identical preprocessing at inference. Report MAE in km/h per horizon versus persistence, including sample counts. Retain persistence where it outperforms XGBoost.

If time permits, derive approximate empirical error bands from development residual quantiles and report coverage on final evaluation. Do not describe these as calibrated probabilities for an individual incident.

## Routing

Use a directed segment-transition graph. A transition is valid when one segment ends where the next begins and that movement is permitted. Count first and last segment costs exactly once. Enforce listed no_turn and no_left restrictions.

The supplied time_window restrictions contain no actual time ranges. Conservatively block those listed movements and disclose this assumption. Never relax restrictions silently to produce a route.

Use observed or predicted travel times available at replay time, not future actual values. Compare a few alternatives around an affected corridor. Move a stated small demand amount off the replaced route and onto the alternative, recalculate travel times and check capacity. Apply active scheduled roadwork closure_fraction consistently and show sensitivity to diversion uptake. Return no feasible route explicitly.

## Recurring bottlenecks and planning

Rank segments by repeated congestion across days and accumulated delay. For five-minute samples, approximate vehicle-hours of segment delay as flow_vph * (5/60) * (delay_min/60). This is not a count of unique travelers.

Start with one capacity_upgrade candidate and its capacity_delta_vph. Use a documented volume–delay relationship, calibrated on training observations where feasible. Compare baseline and modified capacity using identical demand and consistent roadwork/peak assumptions. Show capacity, estimated travel time, cost index and limitations.

Until network reassignment is implemented, label results fixed-demand local estimates. They do not establish citywide benefit. Cost_index is not currency. feasibility_band has no defined ordering in the schema: display the supplied value without assuming low means better or worse. Defer connectors because new endpoints are absent and advanced signal retiming requires additional assumptions. OD-based network reassignment is an extension after the core workflow works.

## Proposed API contract

Agree schemas in the first hour. These endpoints are planned, not implemented.

| Endpoint | Input | Output |
| --- | --- | --- |
| GET /health | None | Readiness and artifact availability |
| GET /network | None | Nodes, directed links and attributes |
| GET /traffic | timestamp | Snapshot, quality flags and dataset scope |
| GET /segments/{id}/history | start, end | Bounded past history |
| GET /alerts | timestamp | Suspected incidents and evidence |
| GET /forecasts/{id} | timestamp | Four predictions and model metadata |
| POST /diversions | timestamp, origin_node, destination_node, diverted_flow_vph | Feasible alternatives or no-route result |
| GET /planning/candidates | None | Candidates and bottleneck summaries |
| POST /planning/evaluate | candidate_id, timestamp | Baseline, scenario and assumptions |
| GET /metrics | None | Saved evaluation, split and model version |

Use Pydantic schemas with matching TypeScript interfaces. Units are km/h, vehicles/hour and minutes. Dataset timestamps have no explicit timezone: preserve dataset-local timestamps and document the convention rather than silently appending UTC. Reject unsupported IDs/times, bound history ranges and serialize unavailable numbers as JSON null rather than NaN.

Fetch geometry once and conditions separately. Ordinary HTTP requests suffice; defer WebSockets. Keep evidence tied to the same replay time. Label precomputed predictions if used for the demo.

## Handoffs

- Sohana: frontend, Leaflet, Recharts, API client, loading/error states and Vercel.
- Jithendra: shared preparation, FastAPI schemas, detection, CORS and Render.
- Bhavana: training, saved artifacts, inference wrapper and evaluation.
- Fayaz: routing/planning functions, restriction checks and integration tests.

Hour 4: basic hosted frontend/API. Hour 6: real observations displayed through the API. Hour 10: all core features connected. Hours 10–13: evaluation and hosted memory checks. Hours 13–15: feature freeze, fixes and documentation. Last three hours: rehearsal, fallback checks and submission.

## Acceptance criteria

1. Frontend production build succeeds; health, snapshot and forecast requests work locally and from the deployed frontend origin.
2. No target/future leakage; joins do not multiply observations.
3. Forecast MAE is reported by horizon against persistence on reserved dates.
4. Incident metrics state matching rules. Merge repeated alerts for event-level reporting and acknowledge the small validation event count.
5. Demonstrated routes obey directions and restrictions; no-route cases remain visible.
6. Scenario comparisons hold demand constant and disclose whether reassignment is absent.
7. Missing, duplicate, negative and stale readings have defined handling. Noise/demand stress tests are distinct from supplied-data results.
8. Measure backend memory and cold-start behavior. Keep training local and inference/data loading bounded.
9. A fresh local two-process startup works. Offline network display does not require downloaded OpenStreetMap tiles.

## Five minute demonstration

Replay an incident window, explain the alert, inspect four forecasts, compare a feasible diversion and evaluate one capacity upgrade. Present final evaluation separately from the chosen demo. Include one missing-data or unavailable-route case. Do not claim unmeasured accuracy or improvement.

See [README.md](README.md) for setup, configuration, deployment and official technical references.
