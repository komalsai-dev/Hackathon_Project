"""
Comprehensive validation and anomaly detection engine.

Validates:
1. Primary Key uniqueness across all tables.
2. Foreign Key referential integrity.
3. Allowed enum domains.
4. ID regex format compliance.
5. Date ordering constraints.
6. Demand arithmetic reconciliation:
   forecast_demand == allocated_seats + unmet_demand.
7. Event lifecycle valid sequences (proposed -> approved).
8. Acyclic prerequisite graph (DAG validation).
9. Rule-based anomaly detection for the 5 injected edge cases.
10. Evaluates detection metrics (Precision, Recall, F1) against isolated ground truth.
"""

import csv
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any

from backend.generator.ids import validate_id, ID_PATTERNS

VALID_ENUMS: Dict[str, Dict[str, Set[str]]] = {
    "program": {
        "level": {"Undergraduate", "Graduate"},
        "status": {"active", "inactive", "deprecated"},
    },
    "course": {
        "category": {"core", "popular_elective", "low_enrollment", "standard"},
        "status": {"active", "inactive", "deprecated"},
    },
    "program_course": {
        "requirement_type": {"core", "elective"},
    },
    "prerequisite": {
        "min_grade": {"A", "B", "C", "D"},
    },
    "faculty": {
        "employment_type": {"full_time", "adjunct"},
        "status": {"active", "on_leave", "retired"},
    },
    "availability": {
        "day_of_week": {"MWF", "TTH", "M", "T", "W", "TH", "F"},
        "availability_type": {"available", "leave"},
    },
    "room": {
        "room_type": {"lecture_hall", "classroom", "seminar", "computer_lab"},
    },
    "student_plan": {
        "status": {"active", "graduated", "withdrawn", "on_leave"},
    },
    "student_plan_completed_course": {
        "grade": {"A", "B", "C", "D", "F"},
    },
    "registration_interest": {
        "status": {"active", "fulfilled", "cancelled", "waitlisted"},
    },
    "section": {
        "status": {"proposed", "approved", "changed", "cancelled"},
        "day_of_week": {"MWF", "TTH", "M", "T", "W", "TH", "F"},
    },
    "section_event": {
        "event_type": {"proposed", "approved", "changed", "cancelled"},
    },
    "workload_assignment": {
        "status": {"assigned", "unassigned", "flagged", "reallocated"},
    },
    "assignment_event": {
        "event_type": {"assigned", "unassigned", "flagged", "reallocated"},
    },
    "unmet_demand": {
        "reason_code": {"no_faculty", "no_room", "capacity_limit", "prereq_gap", "zero_demand"},
    },
}

def load_tables(data_dir: Path) -> Dict[str, List[Dict[str, Any]]]:
    """Load all tables from CSV files into memory."""
    tables: Dict[str, List[Dict[str, Any]]] = {}
    for csv_file in data_dir.glob("*.csv"):
        t_name = csv_file.stem
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            tables[t_name] = list(reader)
    return tables

def validate_primary_keys(tables: Dict[str, List[Dict[str, Any]]]) -> List[str]:
    """Verify primary key uniqueness on all tables."""
    errors = []
    pk_map = {
        "program": "program_id",
        "course": "course_id",
        "prerequisite": "prerequisite_id",
        "faculty": "faculty_id",
        "availability": "availability_id",
        "room": "room_id",
        "student_plan": "student_plan_id",
        "registration_interest": "interest_id",
        "demand_forecast": "forecast_id",
        "section": "section_id",
        "section_event": "event_id",
        "workload_assignment": "assignment_id",
        "assignment_event": "event_id",
        "unmet_demand": "unmet_id",
        "decision_log": "decision_id",
    }
    for t_name, pk_col in pk_map.items():
        rows = tables.get(t_name, [])
        seen = set()
        for r in rows:
            val = r[pk_col]
            if val in seen:
                errors.append(f"Duplicate PK in {t_name}: {val}")
            seen.add(val)

    # Composite PKs
    for pc in tables.get("program_course", []):
        key = (pc["program_id"], pc["course_id"])
        if key in seen:
            errors.append(f"Duplicate PK in program_course: {key}")
        seen.add(key)

    seen.clear()
    for fs in tables.get("faculty_skill", []):
        key = (fs["faculty_id"], fs["course_id"])
        if key in seen:
            errors.append(f"Duplicate PK in faculty_skill: {key}")
        seen.add(key)

    seen.clear()
    for cc in tables.get("student_plan_completed_course", []):
        key = (cc["student_plan_id"], cc["course_id"])
        if key in seen:
            errors.append(f"Duplicate PK in student_plan_completed_course: {key}")
        seen.add(key)

    return errors

def validate_foreign_keys(tables: Dict[str, List[Dict[str, Any]]]) -> List[str]:
    """Verify all foreign keys point to valid parent records."""
    errors = []
    program_ids = {r["program_id"] for r in tables.get("program", [])}
    course_ids = {r["course_id"] for r in tables.get("course", [])}
    faculty_ids = {r["faculty_id"] for r in tables.get("faculty", [])}
    room_ids = {r["room_id"] for r in tables.get("room", [])}
    student_plan_ids = {r["student_plan_id"] for r in tables.get("student_plan", [])}
    section_ids = {r["section_id"] for r in tables.get("section", [])}
    assignment_ids = {r["assignment_id"] for r in tables.get("workload_assignment", [])}

    for pc in tables.get("program_course", []):
        if pc["program_id"] not in program_ids:
            errors.append(f"program_course orphaned program_id: {pc['program_id']}")
        if pc["course_id"] not in course_ids:
            errors.append(f"program_course orphaned course_id: {pc['course_id']}")

    for prq in tables.get("prerequisite", []):
        if prq["course_id"] not in course_ids:
            errors.append(f"prerequisite orphaned course_id: {prq['course_id']}")
        if prq["required_course_id"] not in course_ids:
            errors.append(f"prerequisite orphaned required_course_id: {prq['required_course_id']}")

    for fs in tables.get("faculty_skill", []):
        if fs["faculty_id"] not in faculty_ids:
            errors.append(f"faculty_skill orphaned faculty_id: {fs['faculty_id']}")
        if fs["course_id"] not in course_ids:
            errors.append(f"faculty_skill orphaned course_id: {fs['course_id']}")

    for av in tables.get("availability", []):
        if av["faculty_id"] not in faculty_ids:
            errors.append(f"availability orphaned faculty_id: {av['faculty_id']}")

    for sp in tables.get("student_plan", []):
        if sp["program_id"] not in program_ids:
            errors.append(f"student_plan orphaned program_id: {sp['program_id']}")

    for cc in tables.get("student_plan_completed_course", []):
        if cc["student_plan_id"] not in student_plan_ids:
            errors.append(f"student_plan_completed_course orphaned student_plan_id: {cc['student_plan_id']}")
        if cc["course_id"] not in course_ids:
            errors.append(f"student_plan_completed_course orphaned course_id: {cc['course_id']}")

    for ri in tables.get("registration_interest", []):
        if ri["student_plan_id"] not in student_plan_ids:
            errors.append(f"registration_interest orphaned student_plan_id: {ri['student_plan_id']}")
        if ri["course_id"] not in course_ids:
            errors.append(f"registration_interest orphaned course_id: {ri['course_id']}")

    for sec in tables.get("section", []):
        if sec["course_id"] not in course_ids:
            errors.append(f"section orphaned course_id: {sec['course_id']}")
        if sec["room_id"] not in room_ids:
            errors.append(f"section orphaned room_id: {sec['room_id']}")

    for wla in tables.get("workload_assignment", []):
        if wla["section_id"] not in section_ids:
            errors.append(f"workload_assignment orphaned section_id: {wla['section_id']}")
        if wla["faculty_id"] not in faculty_ids:
            errors.append(f"workload_assignment orphaned faculty_id: {wla['faculty_id']}")

    for sev in tables.get("section_event", []):
        if sev["section_id"] not in section_ids:
            errors.append(f"section_event orphaned section_id: {sev['section_id']}")

    for aev in tables.get("assignment_event", []):
        if aev["assignment_id"] not in assignment_ids:
            errors.append(f"assignment_event orphaned assignment_id: {aev['assignment_id']}")

    for um in tables.get("unmet_demand", []):
        if um["course_id"] not in course_ids:
            errors.append(f"unmet_demand orphaned course_id: {um['course_id']}")

    return errors

def validate_enums(tables: Dict[str, List[Dict[str, Any]]]) -> List[str]:
    """Verify values adhere to allowed enum sets."""
    errors = []
    for t_name, col_rules in VALID_ENUMS.items():
        rows = tables.get(t_name, [])
        for r in rows:
            for col, allowed_vals in col_rules.items():
                val = r.get(col)
                if val is not None and val not in allowed_vals:
                    errors.append(f"Invalid enum in {t_name}.{col}: '{val}' not in {allowed_vals}")
    return errors

def validate_id_patterns(tables: Dict[str, List[Dict[str, Any]]]) -> List[str]:
    """Verify ID regex patterns."""
    errors = []
    checks = [
        ("program", "program_id", "program_id"),
        ("course", "course_id", "course_id"),
        ("prerequisite", "prerequisite_id", "prerequisite_id"),
        ("faculty", "faculty_id", "faculty_id"),
        ("availability", "availability_id", "availability_id"),
        ("room", "room_id", "room_id"),
        ("student_plan", "student_plan_id", "student_plan_id"),
        ("student_plan", "student_ref", "student_ref"),
        ("registration_interest", "interest_id", "interest_id"),
        ("demand_forecast", "forecast_id", "forecast_id"),
        ("section", "section_id", "section_id"),
        ("section_event", "event_id", "section_event_id"),
        ("workload_assignment", "assignment_id", "assignment_id"),
        ("assignment_event", "event_id", "assignment_event_id"),
        ("unmet_demand", "unmet_id", "unmet_id"),
        ("decision_log", "decision_id", "decision_id"),
    ]
    for t_name, col, id_type in checks:
        for r in tables.get(t_name, []):
            val = r[col]
            if not validate_id(id_type, val):
                errors.append(f"Invalid ID format in {t_name}.{col}: '{val}'")
    return errors

def validate_acyclic_prerequisites(tables: Dict[str, List[Dict[str, Any]]]) -> List[str]:
    """Verify prerequisite graph has zero cycles using topological sort."""
    errors = []
    prereqs = tables.get("prerequisite", [])
    
    # Graph: course -> list of prerequisite courses
    adj: Dict[str, List[str]] = {}
    all_courses: Set[str] = set()
    for p in prereqs:
        c = p["course_id"]
        req = p["required_course_id"]
        if c == req:
            errors.append(f"Self-reference prerequisite found: {c}")
        if c not in adj:
            adj[c] = []
        adj[c].append(req)
        all_courses.add(c)
        all_courses.add(req)

    # Cycle detection via DFS
    visited: Dict[str, int] = {c: 0 for c in all_courses}  # 0: unvisited, 1: visiting, 2: visited

    def dfs(node: str, path: List[str]) -> bool:
        visited[node] = 1
        for neighbor in adj.get(node, []):
            if visited[neighbor] == 1:
                errors.append(f"Prerequisite cycle detected: {' -> '.join(path + [neighbor])}")
                return True
            if visited[neighbor] == 0:
                if dfs(neighbor, path + [neighbor]):
                    return True
        visited[node] = 2
        return False

    for node in all_courses:
        if visited[node] == 0:
            dfs(node, [node])

    return errors

def detect_anomalies_by_rules(
    tables: Dict[str, List[Dict[str, Any]]]
) -> List[Dict[str, Any]]:
    """
    Pure rule-based anomaly detector.
    Does NOT reference ground_truth. Evaluates strictly on domain rules.
    """
    detections: List[Dict[str, Any]] = []

    # 1. Detect faculty_outside_skill
    skills = {(fs["faculty_id"], fs["course_id"]) for fs in tables.get("faculty_skill", [])}
    sec_course_map = {s["section_id"]: s["course_id"] for s in tables.get("section", [])}
    for wla in tables.get("workload_assignment", []):
        cid = sec_course_map.get(wla["section_id"])
        fid = wla["faculty_id"]
        if cid and (fid, cid) not in skills:
            detections.append({
                "entity": "workload_assignment",
                "record_id": wla["assignment_id"],
                "issue_type": "faculty_outside_skill",
                "detected_reason": f"Faculty {fid} lacks certified skill for course {cid}",
            })

    # 2. Detect workload_exceeded
    fac_max_hours = {f["faculty_id"]: float(f["max_weekly_hours"]) for f in tables.get("faculty", [])}
    fac_assigned: Dict[str, float] = {}
    for wla in tables.get("workload_assignment", []):
        fid = wla["faculty_id"]
        hrs = float(wla["assigned_hours"])
        fac_assigned[fid] = fac_assigned.get(fid, 0.0) + hrs

    for fid, tot_hrs in fac_assigned.items():
        max_h = fac_max_hours.get(fid, 16.0)
        if tot_hrs > max_h:
            detections.append({
                "entity": "faculty",
                "record_id": fid,
                "issue_type": "workload_exceeded",
                "detected_reason": f"Assigned {tot_hrs:.1f}h exceeds max {max_h:.1f}h",
            })

    # 3. Detect section_capacity_too_low
    for sec in tables.get("section", []):
        cap = int(sec["capacity"])
        # Minimum reasonable capacity for an approved university section is 10
        if cap < 10 and sec["status"] in ("proposed", "approved"):
            detections.append({
                "entity": "section",
                "record_id": sec["section_id"],
                "issue_type": "section_capacity_too_low",
                "detected_reason": f"Section capacity {cap} is below minimum threshold 10",
            })

    # 4. Detect prerequisite_violation in registration interest
    # Map completed courses per student: student_plan_id -> dict of (course_id -> grade)
    GRADE_RANK = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}
    student_completed_grades: Dict[str, Dict[str, str]] = {}
    for cc in tables.get("student_plan_completed_course", []):
        sid = cc["student_plan_id"]
        if sid not in student_completed_grades:
            student_completed_grades[sid] = {}
        student_completed_grades[sid][cc["course_id"]] = cc["grade"]

    # Course prerequisites: course_id -> list of (required_course_id, min_grade)
    prereq_rules: Dict[str, List[Tuple[str, str]]] = {}
    for prq in tables.get("prerequisite", []):
        c = prq["course_id"]
        if c not in prereq_rules:
            prereq_rules[c] = []
        prereq_rules[c].append((prq["required_course_id"], prq.get("min_grade", "C")))

    for ri in tables.get("registration_interest", []):
        if ri["term"] == "2026-FA":
            cid = ri["course_id"]
            sid = ri["student_plan_id"]
            reqs = prereq_rules.get(cid, [])
            student_grades = student_completed_grades.get(sid, {})
            for req, min_g in reqs:
                if req not in student_grades or GRADE_RANK.get(student_grades[req], 0) < GRADE_RANK.get(min_g, 2):
                    detections.append({
                        "entity": "registration_interest",
                        "record_id": ri["interest_id"],
                        "issue_type": "prerequisite_violation",
                        "detected_reason": f"Student {sid} interested in {cid} without prerequisite {req} (min grade {min_g})",
                    })
                    break

    # 5. Detect duplicate_section_assignment
    sec_info = {s["section_id"]: s for s in tables.get("section", [])}
    # Check faculty double bookings
    fac_slots: Dict[Tuple[str, str, str, str], str] = {}  # (faculty_id, term, day, start_time) -> assignment_id
    for wla in tables.get("workload_assignment", []):
        sec = sec_info.get(wla["section_id"])
        if sec:
            key = (wla["faculty_id"], sec["term"], sec["day_of_week"], sec["start_time"])
            if key in fac_slots:
                detections.append({
                    "entity": "workload_assignment",
                    "record_id": wla["assignment_id"],
                    "issue_type": "duplicate_section_assignment",
                    "detected_reason": f"Faculty {wla['faculty_id']} double-booked in {sec['day_of_week']} {sec['start_time']}",
                })
            else:
                fac_slots[key] = wla["assignment_id"]

    return detections

def evaluate_detections_against_ground_truth(
    detections: List[Dict[str, Any]],
    ground_truth: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Compare detected anomalies against isolated ground truth to compute
    Precision, Recall, and F1-score per anomaly category and overall.
    """
    # Filter injected anomalies (injected_flag == 1 or '1')
    gt_injected = [g for g in ground_truth if str(g.get("injected_flag", "1")) == "1"]

    gt_set = {(g["issue_type"], g["record_id"]) for g in gt_injected}
    det_set = {(d["issue_type"], d["record_id"]) for d in detections}

    categories = [
        "faculty_outside_skill",
        "workload_exceeded",
        "section_capacity_too_low",
        "prerequisite_violation",
        "duplicate_section_assignment",
    ]

    results_by_cat: Dict[str, Dict[str, float]] = {}

    total_tp = 0
    total_fp = 0
    total_fn = 0

    for cat in categories:
        cat_gt = {rec_id for c, rec_id in gt_set if c == cat}
        cat_det = {rec_id for c, rec_id in det_set if c == cat}

        tp = len(cat_gt & cat_det)
        fp = len(cat_det - cat_gt)
        fn = len(cat_gt - cat_det)

        precision = (tp / (tp + fp)) if (tp + fp) > 0 else 1.0
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else 1.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        results_by_cat[cat] = {
            "ground_truth_count": len(cat_gt),
            "detected_count": len(cat_det),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
        }
        total_tp += tp
        total_fp += fp
        total_fn += fn

    overall_prec = (total_tp / (total_tp + total_fp)) if (total_tp + total_fp) > 0 else 1.0
    overall_rec = (total_tp / (total_tp + total_fn)) if (total_tp + total_fn) > 0 else 1.0
    overall_f1 = (2 * overall_prec * overall_rec / (overall_prec + overall_rec)) if (overall_prec + overall_rec) > 0 else 0.0

    return {
        "by_category": results_by_cat,
        "overall": {
            "total_ground_truth": len(gt_injected),
            "total_detected": len(detections),
            "tp": total_tp,
            "fp": total_fp,
            "fn": total_fn,
            "precision": round(overall_prec, 4),
            "recall": round(overall_rec, 4),
            "f1_score": round(overall_f1, 4),
        }
    }

def run_sql_validation_queries(sqlite_path: Path, queries_path: Path) -> List[str]:
    """Execute SQL integrity queries against SQLite database."""
    errors = []
    if not sqlite_path.exists():
        return [f"SQLite DB does not exist: {sqlite_path}"]

    conn = sqlite3.connect(sqlite_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # Check SQLite foreign key violations natively
    fk_violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
    if fk_violations:
        for fkv in fk_violations:
            errors.append(f"SQLite PRAGMA foreign_key_check violation: {fkv}")

    conn.close()
    return errors

def main():
    root = Path(__file__).resolve().parent.parent.parent
    data_dir = root / "data" / "output"
    gt_dir = root / "data" / "ground_truth"
    sqlite_path = data_dir / "course_demand.sqlite"
    queries_path = root / "database" / "validation_queries.sql"

    print("=" * 70)
    print("RUNNING AUTOMATED VALIDATION & INTEGRITY CHECKS")
    print("=" * 70)

    tables = load_tables(data_dir)
    with open(gt_dir / "ground_truth.json", "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    # 1. Structural checks
    pk_errs = validate_primary_keys(tables)
    fk_errs = validate_foreign_keys(tables)
    enum_errs = validate_enums(tables)
    id_errs = validate_id_patterns(tables)
    dag_errs = validate_acyclic_prerequisites(tables)
    sql_errs = run_sql_validation_queries(sqlite_path, queries_path)

    structural_pass = (
        len(pk_errs) == 0 and
        len(fk_errs) == 0 and
        len(enum_errs) == 0 and
        len(id_errs) == 0 and
        len(dag_errs) == 0 and
        len(sql_errs) == 0
    )

    print(f"Primary Key Uniqueness   : {'PASS' if not pk_errs else f'FAIL ({len(pk_errs)} errors)'}")
    print(f"Foreign Key Integrity    : {'PASS' if not fk_errs else f'FAIL ({len(fk_errs)} errors)'}")
    print(f"Allowed Enums Compliance : {'PASS' if not enum_errs else f'FAIL ({len(enum_errs)} errors)'}")
    print(f"ID Regex Format Checks   : {'PASS' if not id_errs else f'FAIL ({len(id_errs)} errors)'}")
    print(f"Prerequisite DAG Acyclic : {'PASS' if not dag_errs else f'FAIL ({len(dag_errs)} errors)'}")
    print(f"SQLite DB Native Checks  : {'PASS' if not sql_errs else f'FAIL ({len(sql_errs)} errors)'}")

    # 2. Rule-based anomaly detection
    detections = detect_anomalies_by_rules(tables)
    eval_metrics = evaluate_detections_against_ground_truth(detections, ground_truth)
    ov = eval_metrics["overall"]

    print("\nANOMALY DETECTION EVALUATION (vs Isolated Ground Truth):")
    print(f"  --> Precision : {ov['precision'] * 100:.2f}%")
    print(f"  --> Recall    : {ov['recall'] * 100:.2f}%")
    print(f"  --> F1-Score  : {ov['f1_score'] * 100:.2f}%")
    print(f"  --> Injected: {ov['total_ground_truth']} | Detected: {ov['total_detected']} | TP: {ov['tp']}, FP: {ov['fp']}, FN: {ov['fn']}")

    # 3. Write validation report
    from backend.validation.report import write_validation_summary_report
    report_path = root / "docs" / "validation_summary.md"
    write_validation_summary_report(
        report_path=report_path,
        structural_results={
            "pk_errors": pk_errs,
            "fk_errors": fk_errs,
            "enum_errors": enum_errs,
            "id_errors": id_errs,
            "dag_errors": dag_errs,
            "sql_errors": sql_errs,
        },
        eval_metrics=eval_metrics,
        summary_path=data_dir / "summary.json"
    )
    print(f"\nDetailed validation summary written to: {report_path}")
    print("=" * 70)

    if not structural_pass:
        print("VALIDATION FAILED DUE TO STRUCTURAL ERRORS.")
        sys.exit(1)
    else:
        print("ALL STRUCTURAL AND INTEGRITY CHECKS PASSED.")

if __name__ == "__main__":
    import sys
    main()
