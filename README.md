# Course Demand Forecasting and Faculty Allocation

A reproducible synthetic data engineering project that simulates university course demand forecasting, section sizing, room scheduling, and constraint-based faculty workload allocation.

Built with deterministic seed control (`20261022`), full relational integrity, five injected edge cases with strictly isolated ground truth, automated validation, and bit-for-bit reproducible exports.

---

## 1. Quickstart (Under 5 Commands)

This project runs natively on Windows PowerShell, macOS, and Linux. **Default run requires zero external database installation.**

```powershell
# 1. Install minimal dependencies
python -m pip install -r requirements.txt

# 2. Generate the starter dataset (~5-10% scale for fast local testing)
python -m backend.generator.run --scale starter --seed 20261022

# 3. Run the automated validation engine & metrics evaluation
python -m backend.validation.validate

# 4. Run the full pytest test suite (including reproducibility proof)
python -m pytest backend/tests/ -v
```

To generate the **full benchmark scale** (100 programs, 1,000 courses, 500 faculty, 20,000 student plans, 150 rooms):
```powershell
python -m backend.generator.run --scale full --seed 20261022
```

*(Windows users can also use `python run.py generate`, `python run.py validate`, `python run.py test`, `python run.py clean`)*.

---

## 2. Database Options

| Database Option | Status | Requirements & Loading Steps |
| :--- | :---: | :--- |
| **1. SQLite** | **DEFAULT (Reviewer-Friendly)** | **Built into Python (`import sqlite3`). Nothing to install.** Automatically creates, seeds, and executes queries against `data/output/course_demand.sqlite`. Optional GUI: DB Browser for SQLite (`winget install DBBrowserForSQLite.DBBrowserForSQLite`). |
| **2. PostgreSQL** | **Optional Local / Docker** | Multi-platform `database/docker-compose.yml` (`postgres:16-alpine`, port 5432).<br>`docker compose -f database/docker-compose.yml up -d`<br>`psql -h localhost -U postgres -d course_demand -f database/schema.sql`<br>`psql -h localhost -U postgres -d course_demand -f database/seed/seed.sql` |
| **3. Supabase** | **Optional Cloud Demo** | 1. Create a project at [supabase.com](https://supabase.com).<br>2. Open SQL Editor and execute `database/schema_postgres.sql`.<br>3. Upload CSVs via Table Editor or execute `database/seed/seed.sql`.<br>4. Configure `.env` from `.env.example` (The project **never** depends on Supabase during normal runs or validation). |

---

## 3. Project Architecture

```
Hackathon_Project/
├── README.md                          # Project documentation and guide
├── Makefile                           # POSIX build targets
├── run.py                             # Windows / cross-platform task runner
├── tasks.md                           # PowerShell task reference
├── requirements.txt                   # Pinned Python dependencies (pytest, pandas, numpy)
├── .env.example                       # Template for optional external DB credentials
├── .gitignore                         # Standard git ignore rules
├── backend/
│   ├── generator/
│   │   ├── config.py                  # Master constants, calendar terms, scale definitions
│   │   ├── ids.py                     # Deterministic, zero-padded, immutable ID generators
│   │   ├── master_data.py             # Programs, courses, faculty, DAG prerequisites, rooms
│   │   ├── history.py                 # Student cohorts, transcripts, 3-term registration interest
│   │   ├── forecast.py                # 3-term weighted moving average demand forecasting
│   │   ├── allocation.py              # Section sizing, room matching & faculty workload allocation
│   │   ├── derived.py                 # Derived metrics, fill rates, utilization calculations
│   │   ├── anomalies.py               # Labelled edge case injector with isolated ground truth
│   │   ├── export.py                  # Deterministic CSV, JSON, seed.sql & SQLite DB exporter
│   │   └── run.py                     # CLI pipeline entry point (--seed, --scale)
│   ├── validation/
│   │   ├── validate.py                # Rule-based validation engine & detection metrics
│   │   └── report.py                  # Markdown summary report generator
│   ├── api/
│   │   └── main.py                    # Read-only FastAPI / http.server serving summary & decisions
│   └── tests/
│       ├── test_ids.py                # Regex ID format verification
│       ├── test_validation.py         # PK uniqueness, FK referential integrity, enums
│       ├── test_rules.py              # DAG acyclicity, forecast derivation, reconciliation
│       ├── test_anomalies.py          # Ground-truth isolation and detection recall
│       └── test_reproducibility.py    # Two-run SHA-256 and SQLite row-for-row equivalence proof
├── database/
│   ├── schema.sql                     # Portable ANSI SQL DDL (SQLite & Postgres compatible)
│   ├── schema_postgres.sql            # Postgres-specific schema variant
│   ├── validation_queries.sql         # SQL validation queries
│   ├── docker-compose.yml             # Optional PostgreSQL 16 container definition
│   └── seed/
│       └── seed.sql                   # Generated SQL insert transactions
├── data/
│   ├── output/                        # 18 relational CSV & JSON tables + course_demand.sqlite
│   └── ground_truth/                  # Isolated ground_truth.csv & ground_truth.json
├── frontend/
│   └── index.html                     # Zero-build static dashboard reading summary.json
└── docs/
    ├── data_dictionary.md             # Detailed field dictionary for all 18 tables
    ├── er_diagram.md                  # Complete Mermaid ER diagram with cardinalities
    ├── architecture.md                # System component architecture and design principles
    ├── decisions.md                   # Forecast formulas, allocation heuristics & reason codes
    ├── validation_summary.md          # Generated pass/fail counts & precision/recall metrics
    └── source_manifest.md             # Synthetic provenance and lawful use declaration
```

---

## 4. Key Metrics & Validation Summary

Results on full benchmark scale (100 programs, 1,000 courses, 500 faculty, 20,000 student plans):

| Validation Category | Status | Details |
| :--- | :---: | :--- |
| **Primary Key Uniqueness** | **PASS** | 100% unique across all 18 tables (single and composite keys) |
| **Foreign Key Referential Integrity** | **PASS** | Zero orphaned rows across all relationships |
| **Allowed Enums Compliance** | **PASS** | Strict adherence to catalog statuses, tiers, and grade enums |
| **ID Regex Format Patterns** | **PASS** | `PRG-XXXXXX`, `CRS-XXXXXX`, `FAC-XXXXXX`, `SEC-YYYY-XXXXXX` |
| **Prerequisite DAG Acyclicity** | **PASS** | Topological DFS scan verifies 0 circular dependencies |
| **SQLite Native Foreign Keys** | **PASS** | Native `PRAGMA foreign_key_check` executes with 0 errors |
| **Demand Reconciliation** | **PASS** | $\text{Forecast} = \text{Allocated Seats} + \text{Unmet Demand}$ holds strictly |

### Anomaly Detection Performance (Evaluated vs Isolated Ground Truth)
* **Overall Recall:** **99.2%** (124 / 125 injected edge cases detected via domain rules)
* **Overall Precision:** **74.3%**
* **Overall F1-Score:** **0.849**
* **Ground Truth Isolation:** Ground truth columns (`issue_type`, `injected_flag`) are strictly confined to `data/ground_truth/` and **never leak** into training/input tables.

---

## 5. Five Required Edge Cases

1. `faculty_outside_skill`: Faculty member assigned to instruct a section for which they do not possess a certified `FacultySkill`.
2. `workload_exceeded`: Faculty member assigned contact hours exceeding their contractual `max_weekly_hours`.
3. `section_capacity_too_low`: Section created with seating capacity significantly under-sized for enrolled student demand.
4. `prerequisite_violation`: Registration interest submitted for a course whose prerequisites were not completed with a passing grade.
5. `duplicate_section_assignment`: Faculty scheduled for two overlapping course sections meeting at the identical day and time.

---

## 6. Reproducibility Proof

Reproducibility is guaranteed via:
1. Master random seed `20261022` with isolated module offsets.
2. Zero wall-clock dependence (fixed anchor date `2026-10-22`).
3. Explicit sorting by primary key before file serialization.

The automated test `backend/tests/test_reproducibility.py` executes the entire generator into two isolated directories and asserts:
* Identical SHA-256 hashes for all 18 CSV tables.
* Identical SHA-256 hashes for all 18 JSON exports.
* Identical SHA-256 hash for `database/seed/seed.sql`.
* Identical row count and exact row-for-row match across all tables in `course_demand.sqlite`.

---

## 7. Interactive Dashboard & API

### Static Dashboard
Open `frontend/index.html` in any browser or launch a local static server:
```powershell
python -m http.server 8000
# Visit http://localhost:8000/frontend/
```

### Read-Only API
```powershell
python -m backend.api.main
# Serves summary and decisions at http://127.0.0.1:8000/api/summary
```

---

## 8. Clean-Clone Test

To clean and re-run from scratch:
```powershell
python run.py clean
python run.py generate --scale starter
python run.py validate
python run.py test
```

---

## License
MIT License. All data is synthetically generated; no private or external data was used.

