"""
Tests for domain business logic: prerequisite DAG acyclicity, demand forecasting,
and arithmetic reconciliation.
"""

from pathlib import Path
from backend.validation.validate import load_tables, validate_acyclic_prerequisites

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "output"

def test_prerequisite_dag_acyclicity():
    tables = load_tables(DATA_DIR)
    errors = validate_acyclic_prerequisites(tables)
    assert len(errors) == 0, f"Prerequisite cycles detected: {errors}"

def test_forecast_demand_derived_from_history():
    tables = load_tables(DATA_DIR)
    forecasts = tables.get("demand_forecast", [])
    assert len(forecasts) > 0, "No demand forecasts found"
    for fc in forecasts:
        assert fc["method"] == "weighted_moving_average_3term"
        assert fc["window_terms_used"] == "2025-FA,2026-SP,2026-SU"
        assert int(fc["forecast_demand"]) >= 0
        assert int(fc["lower_bound"]) <= int(fc["upper_bound"])

def test_demand_arithmetic_reconciliation():
    tables = load_tables(DATA_DIR)
    forecasts = {f["course_id"]: int(f["forecast_demand"]) for f in tables.get("demand_forecast", [])}
    unmet = {u["course_id"]: int(u["unmet_count"]) for u in tables.get("unmet_demand", [])}
    
    sec_seats: dict = {}
    for s in tables.get("section", []):
        if s["status"] in ("proposed", "approved"):
            cid = s["course_id"]
            sec_seats[cid] = sec_seats.get(cid, 0) + int(s["capacity"])

    # Load ground truth capacity anomalies to account for deliberate edge cases
    import json
    gt_file = ROOT / "data" / "ground_truth" / "ground_truth.json"
    anomalous_sec_ids = set()
    if gt_file.exists():
        with open(gt_file, "r", encoding="utf-8") as f:
            gt_data = json.load(f)
            anomalous_sec_ids = {g["record_id"] for g in gt_data if g["issue_type"] == "section_capacity_too_low"}

    anomalous_courses = {
        s["course_id"] for s in tables.get("section", []) if s["section_id"] in anomalous_sec_ids
    }

    # For every course NOT injected with capacity anomalies, forecast_demand == allocated_seats + unmet_demand strictly holds!
    for cid, f_demand in forecasts.items():
        alloc = sec_seats.get(cid, 0)
        un = unmet.get(cid, 0)
        diff = abs(f_demand - (alloc + un))
        if cid not in anomalous_courses:
            assert diff == 0, f"Reconciliation balance failure for course {cid}: forecast={f_demand}, alloc={alloc}, unmet={un}"
        else:
            # Capacity was deliberately dropped by the anomaly injection
            assert diff > 0, f"Expected anomaly discrepancy for course {cid}"
