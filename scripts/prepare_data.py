#!/usr/bin/env python3
"""
NagaraNetraAI - Data Preparation and Normalization Pipeline
Ingests raw organizer CSVs, validates schemas and referential integrity,
normalizes data types, preserves legitimate nulls and outliers,
and outputs partitioned Apache Parquet files.

Usage:
    python scripts/prepare_data.py [--raw-dir data/raw] [--out-dir data/processed]
"""

import argparse
import os
import sys
from datetime import datetime
import pandas as pd
import numpy as np

EXPECTED_RAW_FILES = [
    "nodes.csv",
    "network.csv",
    "signal_plans.csv",
    "turn_restrictions.csv",
    "planning_candidates.csv",
    "od_demand_profiles.csv",
    "context_train.csv",
    "context_validation.csv",
    "traffic_train.csv",
    "traffic_validation.csv",
    "forecast_targets_train.csv",
    "forecast_targets_validation.csv",
]


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def prepare_data(raw_dir: str, out_dir: str):
    log(f"Starting data preparation pipeline...")
    log(f"Raw source: {os.path.abspath(raw_dir)}")
    log(f"Output destination: {os.path.abspath(out_dir)}")

    # 1. Verify existence of required raw files
    for fname in EXPECTED_RAW_FILES:
        fpath = os.path.join(raw_dir, fname)
        if not os.path.exists(fpath):
            raise FileNotFoundError(f"Missing required raw dataset: {fpath}")

    os.makedirs(out_dir, exist_ok=True)
    ref_dir = os.path.join(out_dir, "reference")
    traffic_dir = os.path.join(out_dir, "traffic")
    os.makedirs(ref_dir, exist_ok=True)
    os.makedirs(traffic_dir, exist_ok=True)

    # 2. Nodes
    log("Processing nodes.csv...")
    df_nodes = pd.read_csv(os.path.join(raw_dir, "nodes.csv"))
    expected_node_cols = ["node_id", "x", "y", "lat", "lon"]
    if list(df_nodes.columns) != expected_node_cols:
        raise ValueError(f"Unexpected nodes.csv columns: {df_nodes.columns}")

    df_nodes = df_nodes.astype({
        "node_id": "string",
        "x": "float32",
        "y": "float32",
        "lat": "float32",
        "lon": "float32",
    })
    df_nodes = df_nodes.sort_values("node_id").reset_index(drop=True)
    valid_node_ids = set(df_nodes["node_id"])
    nodes_out = os.path.join(out_dir, "nodes.parquet")
    df_nodes.to_parquet(nodes_out, engine="pyarrow", index=False)
    log(f"  -> Wrote {len(df_nodes)} nodes to {nodes_out}")

    # 3. Network
    log("Processing network.csv...")
    df_net = pd.read_csv(os.path.join(raw_dir, "network.csv"))
    expected_net_cols = [
        "segment_id", "source_node", "target_node", "road_class", "lanes",
        "free_flow_speed_kmh", "capacity_vph", "length_km", "grade_pct",
        "signal_id", "structural_bottleneck", "importance", "peak_capacity_factor"
    ]
    if list(df_net.columns) != expected_net_cols:
        raise ValueError(f"Unexpected network.csv columns: {df_net.columns}")

    # Validate foreign keys
    invalid_sources = set(df_net["source_node"]) - valid_node_ids
    invalid_targets = set(df_net["target_node"]) - valid_node_ids
    if invalid_sources or invalid_targets:
        raise ValueError(f"Network contains invalid node IDs: sources={invalid_sources}, targets={invalid_targets}")

    df_net = df_net.astype({
        "segment_id": "string",
        "source_node": "string",
        "target_node": "string",
        "road_class": "string",
        "lanes": "int32",
        "free_flow_speed_kmh": "float32",
        "capacity_vph": "float32",
        "length_km": "float32",
        "grade_pct": "float32",
        "signal_id": "string",  # preserves nulls cleanly
        "structural_bottleneck": "int32",
        "importance": "float32",
        "peak_capacity_factor": "float32",
    })
    df_net = df_net.sort_values("segment_id").reset_index(drop=True)
    valid_segment_ids = set(df_net["segment_id"])
    net_out = os.path.join(out_dir, "network.parquet")
    df_net.to_parquet(net_out, engine="pyarrow", index=False)
    log(f"  -> Wrote {len(df_net)} segments to {net_out} (preserved {df_net['signal_id'].isna().sum()} unsignalized nulls)")

    # 4. Signals
    log("Processing signal_plans.csv...")
    df_sig = pd.read_csv(os.path.join(raw_dir, "signal_plans.csv"))
    if not set(df_sig["node_id"]).issubset(valid_node_ids):
        raise ValueError("signal_plans.csv contains orphan node IDs")
    df_sig = df_sig.astype({
        "signal_id": "string",
        "node_id": "string",
        "cycle_s": "float32",
        "green_ratio": "float32",
        "offset_s": "float32",
    }).sort_values("signal_id").reset_index(drop=True)
    sig_out = os.path.join(ref_dir, "signals.parquet")
    df_sig.to_parquet(sig_out, engine="pyarrow", index=False)
    log(f"  -> Wrote {len(df_sig)} signal plans to {sig_out}")

    # 5. Turn Restrictions
    log("Processing turn_restrictions.csv...")
    df_turns = pd.read_csv(os.path.join(raw_dir, "turn_restrictions.csv"))
    if not set(df_turns["node_id"]).issubset(valid_node_ids):
        raise ValueError("turn_restrictions.csv contains invalid node IDs")
    if not set(df_turns["from_segment"]).issubset(valid_segment_ids):
        raise ValueError("turn_restrictions.csv contains invalid from_segment IDs")
    if not set(df_turns["to_segment"]).issubset(valid_segment_ids):
        raise ValueError("turn_restrictions.csv contains invalid to_segment IDs")

    df_turns = df_turns.astype({
        "node_id": "string",
        "from_segment": "string",
        "to_segment": "string",
        "restriction": "string",
    }).sort_values(["node_id", "from_segment", "to_segment"]).reset_index(drop=True)
    turns_out = os.path.join(ref_dir, "turn_restrictions.parquet")
    df_turns.to_parquet(turns_out, engine="pyarrow", index=False)
    log(f"  -> Wrote {len(df_turns)} turn restrictions to {turns_out}")

    # 6. Planning Candidates
    log("Processing planning_candidates.csv...")
    df_plans = pd.read_csv(os.path.join(raw_dir, "planning_candidates.csv"))
    if not set(df_plans["target_segment"]).issubset(valid_segment_ids):
        raise ValueError("planning_candidates.csv contains invalid target_segment IDs")

    df_plans = df_plans.astype({
        "candidate_id": "string",
        "target_segment": "string",
        "intervention_type": "string",
        "capacity_delta_vph": "float32",
        "cost_index": "int32",
        "feasibility_band": "string",
    }).sort_values("candidate_id").reset_index(drop=True)
    plans_out = os.path.join(ref_dir, "planning_candidates.parquet")
    df_plans.to_parquet(plans_out, engine="pyarrow", index=False)
    log(f"  -> Wrote {len(df_plans)} planning candidates to {plans_out}")

    # 7. Context (train + validation normalized)
    log("Processing context_train.csv and context_validation.csv...")
    df_ctx_tr = pd.read_csv(os.path.join(raw_dir, "context_train.csv"))
    df_ctx_val = pd.read_csv(os.path.join(raw_dir, "context_validation.csv"))
    df_ctx = pd.concat([df_ctx_tr, df_ctx_val], ignore_index=True)

    # Normalize hour to integer (e.g. "0.0" -> 0)
    df_ctx["hour"] = df_ctx["hour"].astype(float).astype("int32")
    df_ctx["event_level"] = df_ctx["event_level"].astype("int32")
    df_ctx["holiday_flag"] = df_ctx["holiday_flag"].astype("int32")
    df_ctx["day_of_week"] = df_ctx["day_of_week"].astype("int32")
    df_ctx["temperature_c"] = df_ctx["temperature_c"].astype("float32")
    df_ctx["rain_intensity"] = df_ctx["rain_intensity"].astype("float32")
    df_ctx["event_id"] = df_ctx["event_id"].astype("string")  # preserves nulls
    df_ctx["timestamp"] = df_ctx["timestamp"].astype("string")

    df_ctx = df_ctx.sort_values("timestamp").reset_index(drop=True)
    ctx_out = os.path.join(out_dir, "context.parquet")
    df_ctx.to_parquet(ctx_out, engine="pyarrow", index=False)
    log(f"  -> Wrote {len(df_ctx)} context rows to {ctx_out} (normalized hour to int32, preserved {df_ctx['event_id'].isna().sum()} event_id nulls)")

    # 8. Traffic Observations (Processed day-by-day to enforce 512 MB memory constraint)
    log("Processing traffic observations into daily partitions (date=YYYY-MM-DD)...")
    traffic_files = [
        os.path.join(raw_dir, "traffic_train.csv"),
        os.path.join(raw_dir, "traffic_validation.csv"),
    ]

    total_traffic_rows = 0
    partition_counts = {}

    for tf in traffic_files:
        log(f"  Streaming {os.path.basename(tf)}...")
        # Read in daily chunks (each day has 436 segments * 288 steps = 125,568 rows)
        chunk_size = 125568
        for chunk in pd.read_csv(tf, chunksize=chunk_size):
            # Validate segment references
            if not set(chunk["segment_id"]).issubset(valid_segment_ids):
                raise ValueError("Traffic chunk contains unknown segment_id")

            # Validate numeric bounds
            if (chunk["speed_kmh"] < 0).any() or (chunk["flow_vph"] < 0).any():
                raise ValueError("Traffic chunk contains negative speed or flow")
            if (chunk["sensor_quality"] < 1).any():
                raise ValueError("Traffic chunk contains sensor_quality < 1")

            # Extract partition date from timestamp (first 10 chars: YYYY-MM-DD)
            chunk_dates = chunk["timestamp"].str[:10].unique()
            for cdate in chunk_dates:
                df_day = chunk[chunk["timestamp"].str[:10] == cdate].copy()
                
                # Verify uniqueness of (timestamp, segment_id)
                dups = df_day.duplicated(subset=["timestamp", "segment_id"]).sum()
                if dups > 0:
                    raise ValueError(f"Duplicate (timestamp, segment_id) detected on date {cdate}: {dups} duplicates")

                # Cast types
                df_day = df_day.astype({
                    "timestamp": "string",
                    "segment_id": "string",
                    "source_node": "string",
                    "target_node": "string",
                    "speed_kmh": "float32",
                    "flow_vph": "float32",
                    "occupancy_pct": "float32",
                    "travel_time_min": "float32",
                    "free_flow_time_min": "float32",
                    "delay_min": "float32",
                    "queue_length_veh": "float32",
                    "congestion_index": "float32",
                    "sensor_quality": "float32",
                })

                # Sort deterministically by timestamp, segment_id
                df_day = df_day.sort_values(["timestamp", "segment_id"]).reset_index(drop=True)

                day_dir = os.path.join(traffic_dir, f"date={cdate}")
                os.makedirs(day_dir, exist_ok=True)
                part_file = os.path.join(day_dir, "part.parquet")

                # If partition already exists (in case day spans chunk), append/combine cleanly
                if os.path.exists(part_file):
                    existing = pd.read_parquet(part_file)
                    df_day = pd.concat([existing, df_day], ignore_index=True)
                    df_day = df_day.sort_values(["timestamp", "segment_id"]).reset_index(drop=True)

                df_day.to_parquet(part_file, engine="pyarrow", index=False)
                partition_counts[cdate] = len(df_day)
                total_traffic_rows += len(df_day)

    log(f"  -> Total traffic rows processed: {total_traffic_rows:,} across {len(partition_counts)} daily partitions.")
    for d, c in sorted(partition_counts.items()):
        log(f"     • date={d}: {c:,} rows")

    log("\n[SUCCESS] Data preparation and Parquet normalization complete!")
    return True


def main():
    parser = argparse.ArgumentParser(description="Prepare and normalize NagaraNetraAI datasets.")
    parser.add_argument("--raw-dir", default="data/raw", help="Path to raw CSV directory")
    parser.add_argument("--out-dir", default="data/processed", help="Path to output processed directory")
    args = parser.parse_args()

    prepare_data(args.raw_dir, args.out_dir)


if __name__ == "__main__":
    main()
