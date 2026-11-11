"""
Master data generator for university programs, courses, prerequisites,
faculty, faculty skills, availability, and rooms.

Determinism:
Uses random.Random(seed + SEED_OFFSETS['master_data']). No wall-clock timestamps.
"""

import random
from typing import Dict, List, Tuple, Any
from backend.generator.config import (
    ScaleConfig,
    SEED_OFFSETS,
    DEPARTMENTS,
    ROOM_CAPACITIES,
    ROOM_TYPES,
    TIME_SLOTS,
    AS_OF_DATE,
    ALL_TERMS,
)
from backend.generator.ids import (
    make_program_id,
    make_course_id,
    make_prerequisite_id,
    make_faculty_id,
    make_availability_id,
    make_room_id,
)

# Realistic subject names per department
DEPT_SUBJECTS: Dict[str, List[str]] = {
    "Computer Science": [
        "Intro to Programming", "Data Structures", "Algorithms", "Operating Systems",
        "Computer Networks", "Database Systems", "Software Engineering", "Artificial Intelligence",
        "Machine Learning", "Distributed Systems", "Cloud Computing", "Computer Architecture",
        "Cybersecurity", "Computer Graphics", "Compilers", "Web Development",
    ],
    "Data Science": [
        "Data Mining", "Applied Statistics", "Deep Learning", "Natural Language Processing",
        "Big Data Analytics", "Data Visualization", "Predictive Modeling", "Time Series Analysis",
        "Reinforcement Learning", "Data Engineering", "Bayesian Statistics", "MLOps",
    ],
    "Electrical Engineering": [
        "Circuit Analysis", "Signals and Systems", "Digital Logic Design", "Electromagnetics",
        "Microprocessors", "Control Systems", "VLSI Design", "Communication Systems",
        "Power Electronics", "Semiconductor Devices", "Embedded Systems", "Robotics Control",
    ],
    "Mathematics": [
        "Calculus I", "Calculus II", "Linear Algebra", "Differential Equations",
        "Discrete Mathematics", "Probability Theory", "Real Analysis", "Numerical Analysis",
        "Abstract Algebra", "Complex Variables", "Optimization Methods", "Topology",
    ],
    "Business Analytics": [
        "Business Statistics", "Operations Research", "Decision Modeling", "Marketing Analytics",
        "Financial Analytics", "Supply Chain Analytics", "Simulation Modeling", "Risk Analytics",
        "Managerial Economics", "Data-Driven Strategy", "Customer Analytics", "Pricing Analytics",
    ],
    "Information Systems": [
        "Enterprise Systems", "IT Project Management", "Business Process Modeling",
        "Information Security", "Systems Analysis & Design", "Cloud Infrastructure",
        "IT Governance", "E-Commerce Technologies", "IT Auditing", "Knowledge Management",
    ],
    "Economics": [
        "Microeconomics", "Macroeconomics", "Econometrics", "Game Theory",
        "Behavioral Economics", "Public Finance", "International Trade", "Monetary Policy",
        "Labor Economics", "Industrial Organization", "Health Economics", "Development Economics",
    ],
    "Mechanical Engineering": [
        "Statics", "Dynamics", "Thermodynamics", "Fluid Mechanics",
        "Mechanics of Materials", "Heat Transfer", "Mechanical Design", "Mechatronics",
        "Finite Element Analysis", "Manufacturing Processes", "Kinematics", "Vibrations",
    ],
}

FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Margaret",
    "Matthew", "Lisa", "Anthony", "Betty", "Donald", "Dorothy", "Mark", "Sandra",
    "Paul", "Ashley", "Steven", "Kimberly", "Andrew", "Donna", "Kenneth", "Emily",
    "Joshua", "Michelle", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa",
    "Edward", "Deborah", "Ronald", "Stephanie", "Timothy", "Rebecca", "Jason", "Sharon",
    "Jeffrey", "Laura", "Ryan", "Cynthia", "Jacob", "Kathleen", "Gary", "Amy",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
    "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
    "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young",
    "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker",
]

BUILDINGS = ["Turing Hall", "Von Neumann Center", "Shannon Hall", "Euler Science Tower", "Curie Labs"]

def generate_master_data(
    seed: int,
    scale: ScaleConfig
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generate all university master entities:
    - Programs
    - Courses
    - ProgramCourse
    - Prerequisites (guaranteed acyclic DAG)
    - Faculty
    - FacultySkill
    - Availability
    - Rooms
    """
    rng = random.Random(seed + SEED_OFFSETS["master_data"])

    # -------------------------------------------------------------------------
    # 1. Programs
    # -------------------------------------------------------------------------
    programs: List[Dict[str, Any]] = []
    dept_cycle = list(DEPARTMENTS)
    for p_idx in range(1, scale.num_programs + 1):
        pid = make_program_id(p_idx)
        dept = dept_cycle[(p_idx - 1) % len(dept_cycle)]
        level = "Undergraduate" if (p_idx % 3 != 0) else "Graduate"
        prefix = "B.S. in " if level == "Undergraduate" else "M.S. in "
        name = f"{prefix}{dept} (Spec #{p_idx})"
        programs.append({
            "program_id": pid,
            "name": name,
            "level": level,
            "department": dept,
            "status": "active",
            "effective_from": "2020-01-01",
            "effective_to": "2030-12-31",
        })

    # -------------------------------------------------------------------------
    # 2. Courses
    # -------------------------------------------------------------------------
    courses: List[Dict[str, Any]] = []
    # Distribution: ~8% popular_elective, ~12% low_enrollment, rest core/standard
    num_popular = max(1, int(scale.num_courses * 0.08))
    num_low = max(1, int(scale.num_courses * 0.12))
    num_core = int(scale.num_courses * 0.35)
    
    categories = (
        ["popular_elective"] * num_popular +
        ["low_enrollment"] * num_low +
        ["core"] * num_core
    )
    # Fill remaining with 'standard'
    remaining = scale.num_courses - len(categories)
    if remaining > 0:
        categories.extend(["standard"] * remaining)
    rng.shuffle(categories)

    # Department abbreviations
    dept_abbr = {
        "Computer Science": "CS",
        "Data Science": "DS",
        "Electrical Engineering": "EE",
        "Mathematics": "MATH",
        "Business Analytics": "BA",
        "Information Systems": "IS",
        "Economics": "ECON",
        "Mechanical Engineering": "ME",
    }

    course_dept_map: Dict[str, str] = {}
    courses_by_dept: Dict[str, List[str]] = {d: [] for d in DEPARTMENTS}
    dept_course_counters: Dict[str, int] = {d: 0 for d in DEPARTMENTS}
    course_level_map: Dict[str, int] = {}

    for c_idx in range(1, scale.num_courses + 1):
        cid = make_course_id(c_idx)
        cat = categories[c_idx - 1]
        dept = dept_cycle[(c_idx - 1) % len(dept_cycle)]
        course_dept_map[cid] = dept
        courses_by_dept[dept].append(cid)
        dept_course_counters[dept] += 1

        # Level: 100, 200, 300, 400 for undergrad, 500, 600 for grad
        level_tier = rng.choice([100, 200, 300, 400, 500, 600])
        code = f"{dept_abbr[dept]}-{level_tier}-{dept_course_counters[dept]:03d}"
        course_level_map[cid] = level_tier

        # Title
        dept_pool = DEPT_SUBJECTS.get(dept, ["Advanced Topics"])
        base_title = dept_pool[(c_idx - 1) % len(dept_pool)]
        title = f"{base_title} {c_idx}" if c_idx > len(dept_pool) else base_title
        credits = 4 if level_tier >= 400 else 3
        contact_hours = float(credits)

        courses.append({
            "course_id": cid,
            "code": code,
            "title": title,
            "credits": credits,
            "level": level_tier,
            "category": cat,
            "contact_hours_per_week": contact_hours,
            "status": "active",
        })

    # -------------------------------------------------------------------------
    # 3. ProgramCourse Bridge
    # -------------------------------------------------------------------------
    program_courses: List[Dict[str, Any]] = []
    # Link each program to courses in its department + common math/science courses
    for prg in programs:
        p_id = prg["program_id"]
        p_dept = prg["department"]
        dept_course_ids = courses_by_dept[p_dept]
        
        # Pick 6 to 15 courses for the program
        k = min(len(dept_course_ids), rng.randint(6, 15))
        selected_courses = rng.sample(dept_course_ids, k)
        
        for idx, cid in enumerate(selected_courses):
            req_type = "core" if idx < (k // 2) else "elective"
            rec_term = min(8, (idx % 8) + 1)
            program_courses.append({
                "program_id": p_id,
                "course_id": cid,
                "requirement_type": req_type,
                "recommended_term": rec_term,
            })

    # -------------------------------------------------------------------------
    # 4. Prerequisites (Guaranteed Acyclic DAG, prerequisite level <= course level)
    # -------------------------------------------------------------------------
    prerequisites: List[Dict[str, Any]] = []
    prq_idx = 1
    # Sort courses within each department by level to guarantee strictly acyclic edges
    for dept, dept_course_list in courses_by_dept.items():
        dept_courses_sorted = sorted(dept_course_list, key=lambda c: (course_level_map[c], c))
        # Form chains: higher level courses depend on lower level courses
        for i in range(1, len(dept_courses_sorted)):
            higher_course = dept_courses_sorted[i]
            # 40% probability of having a prerequisite
            if rng.random() < 0.40:
                # Pick a strictly lower index course
                prereq_pool = [
                    dept_courses_sorted[j]
                    for j in range(i)
                    if course_level_map[dept_courses_sorted[j]] <= course_level_map[higher_course]
                ]
                if prereq_pool:
                    required_course = rng.choice(prereq_pool)
                    prerequisites.append({
                        "prerequisite_id": make_prerequisite_id(prq_idx),
                        "course_id": higher_course,
                        "required_course_id": required_course,
                        "min_grade": rng.choice(["C", "B", "C"]),
                        "effective_from": "2020-01-01",
                        "effective_to": "2030-12-31",
                    })
                    prq_idx += 1

    # -------------------------------------------------------------------------
    # 5. Faculty & FacultySkill (each faculty 3-12 courses)
    # -------------------------------------------------------------------------
    faculty: List[Dict[str, Any]] = []
    faculty_skills: List[Dict[str, Any]] = []

    for f_idx in range(1, scale.num_faculty + 1):
        fid = make_faculty_id(f_idx)
        dept = dept_cycle[(f_idx - 1) % len(dept_cycle)]
        emp_type = "full_time" if (f_idx % 4 != 0) else "adjunct"
        max_hours = 16.0 if emp_type == "full_time" else 8.0
        fname = rng.choice(FIRST_NAMES)
        lname = rng.choice(LAST_NAMES)
        status = "active" if (f_idx % 20 != 0) else "on_leave"

        faculty.append({
            "faculty_id": fid,
            "name": f"Dr. {fname} {lname}",
            "department": dept,
            "employment_type": emp_type,
            "max_weekly_hours": max_hours,
            "status": status,
        })

        # Skills: 3 to 12 courses primarily in their department
        dept_courses = courses_by_dept[dept]
        if dept_courses:
            num_skills = min(len(dept_courses), rng.randint(3, 12))
            assigned_courses = rng.sample(dept_courses, num_skills)
            for cid in assigned_courses:
                proficiency = rng.choice([1, 2, 2, 3])
                faculty_skills.append({
                    "faculty_id": fid,
                    "course_id": cid,
                    "proficiency": proficiency,
                    "certified_from": "2022-01-15",
                })

    # -------------------------------------------------------------------------
    # 6. Faculty Availability & Leave Blocks
    # -------------------------------------------------------------------------
    availability: List[Dict[str, Any]] = []
    avl_idx = 1
    for fac in faculty:
        fid = fac["faculty_id"]
        is_leave = (fac["status"] == "on_leave")
        
        for term in ALL_TERMS:
            if is_leave:
                availability.append({
                    "availability_id": make_availability_id(avl_idx),
                    "faculty_id": fid,
                    "term": term,
                    "day_of_week": "MWF",
                    "start_time": "08:00:00",
                    "end_time": "17:00:00",
                    "availability_type": "leave",
                })
                avl_idx += 1
            else:
                # Regular faculty available across MWF or TTH slots
                # Give 4-6 time slots of availability
                slots_sample = rng.sample(TIME_SLOTS, rng.randint(5, len(TIME_SLOTS)))
                for slot in slots_sample:
                    availability.append({
                        "availability_id": make_availability_id(avl_idx),
                        "faculty_id": fid,
                        "term": term,
                        "day_of_week": slot["day_of_week"],
                        "start_time": slot["start_time"],
                        "end_time": slot["end_time"],
                        "availability_type": "available",
                    })
                    avl_idx += 1

    # -------------------------------------------------------------------------
    # 7. Rooms
    # -------------------------------------------------------------------------
    rooms: List[Dict[str, Any]] = []
    for r_idx in range(1, scale.num_rooms + 1):
        rid = make_room_id(r_idx)
        bldg = BUILDINGS[(r_idx - 1) % len(BUILDINGS)]
        cap = ROOM_CAPACITIES[(r_idx - 1) % len(ROOM_CAPACITIES)]
        rtype = ROOM_TYPES[(r_idx - 1) % len(ROOM_TYPES)]
        available_slots = len(TIME_SLOTS)

        rooms.append({
            "room_id": rid,
            "building": f"{bldg} Room {100 + r_idx}",
            "capacity": cap,
            "room_type": rtype,
            "available_slots": available_slots,
        })

    return {
        "program": programs,
        "course": courses,
        "program_course": program_courses,
        "prerequisite": prerequisites,
        "faculty": faculty,
        "faculty_skill": faculty_skills,
        "availability": availability,
        "room": rooms,
    }
