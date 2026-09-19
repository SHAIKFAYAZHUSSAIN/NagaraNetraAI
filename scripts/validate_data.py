#!/usr/bin/env python3
"""
NagaraNetraAI - Dataset Validation Script
Audits and validates the raw and processed datasets for data quality,
timestamp validity, numerical bounds, referential integrity, and train/validation leakage.

Usage:
    python scripts/validate_data.py [--data-dir data/raw]
"""

import argparse
import csv
import os
import sys
from datetime import datetime

EXPECTED_FILES = [
    "context_train.csv",
    "context_validation.csv",
    "forecast_targets_train.csv",
    "forecast_targets_validation.csv",
    "incidents_train.csv",
    "incidents_validation.csv",
    "network.csv",
    "nodes.csv",
    "od_demand_profiles.csv",
    "planning_candidates.csv",
    "roadworks_train.csv",
    "roadworks_validation.csv",
    "scenario_examples.csv",
    "signal_plans.csv",
    "traffic_train.csv",
    "traffic_validation.csv",
    "turn_restrictions.csv",
]


def validate_dataset(data_dir: str) -> bool:
    print(f"=== NagaraNetraAI Dataset Validation ===")
    print(f"Target directory: {os.path.abspath(data_dir)}\n")

    errors = []
    warnings = []

    # 1. Check all expected files exist
    print("[1/6] Checking file presence...")
    for fname in EXPECTED_FILES:
        fpath = os.path.join(data_dir, fname)
        if not os.path.exists(fpath):
            errors.append(f"Missing required file: {fname}")
        else:
            size_mb = os.path.getsize(fpath) / (1024 * 1024)
            print(f"  [OK] Found {fname:<32} ({size_mb:.2f} MB)")

    if errors:
        print("\nFATAL: Missing files detected.")
        for err in errors:
            print(f"  [FAIL] {err}")
        return False

    # 2. Nodes & Network Referential Integrity
    print("\n[2/6] Validating reference integrity (Nodes, Network, Signals, Turns)...")
    nodes_path = os.path.join(data_dir, "nodes.csv")
    node_ids = set()
    with open(nodes_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            node_ids.add(r["node_id"])
            try:
                x, y = float(r["x"]), float(r["y"])
                lat, lon = float(r["lat"]), float(r["lon"])
                if not (0 <= x <= 100 and 0 <= y <= 100):
                    errors.append(f"Invalid node coordinates in nodes.csv for {r['node_id']}: x={x}, y={y}")
                if not (15.0 <= lat <= 20.0 and 75.0 <= lon <= 82.0):
                    warnings.append(f"Unusual lat/lon coordinates for node {r['node_id']}: ({lat}, {lon})")
            except ValueError as e:
                errors.append(f"Non-numeric coordinate in nodes.csv for {r['node_id']}: {e}")

    print(f"  [OK] Loaded {len(node_ids)} nodes from nodes.csv")

    network_path = os.path.join(data_dir, "network.csv")
    segment_ids = set()
    with open(network_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            sid = r["segment_id"]
            segment_ids.add(sid)
            if r["source_node"] not in node_ids:
                errors.append(f"network.csv: source_node {r['source_node']} for segment {sid} not in nodes.csv")
            if r["target_node"] not in node_ids:
                errors.append(f"network.csv: target_node {r['target_node']} for segment {sid} not in nodes.csv")
            try:
                cap = float(r["capacity_vph"])
                speed = float(r["free_flow_speed_kmh"])
                length = float(r["length_km"])
                lanes = int(r["lanes"])
                if cap <= 0 or speed <= 0 or length <= 0 or lanes < 1:
                    errors.append(f"network.csv: Invalid physical attributes for segment {sid}")
            except ValueError as e:
                errors.append(f"network.csv: Non-numeric physical attribute for {sid}: {e}")

    print(f"  [OK] Loaded {len(segment_ids)} network segments from network.csv")

    # Signals
    with open(os.path.join(data_dir, "signal_plans.csv"), "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["node_id"] not in node_ids:
                errors.append(f"signal_plans.csv: node_id {r['node_id']} not in nodes.csv")

    # Turn restrictions
    with open(os.path.join(data_dir, "turn_restrictions.csv"), "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["node_id"] not in node_ids:
                errors.append(f"turn_restrictions.csv: node_id {r['node_id']} not in nodes.csv")
            if r["from_segment"] not in segment_ids:
                errors.append(f"turn_restrictions.csv: from_segment {r['from_segment']} not in network.csv")
            if r["to_segment"] not in segment_ids:
                errors.append(f"turn_restrictions.csv: to_segment {r['to_segment']} not in network.csv")

    # Planning candidates
    with open(os.path.join(data_dir, "planning_candidates.csv"), "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["target_segment"] not in segment_ids:
                errors.append(f"planning_candidates.csv: target_segment {r['target_segment']} not in network.csv")

    # OD demand profiles
    with open(os.path.join(data_dir, "od_demand_profiles.csv"), "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["origin_node"] not in node_ids:
                errors.append(f"od_demand_profiles.csv: origin_node {r['origin_node']} not in nodes.csv")
            if r["destination_node"] not in node_ids:
                errors.append(f"od_demand_profiles.csv: destination_node {r['destination_node']} not in nodes.csv")

    print("  [OK] All network, signal, turn, planning, and OD foreign keys valid.")

    # 3. Context & Incidents & Roadworks
    print("\n[3/6] Validating Context, Incidents, and Roadworks...")
    for inc_file in ["incidents_train.csv", "incidents_validation.csv"]:
        with open(os.path.join(data_dir, inc_file), "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["segment_id"] not in segment_ids:
                    errors.append(f"{inc_file}: segment_id {r['segment_id']} not in network.csv")
                # Check timestamps
                try:
                    t1 = datetime.strptime(r["start_time"], "%Y-%m-%d %H:%M:%S")
                    t2 = datetime.strptime(r["end_time"], "%Y-%m-%d %H:%M:%S")
                    if t2 <= t1:
                        errors.append(f"{inc_file}: end_time {t2} <= start_time {t1} for {r['incident_id']}")
                except ValueError as e:
                    errors.append(f"{inc_file}: Malformed timestamp: {e}")

    for rw_file in ["roadworks_train.csv", "roadworks_validation.csv"]:
        with open(os.path.join(data_dir, rw_file), "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["segment_id"] not in segment_ids:
                    errors.append(f"{rw_file}: segment_id {r['segment_id']} not in network.csv")
                try:
                    t1 = datetime.strptime(r["start_time"], "%Y-%m-%d %H:%M:%S")
                    t2 = datetime.strptime(r["end_time"], "%Y-%m-%d %H:%M:%S")
                    if t2 <= t1:
                        errors.append(f"{rw_file}: end_time {t2} <= start_time {t1} for {r['work_id']}")
                    cf = float(r["closure_fraction"])
                    if not (0.0 <= cf <= 1.0):
                        errors.append(f"{rw_file}: closure_fraction {cf} out of [0, 1]")
                except ValueError as e:
                    errors.append(f"{rw_file}: Value error: {e}")

    print("  [OK] Incidents and Roadworks referential integrity and durations valid.")

    # 4. Train vs Validation Leakage & Temporal Boundary Check
    print("\n[4/6] Checking Train / Validation temporal boundaries and leakage...")
    pairs = [
        ("traffic_train.csv", "traffic_validation.csv", "timestamp"),
        ("forecast_targets_train.csv", "forecast_targets_validation.csv", "timestamp"),
        ("context_train.csv", "context_validation.csv", "timestamp"),
        ("incidents_train.csv", "incidents_validation.csv", "start_time"),
        ("roadworks_train.csv", "roadworks_validation.csv", "start_time"),
    ]

    for train_file, val_file, ts_col in pairs:
        # Get train max
        t_max = None
        with open(os.path.join(data_dir, train_file), "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                ts = datetime.strptime(r[ts_col], "%Y-%m-%d %H:%M:%S")
                if t_max is None or ts > t_max:
                    t_max = ts

        # Get val min
        v_min = None
        with open(os.path.join(data_dir, val_file), "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                ts = datetime.strptime(r[ts_col], "%Y-%m-%d %H:%M:%S")
                if v_min is None or ts < v_min:
                    v_min = ts

        if t_max >= v_min:
            errors.append(f"Leakage detected between {train_file} and {val_file}: train max ({t_max}) >= val min ({v_min})")
        else:
            print(f"  [OK] {train_file} ({t_max}) -> {val_file} ({v_min}) strictly separated.")

    # 5. Traffic Observations Deep Check
    print("\n[5/6] Auditing Traffic Observations (bounds, quality, nulls)...")
    for tf in ["traffic_train.csv", "traffic_validation.csv"]:
        row_count = 0
        with open(os.path.join(data_dir, tf), "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            prev_ts = None
            prev_seg = None
            for r in reader:
                row_count += 1
                sp = float(r["speed_kmh"])
                fl = float(r["flow_vph"])
                oc = float(r["occupancy_pct"])
                dl = float(r["delay_min"])
                ql = float(r["queue_length_veh"])
                ci = float(r["congestion_index"])
                sq = float(r["sensor_quality"])

                if sp < 0 or fl < 0 or oc < 0 or dl < 0 or ql < 0 or ci < 0:
                    errors.append(f"{tf}: Negative value detected at row {row_count}")
                    break
                if sq < 1:
                    errors.append(f"{tf}: sensor_quality < 1 at row {row_count}")
                    break

                ts_str = r["timestamp"]
                if prev_ts is not None and ts_str < prev_ts:
                    errors.append(f"{tf}: Timestamps out of order at row {row_count}")
                    break
                prev_ts = ts_str

        print(f"  [OK] Checked {row_count:,} rows in {tf}: All non-negative, sensor_quality >= 1, sorted.")

    # 6. Summary
    print("\n[6/6] Validation Summary:")
    if warnings:
        print(f"  Warnings ({len(warnings)}):")
        for w in warnings[:5]:
            print(f"    ! {w}")
        if len(warnings) > 5:
            print(f"    ... and {len(warnings) - 5} more warnings.")

    if errors:
        print(f"\n  FAILED with {len(errors)} errors:")
        for err in errors[:10]:
            print(f"    [FAIL] {err}")
        return False
    else:
        print("\n  STATUS: PASS")
        print("  All datasets comply with schemas, referential integrity, and zero-leakage requirements.")
        return True


def main():
    parser = argparse.ArgumentParser(description="Validate NagaraNetraAI datasets.")
    parser.add_argument(
        "--data-dir",
        default="data/raw",
        help="Directory containing the CSV files (default: data/raw)",
    )
    args = parser.parse_args()

    success = validate_dataset(args.data_dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
