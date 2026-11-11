"""
Deterministic exporter for CSV, JSON, SQLite, and SQL seed files.

Guarantees:
1. All rows sorted strictly by Primary Key before serializing.
2. Formats all NULL / NaN / types deterministically.
3. Inserts cleanly into SQLite via database/schema.sql.
4. Keeps data/ground_truth/ strictly isolated from data/output/.
"""

import csv
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any

# Primary keys for deterministic sorting
TABLE_PRIMARY_KEYS: Dict[str, Any] = {
    "program": lambda r: r["program_id"],
    "course": lambda r: r["course_id"],
    "program_course": lambda r: (r["program_id"], r["course_id"]),
    "prerequisite": lambda r: r["prerequisite_id"],
    "faculty": lambda r: r["faculty_id"],
    "faculty_skill": lambda r: (r["faculty_id"], r["course_id"]),
    "availability": lambda r: r["availability_id"],
    "room": lambda r: r["room_id"],
    "student_plan": lambda r: r["student_plan_id"],
    "student_plan_completed_course": lambda r: (r["student_plan_id"], r["course_id"]),
    "registration_interest": lambda r: r["interest_id"],
    "demand_forecast": lambda r: r["forecast_id"],
    "section": lambda r: r["section_id"],
    "section_event": lambda r: r["event_id"],
    "workload_assignment": lambda r: r["assignment_id"],
    "assignment_event": lambda r: r["event_id"],
    "unmet_demand": lambda r: r["unmet_id"],
    "decision_log": lambda r: r["decision_id"],
}

def export_all(
    all_tables: Dict[str, List[Dict[str, Any]]],
    ground_truth: List[Dict[str, Any]],
    summary_data: Dict[str, Any],
    output_dir: Path,
    ground_truth_dir: Path,
    seed_sql_path: Path,
    sqlite_db_path: Path,
    schema_sql_path: Path
) -> None:
    """
    Export all datasets to disk deterministically.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    ground_truth_dir.mkdir(parents=True, exist_ok=True)
    seed_sql_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Sort all tables by primary key
    sorted_tables: Dict[str, List[Dict[str, Any]]] = {}
    for table_name, rows in all_tables.items():
        sort_fn = TABLE_PRIMARY_KEYS.get(table_name)
        if sort_fn:
            sorted_tables[table_name] = sorted(rows, key=sort_fn)
        else:
            sorted_tables[table_name] = rows

    # 2. Export CSV and JSON for each table
    for table_name, rows in sorted_tables.items():
        csv_file = output_dir / f"{table_name}.csv"
        json_file = output_dir / f"{table_name}.json"

        if rows:
            fieldnames = list(rows[0].keys())
            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        else:
            csv_file.write_text("", encoding="utf-8")

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2)

    # 3. Export Summary JSON
    with open(output_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    # 4. Export Ground Truth (isolated)
    gt_sorted = sorted(ground_truth, key=lambda r: (r["entity"], r["record_id"], r["issue_type"]))
    gt_csv = ground_truth_dir / "ground_truth.csv"
    gt_json = ground_truth_dir / "ground_truth.json"

    if gt_sorted:
        with open(gt_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(gt_sorted[0].keys()))
            writer.writeheader()
            writer.writerows(gt_sorted)

    with open(gt_json, "w", encoding="utf-8") as f:
        json.dump(gt_sorted, f, indent=2)

    # 5. Export SQL Seed file (seed.sql)
    sql_lines: List[str] = [
        "-- Auto-generated deterministic seed data",
        "-- Run after schema.sql",
        "BEGIN TRANSACTION;\n"
    ]

    for table_name, rows in sorted_tables.items():
        if not rows:
            continue
        cols = list(rows[0].keys())
        col_names = ", ".join(cols)
        
        for r in rows:
            vals = []
            for col in cols:
                val = r[col]
                if val is None:
                    vals.append("NULL")
                elif isinstance(val, (int, float)):
                    vals.append(str(val))
                else:
                    # Escape single quotes
                    escaped = str(val).replace("'", "''")
                    vals.append(f"'{escaped}'")
            sql_lines.append(f"INSERT INTO {table_name} ({col_names}) VALUES ({', '.join(vals)});")

    sql_lines.append("\nCOMMIT;\n")
    with open(seed_sql_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sql_lines))

    # 6. Create SQLite Database & Load
    if sqlite_db_path.exists():
        sqlite_db_path.unlink()

    conn = sqlite3.connect(sqlite_db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    
    with open(schema_sql_path, "r", encoding="utf-8") as sf:
        schema_sql = sf.read()
    conn.executescript(schema_sql)

    # Insert data
    cursor = conn.cursor()
    for table_name, rows in sorted_tables.items():
        if not rows:
            continue
        cols = list(rows[0].keys())
        placeholders = ", ".join(["?"] * len(cols))
        stmt = f"INSERT INTO {table_name} ({', '.join(cols)}) VALUES ({placeholders})"
        row_tuples = [tuple(r[c] for c in cols) for r in rows]
        cursor.executemany(stmt, row_tuples)

    conn.commit()
    conn.close()

