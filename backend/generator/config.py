"""
Global configuration and constants for the Course Demand Forecasting
and Faculty Allocation synthetic dataset generator.
"""

from dataclasses import dataclass
from typing import List, Dict

# Master seed for deterministic generation
MASTER_SEED = 20261022

# Fixed reference timeline (no datetime.now() or wall-clock dependence)
AS_OF_DATE = "2026-10-22"
TARGET_TERM = "2026-FA"
HISTORICAL_TERMS: List[str] = ["2025-FA", "2026-SP", "2026-SU"]
ALL_TERMS: List[str] = HISTORICAL_TERMS + [TARGET_TERM]

# Term start and end dates
TERM_DATES: Dict[str, Dict[str, str]] = {
    "2025-FA": {"start": "2025-08-25", "end": "2025-12-15"},
    "2026-SP": {"start": "2026-01-12", "end": "2026-05-08"},
    "2026-SU": {"start": "2026-06-01", "end": "2026-08-07"},
    "2026-FA": {"start": "2026-08-24", "end": "2026-12-14"},
}

# Standard time slots for courses (Monday/Wednesday/Friday or Tuesday/Thursday)
TIME_SLOTS = [
    {"day_of_week": "MWF", "start_time": "08:00:00", "end_time": "08:50:00", "hours": 3.0},
    {"day_of_week": "MWF", "start_time": "09:00:00", "end_time": "09:50:00", "hours": 3.0},
    {"day_of_week": "MWF", "start_time": "10:00:00", "end_time": "10:50:00", "hours": 3.0},
    {"day_of_week": "MWF", "start_time": "11:00:00", "end_time": "11:50:00", "hours": 3.0},
    {"day_of_week": "MWF", "start_time": "13:00:00", "end_time": "13:50:00", "hours": 3.0},
    {"day_of_week": "MWF", "start_time": "14:00:00", "end_time": "14:50:00", "hours": 3.0},
    {"day_of_week": "TTH", "start_time": "08:30:00", "end_time": "09:45:00", "hours": 3.0},
    {"day_of_week": "TTH", "start_time": "10:00:00", "end_time": "11:15:00", "hours": 3.0},
    {"day_of_week": "TTH", "start_time": "13:00:00", "end_time": "14:15:00", "hours": 3.0},
    {"day_of_week": "TTH", "start_time": "14:30:00", "end_time": "15:45:00", "hours": 3.0},
]

# Room capacity options
ROOM_CAPACITIES = [20, 30, 40, 60, 120]
ROOM_TYPES = ["lecture_hall", "classroom", "seminar", "computer_lab"]

# Course categories distribution: ~8% popular electives, ~12% low-enrollment, rest standard/core
COURSE_CATEGORIES = {
    "core": 0.35,
    "standard": 0.45,
    "popular_elective": 0.08,
    "low_enrollment": 0.12,
}

# Academic departments
DEPARTMENTS = [
    "Computer Science",
    "Data Science",
    "Electrical Engineering",
    "Mathematics",
    "Business Analytics",
    "Information Systems",
    "Economics",
    "Mechanical Engineering",
]

# Forecast parameters
FORECAST_WEIGHTS = [0.2, 0.3, 0.5]  # for [H1 (2025-FA), H2 (2026-SP), H3 (2026-SU)]
POPULAR_ELECTIVE_BOOST = 1.30
LOW_ENROLLMENT_DAMPENER = 0.65

# Scale configurations
@dataclass(frozen=True)
class ScaleConfig:
    num_programs: int
    num_courses: int
    num_faculty: int
    num_student_plans: int
    num_rooms: int

SCALE_CONFIGS = {
    "starter": ScaleConfig(
        num_programs=10,
        num_courses=100,
        num_faculty=50,
        num_student_plans=1500,
        num_rooms=30,
    ),
    "full": ScaleConfig(
        num_programs=100,
        num_courses=1000,
        num_faculty=500,
        num_student_plans=20000,
        num_rooms=150,
    ),
}

# Module seed offsets (to guarantee independence while preserving master seed determinism)
SEED_OFFSETS = {
    "master_data": 100,
    "history": 200,
    "forecast": 300,
    "allocation": 400,
    "anomalies": 500,
}

