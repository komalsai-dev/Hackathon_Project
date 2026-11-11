"""
Reproducibility test:
Runs the generator twice with the identical master seed (20261022) into two isolated
temporary directories.
Asserts:
1. Exact identical SHA-256 checksums across all CSV, JSON, and seed.sql files.
2. Exact row-for-row match across all tables in SQLite database.
"""

import hashlib
import sqlite3
import shutil
from pathlib import Path
import tempfile
import pytest

from backend.generator.run import run_pipeline

def compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def test_deterministic_reproducibility(tmp_path):
    run1_dir = tmp_path / "run1"
    run2_dir = tmp_path / "run2"

    seed = 20261022
    scale = "starter"

    # Execute Run 1
    run_pipeline(seed=seed, scale_name=scale, base_dir=run1_dir)

    # Execute Run 2
    run_pipeline(seed=seed, scale_name=scale, base_dir=run2_dir)

    # 1. Compare SHA-256 for all CSV and JSON files in data/output
    run1_output = run1_dir / "data" / "output"
    run2_output = run2_dir / "data" / "output"

    csv_files = sorted([f.name for f in run1_output.glob("*.csv")])
    assert len(csv_files) > 0, "No CSV files produced in run 1"

    for fname in csv_files:
        f1 = run1_output / fname
        f2 = run2_output / fname
        assert f2.exists(), f"File {fname} missing in run 2"
        hash1 = compute_sha256(f1)
        hash2 = compute_sha256(f2)
        assert hash1 == hash2, f"SHA-256 mismatch for CSV {fname}: {hash1} != {hash2}"

    json_files = sorted([f.name for f in run1_output.glob("*.json")])
    for fname in json_files:
        f1 = run1_output / fname
        f2 = run2_output / fname
        assert f2.exists(), f"File {fname} missing in run 2"
        hash1 = compute_sha256(f1)
        hash2 = compute_sha256(f2)
        assert hash1 == hash2, f"SHA-256 mismatch for JSON {fname}: {hash1} != {hash2}"

    # 2. Compare seed.sql SHA-256
    s1 = run1_dir / "database" / "seed" / "seed.sql"
    s2 = run2_dir / "database" / "seed" / "seed.sql"
    assert s1.exists() and s2.exists()
    assert compute_sha256(s1) == compute_sha256(s2), "seed.sql checksum mismatch between runs"

    # 3. Compare SQLite database by table contents (as requested)
    db1_path = run1_output / "course_demand.sqlite"
    db2_path = run2_output / "course_demand.sqlite"
    assert db1_path.exists() and db2_path.exists()

    conn1 = sqlite3.connect(db1_path)
    conn2 = sqlite3.connect(db2_path)

    tables1 = [r[0] for r in conn1.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;").fetchall()]
    tables2 = [r[0] for r in conn2.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;").fetchall()]
    assert tables1 == tables2, f"SQLite tables mismatch: {tables1} != {tables2}"

    for t in tables1:
        rows1 = conn1.execute(f"SELECT * FROM {t};").fetchall()
        rows2 = conn2.execute(f"SELECT * FROM {t};").fetchall()
        assert len(rows1) == len(rows2), f"Row count mismatch in table {t}: {len(rows1)} vs {len(rows2)}"
        assert rows1 == rows2, f"Row content mismatch in SQLite table {t}"

    conn1.close()
    conn2.close()

