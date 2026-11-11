"""
Deterministic, zero-padded, immutable ID generators and validators.
Standard formats:
- Program: PRG-000001
- Course: CRS-000001
- Prerequisite: PRQ-000001
- Faculty: FAC-000001
- Availability: AVL-000001
- Room: ROM-0001
- StudentPlan: STP-000001
- StudentRef: STU-000001
- RegistrationInterest: INT-000001
- DemandForecast: DFC-2026-000001
- Section: SEC-2026-000001
- SectionEvent: SEV-2026-000001
- WorkloadAssignment: WLA-2026-000001
- AssignmentEvent: AEV-2026-000001
- UnmetDemand: UMD-2026-000001
- DecisionLog: DCL-2026-000001
"""

import re
from typing import Dict, Pattern

ID_PATTERNS: Dict[str, Pattern] = {
    "program_id": re.compile(r"^PRG-\d{6}$"),
    "course_id": re.compile(r"^CRS-\d{6}$"),
    "prerequisite_id": re.compile(r"^PRQ-\d{6}$"),
    "faculty_id": re.compile(r"^FAC-\d{6}$"),
    "availability_id": re.compile(r"^AVL-\d{6}$"),
    "room_id": re.compile(r"^ROM-\d{4}$"),
    "student_plan_id": re.compile(r"^STP-\d{6}$"),
    "student_ref": re.compile(r"^STU-\d{6}$"),
    "interest_id": re.compile(r"^INT-\d{6}$"),
    "forecast_id": re.compile(r"^DFC-\d{4}-\d{6}$"),
    "section_id": re.compile(r"^SEC-\d{4}-\d{6}$"),
    "section_event_id": re.compile(r"^SEV-\d{4}-\d{6}$"),
    "assignment_id": re.compile(r"^WLA-\d{4}-\d{6}$"),
    "assignment_event_id": re.compile(r"^AEV-\d{4}-\d{6}$"),
    "unmet_id": re.compile(r"^UMD-\d{4}-\d{6}$"),
    "decision_id": re.compile(r"^DCL-\d{4}-\d{6}$"),
}

def make_program_id(idx: int) -> str:
    return f"PRG-{idx:06d}"

def make_course_id(idx: int) -> str:
    return f"CRS-{idx:06d}"

def make_prerequisite_id(idx: int) -> str:
    return f"PRQ-{idx:06d}"

def make_faculty_id(idx: int) -> str:
    return f"FAC-{idx:06d}"

def make_availability_id(idx: int) -> str:
    return f"AVL-{idx:06d}"

def make_room_id(idx: int) -> str:
    return f"ROM-{idx:04d}"

def make_student_plan_id(idx: int) -> str:
    return f"STP-{idx:06d}"

def make_student_ref(idx: int) -> str:
    return f"STU-{idx:06d}"

def make_interest_id(idx: int) -> str:
    return f"INT-{idx:06d}"

def make_forecast_id(year: int, idx: int) -> str:
    return f"DFC-{year:04d}-{idx:06d}"

def make_section_id(year: int, idx: int) -> str:
    return f"SEC-{year:04d}-{idx:06d}"

def make_section_event_id(year: int, idx: int) -> str:
    return f"SEV-{year:04d}-{idx:06d}"

def make_assignment_id(year: int, idx: int) -> str:
    return f"WLA-{year:04d}-{idx:06d}"

def make_assignment_event_id(year: int, idx: int) -> str:
    return f"AEV-{year:04d}-{idx:06d}"

def make_unmet_id(year: int, idx: int) -> str:
    return f"UMD-{year:04d}-{idx:06d}"

def make_decision_id(year: int, idx: int) -> str:
    return f"DCL-{year:04d}-{idx:06d}"

def validate_id(id_type: str, id_value: str) -> bool:
    """Validate that an ID strictly conforms to its regex pattern."""
    pattern = ID_PATTERNS.get(id_type)
    if not pattern:
        raise ValueError(f"Unknown id_type: {id_type}")
    return bool(pattern.match(id_value))

