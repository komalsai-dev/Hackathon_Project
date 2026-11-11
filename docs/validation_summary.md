# Validation Summary Report

This document details the automated data integrity, rule enforcement, and anomaly detection results.

## 1. Structural & Integrity Checks

| Check Category | Status | Details |
| :--- | :---: | :--- |
| Primary Key Uniqueness | **PASS** | Zero integrity violations detected. |
| Foreign Key Referential Integrity | **PASS** | Zero integrity violations detected. |
| Allowed Enums Compliance | **PASS** | Zero integrity violations detected. |
| ID Regex Format Patterns | **PASS** | Zero integrity violations detected. |
| Prerequisite DAG Acyclicity | **PASS** | Zero integrity violations detected. |
| SQLite Engine Native Foreign Keys | **PASS** | Zero integrity violations detected. |

## 2. Operational KPIs & Reconciliation

| KPI Metric | Value | Target / Benchmark |
| :--- | :---: | :--- |
| **Total Programs** | 100 | Configured scale volume |
| **Total Courses** | 1000 | 100% active curriculum |
| **Total Faculty** | 500 | Full-time & Adjunct mix |
| **Total Student Plans** | 20000 | Historical + active cohorts |
| **Forecast Demand** | 47830 | 3-term weighted moving average |
| **Allocated Seats** | 19001 | Scheduled in classrooms |
| **Unmet Demand** | 28829 | Explicitly recorded with reason codes |
| **Demand Fill Rate** | 39.7% | seats_allocated / forecast_demand |
| **Faculty Utilization** | 25.6% | assigned_hours / max_weekly_hours |
| **Reconciliation Identity** | **100% BALANCED** | `forecast = allocated + unmet` holds strictly |

## 3. Anomaly Detection Performance (vs Isolated Ground Truth)

The validation engine detects anomalies using **pure domain rules** without referencing the ground truth dataset.

| Anomaly Category | Injected (GT) | Detected | TP | FP | FN | Precision | Recall | F1-Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `faculty_outside_skill` | 25 | 25 | 25 | 0 | 0 | 100.0% | 100.0% | 1.0000 |
| `workload_exceeded` | 25 | 31 | 24 | 7 | 1 | 77.4% | 96.0% | 0.8571 |
| `section_capacity_too_low` | 25 | 47 | 25 | 22 | 0 | 53.2% | 100.0% | 0.6944 |
| `prerequisite_violation` | 25 | 25 | 25 | 0 | 0 | 100.0% | 100.0% | 1.0000 |
| `duplicate_section_assignment` | 25 | 39 | 25 | 14 | 0 | 64.1% | 100.0% | 0.7813 |
| **OVERALL TOTALS** | **125** | **167** | **124** | **43** | **1** | **74.2%** | **99.2%** | **0.8493** |

## 4. Evaluation Notes
- **Ground Truth Isolation:** `data/ground_truth/ground_truth.csv` and `.json` are located in a strictly isolated directory and are never loaded by the data generator or input tables.
- **Decision Explainability:** Every allocation and rejection decision is logged with structured reason codes and input snapshots in `decision_log`.
- **Zero Wall-Clock Dependence:** All dates, events, and timestamps originate from the fixed simulation calendar.
