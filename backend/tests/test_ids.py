"""
Unit tests for ID generators and pattern validators.
"""

import pytest
from backend.generator.ids import (
    make_program_id,
    make_course_id,
    make_prerequisite_id,
    make_faculty_id,
    make_availability_id,
    make_room_id,
    make_student_plan_id,
    make_student_ref,
    make_interest_id,
    make_forecast_id,
    make_section_id,
    make_section_event_id,
    make_assignment_id,
    make_assignment_event_id,
    make_unmet_id,
    make_decision_id,
    validate_id,
)

def test_id_formatting():
    assert make_program_id(1) == "PRG-000001"
    assert make_course_id(42) == "CRS-000042"
    assert make_prerequisite_id(999) == "PRQ-000999"
    assert make_faculty_id(5) == "FAC-000005"
    assert make_availability_id(12) == "AVL-000012"
    assert make_room_id(3) == "ROM-0003"
    assert make_student_plan_id(100) == "STP-000100"
    assert make_student_ref(77) == "STU-000077"
    assert make_interest_id(500) == "INT-000500"
    assert make_forecast_id(2026, 1) == "DFC-2026-000001"
    assert make_section_id(2026, 15) == "SEC-2026-000015"
    assert make_section_event_id(2026, 2) == "SEV-2026-000002"
    assert make_assignment_id(2026, 8) == "WLA-2026-000008"
    assert make_assignment_event_id(2026, 9) == "AEV-2026-000009"
    assert make_unmet_id(2026, 3) == "UMD-2026-000003"
    assert make_decision_id(2026, 7) == "DCL-2026-000007"

def test_id_validation_valid():
    assert validate_id("program_id", "PRG-000001")
    assert validate_id("course_id", "CRS-000042")
    assert validate_id("faculty_id", "FAC-000500")
    assert validate_id("section_id", "SEC-2026-000001")
    assert validate_id("assignment_id", "WLA-2026-000001")

def test_id_validation_invalid():
    assert not validate_id("program_id", "PRG-1")
    assert not validate_id("course_id", "CRS000001")
    assert not validate_id("faculty_id", "FAC-ABCDEF")
    assert not validate_id("section_id", "SEC-26-000001")

def test_unknown_id_type():
    with pytest.raises(ValueError):
        validate_id("non_existent_type", "XYZ-001")

