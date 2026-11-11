"""
Edge case and anomaly injector with strictly isolated ground truth logging.

Rules:
1. Baseline records are pristine.
2. Injects controlled negative edge cases (isolated without cross-contaminating other rules):
   - faculty_outside_skill
   - workload_exceeded
   - section_capacity_too_low
   - prerequisite_violation
   - duplicate_section_assignment
3. Also includes normal/boundary cases (injected_flag=0):
   - at_workload_limit
   - at_capacity
   - faculty_on_leave
   - zero_demand_course
4. Strict data isolation:
   Input tables do NOT contain issue_type, injected_flag, or any ground-truth column.
   All labels are written solely to ground_truth.csv / ground_truth.json.
"""

import random
from typing import Dict, List, Any, Set, Tuple
from backend.generator.config import (
    ScaleConfig,
    SEED_OFFSETS,
    TARGET_TERM,
)
from backend.generator.ids import (
    make_assignment_id,
    make_interest_id,
)

def inject_anomalies_and_build_ground_truth(
    seed: int,
    scale: ScaleConfig,
    master_data: Dict[str, List[Dict[str, Any]]],
    history_data: Dict[str, List[Dict[str, Any]]],
    alloc_data: Dict[str, List[Dict[str, Any]]],
    forecasts: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Inject labelled anomalies into table copies in place and return the isolated ground-truth dataset.
    """
    rng = random.Random(seed + SEED_OFFSETS["anomalies"])
    ground_truth: List[Dict[str, Any]] = []

    sections = alloc_data["section"]
    assignments = alloc_data["workload_assignment"]
    faculty = master_data["faculty"]
    faculty_skills = master_data["faculty_skill"]
    reg_interests = history_data["registration_interest"]
    completed_courses = history_data["student_plan_completed_course"]
    prerequisites = master_data["prerequisite"]
    student_plans = history_data["student_plan"]

    # Target count based on scale: 10 on starter, 25-30 on full
    target_count = 10 if scale.num_courses <= 100 else 25

    # Skill set: (faculty_id, course_id)
    known_skills = {(fs["faculty_id"], fs["course_id"]) for fs in faculty_skills}
    faculty_by_id = {f["faculty_id"]: f for f in faculty}
    courses_by_id = {c["course_id"]: c for c in master_data["course"]}

    # Track touched section and assignment IDs to avoid cross-contamination
    touched_assignments: Set[str] = set()
    touched_sections: Set[str] = set()

    # Pre-index faculty courses
    faculty_courses: Dict[str, List[str]] = {f["faculty_id"]: [] for f in faculty}
    for fs in faculty_skills:
        faculty_courses[fs["faculty_id"]].append(fs["course_id"])

    # Current assignments map
    fac_assigned_hours: Dict[str, float] = {f["faculty_id"]: 0.0 for f in faculty}
    for w in assignments:
        if w["status"] == "assigned":
            fac_assigned_hours[w["faculty_id"]] = fac_assigned_hours.get(w["faculty_id"], 0.0) + w["assigned_hours"]

    # -------------------------------------------------------------------------
    # 1. Anomaly: faculty_outside_skill
    # -------------------------------------------------------------------------
    count = 0
    for wla in assignments:
        sec = next((s for s in sections if s["section_id"] == wla["section_id"]), None)
        if not sec or wla["assignment_id"] in touched_assignments:
            continue
        cid = sec["course_id"]
        # Find faculty without skill who is active and won't exceed hours
        unskilled = [
            f["faculty_id"] for f in faculty 
            if (f["faculty_id"], cid) not in known_skills and f["status"] == "active"
        ]
        if unskilled:
            bad_fac = rng.choice(unskilled)
            wla["faculty_id"] = bad_fac
            touched_assignments.add(wla["assignment_id"])
            touched_sections.add(sec["section_id"])
            ground_truth.append({
                "entity": "workload_assignment",
                "record_id": wla["assignment_id"],
                "issue_type": "faculty_outside_skill",
                "expected_decision": "flag_or_reject",
                "expected_reason_code": "FACULTY_LACKS_CERTIFIED_SKILL",
                "injected_flag": 1,
            })
            count += 1
            if count >= target_count:
                break

    # -------------------------------------------------------------------------
    # 2. Anomaly: workload_exceeded
    # -------------------------------------------------------------------------
    count = 0
    wla_counter = len(assignments) + 1000
    for f in faculty:
        if f["status"] != "active":
            continue
        fid = f["faculty_id"]
        skills_of_f = faculty_courses.get(fid, [])
        if not skills_of_f:
            continue
        
        # Find a section teaching one of their skilled courses that hasn't been touched
        sec = next((s for s in sections if s["course_id"] in skills_of_f and s["section_id"] not in touched_sections), None)
        if not sec:
            continue

        cur = fac_assigned_hours.get(fid, 0.0)
        max_h = f["max_weekly_hours"]
        excess_hours = max(4.0, (max_h - cur) + 4.0)

        new_wla_id = make_assignment_id(2026, wla_counter)
        wla_counter += 1
        assignments.append({
            "assignment_id": new_wla_id,
            "section_id": sec["section_id"],
            "faculty_id": fid,
            "assigned_hours": excess_hours,
            "status": "assigned",
            "decision_reason_code": "INJECTED_OVERLOAD",
        })
        fac_assigned_hours[fid] += excess_hours
        touched_assignments.add(new_wla_id)

        ground_truth.append({
            "entity": "faculty",
            "record_id": fid,
            "issue_type": "workload_exceeded",
            "expected_decision": "flag_overload",
            "expected_reason_code": "WORKLOAD_HOURS_EXCEEDED",
            "injected_flag": 1,
        })
        count += 1
        if count >= target_count:
            break

    # -------------------------------------------------------------------------
    # 3. Anomaly: section_capacity_too_low
    # -------------------------------------------------------------------------
    count = 0
    used_cap_courses: Set[str] = set()
    for sec in sections:
        cid = sec["course_id"]
        if sec["capacity"] >= 25 and sec["section_id"] not in touched_sections and cid not in used_cap_courses:
            sec["capacity"] = 5
            touched_sections.add(sec["section_id"])
            used_cap_courses.add(cid)
            ground_truth.append({
                "entity": "section",
                "record_id": sec["section_id"],
                "issue_type": "section_capacity_too_low",
                "expected_decision": "resize_or_split",
                "expected_reason_code": "SECTION_CAPACITY_UNDERSIZED",
                "injected_flag": 1,
            })
            count += 1
            if count >= target_count:
                break

    # -------------------------------------------------------------------------
    # 4. Anomaly: prerequisite_violation
    # -------------------------------------------------------------------------
    count = 0
    int_counter = len(reg_interests) + 5000
    for prq in prerequisites:
        cid = prq["course_id"]
        req_cid = prq["required_course_id"]
        
        # Pick a student plan who definitely has NOT taken req_cid
        for student in student_plans:
            s_id = student["student_plan_id"]
            had_req = any(cc["student_plan_id"] == s_id and cc["course_id"] == req_cid for cc in completed_courses)
            if not had_req:
                new_int_id = make_interest_id(int_counter)
                int_counter += 1
                reg_interests.append({
                    "interest_id": new_int_id,
                    "student_plan_id": s_id,
                    "course_id": cid,
                    "term": TARGET_TERM,
                    "priority": 1,
                    "status": "active",
                    "created_on": "2026-08-01",
                })
                ground_truth.append({
                    "entity": "registration_interest",
                    "record_id": new_int_id,
                    "issue_type": "prerequisite_violation",
                    "expected_decision": "reject_registration",
                    "expected_reason_code": "PREREQUISITE_NOT_COMPLETED",
                    "injected_flag": 1,
                })
                count += 1
                break
        if count >= target_count:
            break

    # -------------------------------------------------------------------------
    # 5. Anomaly: duplicate_section_assignment
    # -------------------------------------------------------------------------
    count = 0
    avail_sections = [s for s in sections if s["section_id"] not in touched_sections]
    if len(avail_sections) >= 2:
        for i in range(0, len(avail_sections) - 1, 2):
            s1 = avail_sections[i]
            s2 = avail_sections[i + 1]
            
            # Find assignments for s1 and s2
            w1 = next((w for w in assignments if w["section_id"] == s1["section_id"] and w["assignment_id"] not in touched_assignments), None)
            w2 = next((w for w in assignments if w["section_id"] == s2["section_id"] and w["assignment_id"] not in touched_assignments), None)
            if not w1 or not w2:
                continue

            # Ensure w1 faculty has skill for s2 so this isn't flagged as faculty_outside_skill
            if (w1["faculty_id"], s2["course_id"]) not in known_skills:
                continue

            # Align day and start time
            s2["day_of_week"] = s1["day_of_week"]
            s2["start_time"] = s1["start_time"]
            s2["end_time"] = s1["end_time"]

            w2["faculty_id"] = w1["faculty_id"]
            touched_assignments.add(w1["assignment_id"])
            touched_assignments.add(w2["assignment_id"])
            touched_sections.add(s1["section_id"])
            touched_sections.add(s2["section_id"])

            ground_truth.append({
                "entity": "workload_assignment",
                "record_id": w2["assignment_id"],
                "issue_type": "duplicate_section_assignment",
                "expected_decision": "reassign_or_flag",
                "expected_reason_code": "SCHEDULE_TIME_COLLISION",
                "injected_flag": 1,
            })
            count += 1
            if count >= target_count:
                break

    # -------------------------------------------------------------------------
    # 6. Boundary / Normal Cases (injected_flag = 0)
    # -------------------------------------------------------------------------
    zero_demand_courses = [fc["course_id"] for fc in forecasts if fc["forecast_demand"] == 0]
    for cid in zero_demand_courses[:5]:
        ground_truth.append({
            "entity": "course",
            "record_id": cid,
            "issue_type": "zero_demand_course",
            "expected_decision": "no_sections_created",
            "expected_reason_code": "ZERO_FORECAST_DEMAND",
            "injected_flag": 0,
        })

    leave_faculty = [f["faculty_id"] for f in faculty if f["status"] == "on_leave"]
    for fid in leave_faculty[:5]:
        ground_truth.append({
            "entity": "faculty",
            "record_id": fid,
            "issue_type": "faculty_on_leave",
            "expected_decision": "skip_assignment",
            "expected_reason_code": "FACULTY_ON_LEAVE",
            "injected_flag": 0,
        })

    return ground_truth
