"""
Tests for structural validation and SQLite database integrity.
"""

import sqlite3
from pathlib import Path
from backend.validation.validate import (
    load_tables,
    validate_primary_keys,
    validate_foreign_keys,
    validate_enums,
    validate_id_patterns,
    validate_acyclic_prerequisites,
    run_sql_validation_queries,
)

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "output"
SQLITE_PATH = DATA_DIR / "course_demand.sqlite"
QUERIES_PATH = ROOT / "database" / "validation_queries.sql"

def test_primary_key_uniqueness():
    tables = load_tables(DATA_DIR)
    errors = validate_primary_keys(tables)
    assert len(errors) == 0, f"Primary key violations: {errors}"

def test_foreign_key_referential_integrity():
    tables = load_tables(DATA_DIR)
    errors = validate_foreign_keys(tables)
    assert len(errors) == 0, f"Foreign key violations: {errors}"

def test_allowed_enums_compliance():
    tables = load_tables(DATA_DIR)
    errors = validate_enums(tables)
    assert len(errors) == 0, f"Enum violations: {errors}"

def test_id_regex_formatting():
    tables = load_tables(DATA_DIR)
    errors = validate_id_patterns(tables)
    assert len(errors) == 0, f"ID format violations: {errors}"

def test_sqlite_native_foreign_keys():
    errors = run_sql_validation_queries(SQLITE_PATH, QUERIES_PATH)
    assert len(errors) == 0, f"SQLite errors: {errors}"

