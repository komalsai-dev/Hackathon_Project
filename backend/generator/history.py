"""
Student plans, completed courses (historical transcripts), and registration
interest generation across historical and target terms.

Determinism:
Uses random.Random(seed + SEED_OFFSETS['history']). Prerequisite satisfaction
is checked before generating registration interest.
"""

import random
from typing import Dict, List, Set, Any
from backend.generator.config import (
    ScaleConfig,
    SEED_OFFSETS,
    HISTORICAL_TERMS,
    TARGET_TERM,
    ALL_TERMS,
    AS_OF_DATE,
)
from backend.generator.ids import (
    make_student_plan_id,
    make_student_ref,
    make_interest_id,
)

GRADES_WEIGHTED = [
    ("A", 0.35),
    ("B", 0.40),
    ("C", 0.18),
    ("D", 0.05),
    ("F", 0.02),
]

GRADE_RANK = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}

def pick_grade(rng: random.Random) -> str:
    r = rng.random()
    cum = 0.0
    for grade, weight in GRADES_WEIGHTED:
        cum += weight
        if r <= cum:
            return grade
    return "B"

def generate_history(
    seed: int,
    scale: ScaleConfig,
    master_data: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Generate:
    - StudentPlan (cohorts with realistic start and graduation terms)
    - StudentPlanCompletedCourse (prior completed courses with passing/failing grades)
    - RegistrationInterest (across 3 historical terms + target term)
    """
    rng = random.Random(seed + SEED_OFFSETS["history"])

    programs = master_data["program"]
    courses = master_data["course"]
    program_courses = master_data["program_course"]
    prerequisites = master_data["prerequisite"]

    # Pre-map prerequisites: course_id -> list of (required_course_id, min_grade)
    prereq_map: Dict[str, List[Tuple[str, str]]] = {}
    for prq in prerequisites:
        cid = prq["course_id"]
        req_cid = prq["required_course_id"]
        mg = prq["min_grade"]
        if cid not in prereq_map:
            prereq_map[cid] = []
        prereq_map[cid].append((req_cid, mg))

    # Pre-map program courses: program_id -> list of course_ids
    prg_courses_map: Dict[str, List[str]] = {}
    for pc in program_courses:
        pid = pc["program_id"]
        if pid not in prg_courses_map:
            prg_courses_map[pid] = []
        prg_courses_map[pid].append(pc["course_id"])

    # Course category lookup for realistic popularity
    course_cat_map = {c["course_id"]: c["category"] for c in courses}
    course_ids_all = [c["course_id"] for c in courses]

    student_plans: List[Dict[str, Any]] = []
    completed_courses_dict: Dict[Tuple[str, str], Dict[str, Any]] = {}
    registration_interest: List[Dict[str, Any]] = []
    interest_idx = 1

    # Cohort start options
    start_term_options = ["2023-FA", "2024-SP", "2024-FA", "2025-SP", "2025-FA"]

    for s_idx in range(1, scale.num_student_plans + 1):
        plan_id = make_student_plan_id(s_idx)
        s_ref = make_student_ref(s_idx)
        
        # Pick program with slight bias towards first programs
        prg = rng.choice(programs)
        pid = prg["program_id"]
        start_term = rng.choice(start_term_options)
        grad_term = "2027-SP" if prg["level"] == "Undergraduate" else "2026-FA"
        
        student_plans.append({
            "student_plan_id": plan_id,
            "student_ref": s_ref,
            "program_id": pid,
            "start_term": start_term,
            "planned_graduation_term": grad_term,
            "status": "active",
        })

        # Available courses for this student's major
        major_courses = prg_courses_map.get(pid, [])
        if not major_courses:
            major_courses = course_ids_all[:10]

        # Track courses completed by this student: course_id -> grade
        student_transcript: Dict[str, str] = {}

        # ---------------------------------------------------------------------
        # Pre-populate completed courses prior to historical terms
        # ---------------------------------------------------------------------
        # Number of completed courses based on start_term seniority
        num_prior = 4 if "2023" in start_term else (2 if "2024" in start_term else 1)
        prior_candidates = [c for c in major_courses if c not in prereq_map]
        if not prior_candidates:
            prior_candidates = major_courses
        
        k_prior = min(len(prior_candidates), num_prior)
        initial_completed = rng.sample(prior_candidates, k_prior)
        for cid in initial_completed:
            grade = rng.choice(["A", "A", "B", "B", "C"])
            student_transcript[cid] = grade
            completed_courses_dict[(plan_id, cid)] = {
                "student_plan_id": plan_id,
                "course_id": cid,
                "term": "2024-FA",
                "grade": grade,
            }

        # ---------------------------------------------------------------------
        # Simulate term by term: HISTORICAL_TERMS + TARGET_TERM
        # ---------------------------------------------------------------------
        for term_idx, term in enumerate(ALL_TERMS):
            is_target = (term == TARGET_TERM)

            # Determine eligible courses whose prerequisites are met
            eligible_courses: List[str] = []
            for cid in major_courses:
                if cid in student_transcript and student_transcript[cid] in ("A", "B", "C"):
                    # Already completed successfully
                    continue
                
                # Check prerequisites strictly
                reqs = prereq_map.get(cid, [])
                prereqs_satisfied = True
                for req_cid, min_g in reqs:
                    if req_cid not in student_transcript:
                        prereqs_satisfied = False
                        break
                    if GRADE_RANK.get(student_transcript[req_cid], 0) < GRADE_RANK.get(min_g, 2):
                        prereqs_satisfied = False
                        break
                
                if prereqs_satisfied:
                    eligible_courses.append(cid)

            # If no eligible major courses, pick general courses that have NO prerequisites
            if not eligible_courses:
                eligible_courses = [c for c in course_ids_all if c not in prereq_map][:5]

            # Pick 2 to 4 courses for registration interest in this term
            num_courses_to_take = min(len(eligible_courses), rng.randint(2, 4))
            
            # Weighted selection based on course category
            weights = []
            for c in eligible_courses:
                cat = course_cat_map.get(c, "standard")
                if cat == "popular_elective":
                    weights.append(3.0)
                elif cat == "core":
                    weights.append(2.0)
                elif cat == "low_enrollment":
                    weights.append(0.3)
                else:
                    weights.append(1.0)
            
            # Normalized sampling without replacement
            chosen_courses: List[str] = []
            temp_pool = list(eligible_courses)
            temp_weights = list(weights)
            for _ in range(num_courses_to_take):
                if not temp_pool:
                    break
                tot = sum(temp_weights)
                probs = [w / tot for w in temp_weights]
                r = rng.random()
                cum = 0.0
                pick_idx = 0
                for p_i, p_val in enumerate(probs):
                    cum += p_val
                    if r <= cum:
                        pick_idx = p_i
                        break
                chosen = temp_pool.pop(pick_idx)
                temp_weights.pop(pick_idx)
                chosen_courses.append(chosen)

            # Record registration interest
            for priority_rank, cid in enumerate(chosen_courses, start=1):
                status = "fulfilled" if not is_target else "active"
                registration_interest.append({
                    "interest_id": make_interest_id(interest_idx),
                    "student_plan_id": plan_id,
                    "course_id": cid,
                    "term": term,
                    "priority": priority_rank,
                    "status": status,
                    "created_on": "2026-08-01" if is_target else "2025-08-01",
                })
                interest_idx += 1

                # If historical term, record completed course with grade so future prereqs unlock
                if not is_target:
                    g = rng.choice(["A", "A", "B", "B", "C"])  # Passing grade in historical course
                    student_transcript[cid] = g
                    pair = (plan_id, cid)
                    if pair not in completed_courses_dict:
                        completed_courses_dict[pair] = {
                            "student_plan_id": plan_id,
                            "course_id": cid,
                            "term": term,
                            "grade": g,
                        }
                    else:
                        completed_courses_dict[pair]["grade"] = g
                        completed_courses_dict[pair]["term"] = term

    return {
        "student_plan": student_plans,
        "student_plan_completed_course": list(completed_courses_dict.values()),
        "registration_interest": registration_interest,
    }
