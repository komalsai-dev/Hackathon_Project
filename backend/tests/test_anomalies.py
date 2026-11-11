"""
Tests for anomaly injection, detection recall, and strict ground-truth isolation.
"""

import json
from pathlib import Path
from backend.validation.validate import (
    load_tables,
    detect_anomalies_by_rules,
    evaluate_detections_against_ground_truth,
)

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "output"
GT_DIR = ROOT / "data" / "ground_truth"

def test_ground_truth_isolation():
    """Verify ground truth columns do NOT leak into input tables."""
    tables = load_tables(DATA_DIR)
    forbidden_columns = {"issue_type", "injected_flag", "expected_decision", "expected_reason_code"}
    
    for t_name, rows in tables.items():
        if rows:
            cols = set(rows[0].keys())
            leaked = cols & forbidden_columns
            assert len(leaked) == 0, f"Ground truth columns leaked into table {t_name}: {leaked}"

def test_all_five_anomalies_present_in_ground_truth():
    gt_file = GT_DIR / "ground_truth.json"
    assert gt_file.exists(), "Ground truth JSON does not exist"
    
    with open(gt_file, "r", encoding="utf-8") as f:
        gt_data = json.load(f)
    
    required_types = {
        "faculty_outside_skill",
        "workload_exceeded",
        "section_capacity_too_low",
        "prerequisite_violation",
        "duplicate_section_assignment",
    }
    present_types = {r["issue_type"] for r in gt_data if r.get("injected_flag") == 1}
    assert required_types.issubset(present_types), f"Missing anomaly types: {required_types - present_types}"

def test_high_anomaly_detection_recall():
    """Ensure rule-based validation engine detects injected anomalies with >= 90% recall."""
    tables = load_tables(DATA_DIR)
    with open(GT_DIR / "ground_truth.json", "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    detections = detect_anomalies_by_rules(tables)
    eval_metrics = evaluate_detections_against_ground_truth(detections, ground_truth)
    
    recall = eval_metrics["overall"]["recall"]
    assert recall >= 0.90, f"Recall was {recall:.2f}, expected >= 0.90"

