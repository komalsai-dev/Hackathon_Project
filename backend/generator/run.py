"""
Main entry point for dataset generation pipeline.
Usage:
    python -m backend.generator.run [--seed 20261022] [--scale starter|full]
"""

import argparse
import sys
from pathlib import Path
from backend.generator.config import (
    MASTER_SEED,
    SCALE_CONFIGS,
    ScaleConfig,
)
from backend.generator.master_data import generate_master_data
from backend.generator.history import generate_history
from backend.generator.forecast import generate_forecasts
from backend.generator.allocation import run_allocation
from backend.generator.derived import compute_derived_metrics
from backend.generator.anomalies import inject_anomalies_and_build_ground_truth
from backend.generator.export import export_all

def run_pipeline(
    seed: int = MASTER_SEED,
    scale_name: str = "starter",
    base_dir: Path = None
) -> None:
    """
    Execute full generation pipeline deterministically.
    """
    if base_dir is None:
        base_dir = Path(__file__).resolve().parent.parent.parent

    scale = SCALE_CONFIGS.get(scale_name)
    if not scale:
        raise ValueError(f"Unknown scale: {scale_name}. Choose 'starter' or 'full'.")

    print("=" * 70)
    print(f"COURSE DEMAND FORECASTING & FACULTY ALLOCATION GENERATOR")
    print(f"Master Seed: {seed} | Scale: {scale_name.upper()}")
    print("=" * 70)

    # 1. Master Data
    print("\n[1/6] Generating master entities (Programs, Courses, Faculty, Rooms)...")
    master_data = generate_master_data(seed, scale)
    print(f"  --> {len(master_data['program'])} programs, {len(master_data['course'])} courses, "
          f"{len(master_data['faculty'])} faculty, {len(master_data['room'])} rooms")

    # 2. History & Student Plans
    print("\n[2/6] Generating student cohorts, completed courses, and historical registration interest...")
    history_data = generate_history(seed, scale, master_data)
    print(f"  --> {len(history_data['student_plan'])} student plans, "
          f"{len(history_data['registration_interest'])} registration interest records")

    # 3. Demand Forecasting
    print("\n[3/6] Computing 3-term weighted moving average demand forecasts...")
    forecasts = generate_forecasts(master_data, history_data)
    print(f"  --> {len(forecasts)} course forecasts computed for target term")

    # 4. Section Sizing & Faculty Allocation
    print("\n[4/6] Allocating sections, rooms, and faculty workload under constraints...")
    alloc_data = run_allocation(master_data, forecasts)
    print(f"  --> {len(alloc_data['section'])} sections created, "
          f"{len(alloc_data['workload_assignment'])} faculty assignments made, "
          f"{len(alloc_data['decision_log'])} decision log entries recorded")

    # 5. Derived Metrics & Summary
    print("\n[5/6] Computing derived metrics and operational KPIs...")
    summary_data = compute_derived_metrics(master_data, forecasts, alloc_data, history_data)
    kpis = summary_data["kpis"]
    print(f"  --> Total Forecast Demand : {kpis['total_forecast_demand']}")
    print(f"  --> Allocated Seats       : {kpis['total_allocated_seats']}")
    print(f"  --> Unmet Demand Seats    : {kpis['total_unmet_demand']}")
    print(f"  --> Demand Fill Rate      : {kpis['fill_rate_pct']}%")
    print(f"  --> Faculty Utilization   : {kpis['faculty_utilization_pct']}%")

    # 6. Anomaly Injection & Isolated Ground Truth
    print("\n[6/6] Injecting controlled anomalies and recording isolated ground truth...")
    ground_truth = inject_anomalies_and_build_ground_truth(
        seed=seed,
        scale=scale,
        master_data=master_data,
        history_data=history_data,
        alloc_data=alloc_data,
        forecasts=forecasts,
    )
    print(f"  --> Recorded {len(ground_truth)} ground-truth rows (isolated in data/ground_truth/)")

    # Consolidate all tables
    all_tables = {
        "program": master_data["program"],
        "course": master_data["course"],
        "program_course": master_data["program_course"],
        "prerequisite": master_data["prerequisite"],
        "faculty": master_data["faculty"],
        "faculty_skill": master_data["faculty_skill"],
        "availability": master_data["availability"],
        "room": master_data["room"],
        "student_plan": history_data["student_plan"],
        "student_plan_completed_course": history_data["student_plan_completed_course"],
        "registration_interest": history_data["registration_interest"],
        "demand_forecast": forecasts,
        "section": alloc_data["section"],
        "section_event": alloc_data["section_event"],
        "workload_assignment": alloc_data["workload_assignment"],
        "assignment_event": alloc_data["assignment_event"],
        "unmet_demand": alloc_data["unmet_demand"],
        "decision_log": alloc_data["decision_log"],
    }

    # Export
    output_dir = base_dir / "data" / "output"
    gt_dir = base_dir / "data" / "ground_truth"
    seed_sql = base_dir / "database" / "seed" / "seed.sql"
    sqlite_db = output_dir / "course_demand.sqlite"
    # Always locate schema.sql relative to repo root
    schema_sql = Path(__file__).resolve().parent.parent.parent / "database" / "schema.sql"

    print("\nExporting CSVs, JSONs, SQLite database, and SQL seed...")
    export_all(
        all_tables=all_tables,
        ground_truth=ground_truth,
        summary_data=summary_data,
        output_dir=output_dir,
        ground_truth_dir=gt_dir,
        seed_sql_path=seed_sql,
        sqlite_db_path=sqlite_db,
        schema_sql_path=schema_sql,
    )
    print(f"SUCCESS: Dataset generated successfully into {output_dir}")
    print("=" * 70)

def main():
    parser = argparse.ArgumentParser(description="Course Demand Synthetic Data Generator")
    parser.add_argument("--seed", type=int, default=MASTER_SEED, help="Master random seed")
    parser.add_argument("--scale", type=str, default="starter", choices=["starter", "full"], help="Dataset scale")
    args = parser.parse_args()

    run_pipeline(seed=args.seed, scale_name=args.scale)

if __name__ == "__main__":
    main()
