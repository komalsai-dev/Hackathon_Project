"""
Section creation, room allocation, faculty assignment, and decision logging.

Enforces:
1. Room slot availability (no double-booking: room_id, day_of_week, start_time).
2. Faculty eligibility:
   - Certified skill for the course (FacultySkill)
   - Available in section slot (Availability)
   - Not on leave (status != 'on_leave')
   - No time collision with another section
   - Current weekly hours + section contact hours <= max_weekly_hours
3. Deterministic ranking:
   Proficiency (descending) -> Current hours (ascending) -> Faculty ID (ascending)
4. DecisionLog row for EVERY allocation decision (assigned or rejected).
5. Exact reconciliation: forecast_demand = allocated_seats + unmet_demand.
"""

import json
import math
from typing import Dict, List, Set, Tuple, Any
from backend.generator.config import (
    TARGET_TERM,
    TIME_SLOTS,
    AS_OF_DATE,
)
from backend.generator.ids import (
    make_section_id,
    make_section_event_id,
    make_assignment_id,
    make_assignment_event_id,
    make_unmet_id,
    make_decision_id,
)

def run_allocation(
    master_data: Dict[str, List[Dict[str, Any]]],
    forecasts: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Run deterministic section creation and faculty allocation for TARGET_TERM.
    """
    courses = master_data["course"]
    faculty = master_data["faculty"]
    faculty_skills = master_data["faculty_skill"]
    availability = master_data["availability"]
    rooms = master_data["room"]

    # Pre-index courses
    course_map = {c["course_id"]: c for c in courses}

    # Pre-index faculty skills: (faculty_id, course_id) -> proficiency
    skill_map: Dict[Tuple[str, str], int] = {}
    faculty_courses_map: Dict[str, Set[str]] = {}
    for fs in faculty_skills:
        fid = fs["faculty_id"]
        cid = fs["course_id"]
        skill_map[(fid, cid)] = fs["proficiency"]
        if cid not in faculty_courses_map:
            faculty_courses_map[cid] = set()
        faculty_courses_map[cid].add(fid)

    # Pre-index faculty availability in TARGET_TERM: (faculty_id, day_of_week, start_time) -> availability_type
    faculty_avail_map: Dict[Tuple[str, str, str], str] = {}
    for av in availability:
        if av["term"] == TARGET_TERM:
            key = (av["faculty_id"], av["day_of_week"], av["start_time"])
            faculty_avail_map[key] = av["availability_type"]

    faculty_info = {f["faculty_id"]: f for f in faculty}

    # Track state during allocation
    faculty_assigned_hours: Dict[str, float] = {f["faculty_id"]: 0.0 for f in faculty}
    faculty_busy_slots: Set[Tuple[str, str, str]] = set()  # (faculty_id, day, start_time)
    room_busy_slots: Set[Tuple[str, str, str]] = set()     # (room_id, day, start_time)

    # Sort rooms by capacity ascending for best-fit matching
    sorted_rooms = sorted(rooms, key=lambda r: (r["capacity"], r["room_id"]))

    sections: List[Dict[str, Any]] = []
    section_events: List[Dict[str, Any]] = []
    assignments: List[Dict[str, Any]] = []
    assignment_events: List[Dict[str, Any]] = []
    unmet_demand_records: List[Dict[str, Any]] = []
    decision_logs: List[Dict[str, Any]] = []

    sec_counter = 1
    sec_ev_counter = 1
    wla_counter = 1
    wla_ev_counter = 1
    unmet_counter = 1
    dcl_counter = 1

    # Deterministic processing order: Course ID ascending
    sorted_forecasts = sorted(forecasts, key=lambda f: f["course_id"])

    for fc in sorted_forecasts:
        cid = fc["course_id"]
        c_info = course_map[cid]
        f_demand = fc["forecast_demand"]
        contact_hours = c_info["contact_hours_per_week"]

        if f_demand <= 0:
            # Zero demand course
            unmet_demand_records.append({
                "unmet_id": make_unmet_id(2026, unmet_counter),
                "course_id": cid,
                "term": TARGET_TERM,
                "unmet_count": 0,
                "reason_code": "zero_demand",
            })
            unmet_counter += 1

            decision_logs.append({
                "decision_id": make_decision_id(2026, dcl_counter),
                "entity_type": "course",
                "entity_id": cid,
                "decision": "no_sections_created",
                "reason_code": "ZERO_FORECAST_DEMAND",
                "explanation_text": f"Course {cid} has 0 forecast demand. No sections proposed.",
                "inputs_snapshot": json.dumps({"forecast_demand": 0, "course_code": c_info["code"]}),
            })
            dcl_counter += 1
            continue

        remaining_demand = f_demand
        allocated_course_seats = 0

        # Slot index iterator for spreading sections across the weekly timetable
        slot_idx_cycle = 0

        while remaining_demand > 0:
            # 1. Select best room and time slot
            assigned_room = None
            assigned_slot = None

            # Try to find a room with capacity >= min(remaining_demand, 40)
            target_cap = min(remaining_demand, 40)
            
            # Search available (room, slot) combinations
            for slot in TIME_SLOTS[slot_idx_cycle:] + TIME_SLOTS[:slot_idx_cycle]:
                s_day = slot["day_of_week"]
                s_time = slot["start_time"]
                
                # Find best fitting room available at this slot
                for r in sorted_rooms:
                    r_id = r["room_id"]
                    if (r_id, s_day, s_time) not in room_busy_slots:
                        if r["capacity"] >= target_cap:
                            assigned_room = r
                            assigned_slot = slot
                            break
                if assigned_room:
                    break

            # If no room >= target_cap, take any available room
            if not assigned_room:
                for slot in TIME_SLOTS:
                    s_day = slot["day_of_week"]
                    s_time = slot["start_time"]
                    for r in sorted_rooms:
                        r_id = r["room_id"]
                        if (r_id, s_day, s_time) not in room_busy_slots:
                            assigned_room = r
                            assigned_slot = slot
                            break
                    if assigned_room:
                        break

            if not assigned_room or not assigned_slot:
                # No room available anywhere in timetable
                decision_logs.append({
                    "decision_id": make_decision_id(2026, dcl_counter),
                    "entity_type": "course",
                    "entity_id": cid,
                    "decision": "unmet_demand_room_shortage",
                    "reason_code": "NO_ROOM_AVAILABLE",
                    "explanation_text": f"No available classroom could be scheduled for course {cid} (remaining demand: {remaining_demand}).",
                    "inputs_snapshot": json.dumps({"remaining_demand": remaining_demand, "all_rooms_busy": True}),
                })
                dcl_counter += 1
                break

            # Section capacity is min of room capacity and remaining demand
            sec_capacity = min(assigned_room["capacity"], remaining_demand)

            # 2. Select best qualified faculty
            slot_day = assigned_slot["day_of_week"]
            slot_start = assigned_slot["start_time"]
            slot_end = assigned_slot["end_time"]

            eligible_candidates: List[Tuple[int, float, str]] = []  # (-proficiency, current_hours, faculty_id)
            rejection_reasons: List[Dict[str, str]] = []

            certified_fac_ids = sorted(faculty_courses_map.get(cid, set()))
            for fid in certified_fac_ids:
                f_meta = faculty_info[fid]
                
                # Check status
                if f_meta["status"] == "on_leave":
                    rejection_reasons.append({"faculty_id": fid, "reason": "ON_LEAVE"})
                    continue

                # Check slot availability
                avail_type = faculty_avail_map.get((fid, slot_day, slot_start))
                if avail_type != "available":
                    rejection_reasons.append({"faculty_id": fid, "reason": "UNAVAILABLE_SLOT"})
                    continue

                # Check time collision
                if (fid, slot_day, slot_start) in faculty_busy_slots:
                    rejection_reasons.append({"faculty_id": fid, "reason": "TIME_CONFLICT"})
                    continue

                # Check workload limit
                cur_hours = faculty_assigned_hours[fid]
                max_hours = f_meta["max_weekly_hours"]
                if cur_hours + contact_hours > max_hours:
                    rejection_reasons.append({
                        "faculty_id": fid,
                        "reason": "MAX_HOURS_EXCEEDED",
                        "current": cur_hours,
                        "needed": contact_hours,
                        "max": max_hours
                    })
                    continue

                prof = skill_map.get((fid, cid), 1)
                # Sort key: highest proficiency (-prof), lowest current load, lowest ID
                eligible_candidates.append((-prof, cur_hours, fid))

            eligible_candidates.sort()

            # Create section
            sec_id = make_section_id(2026, sec_counter)
            sec_counter += 1

            if eligible_candidates:
                # Faculty found!
                best_prof_neg, _, best_fid = eligible_candidates[0]
                best_prof = -best_prof_neg

                # Mark room busy
                room_busy_slots.add((assigned_room["room_id"], slot_day, slot_start))
                # Mark faculty busy
                faculty_busy_slots.add((best_fid, slot_day, slot_start))
                faculty_assigned_hours[best_fid] += contact_hours

                # Create Section
                sections.append({
                    "section_id": sec_id,
                    "course_id": cid,
                    "term": TARGET_TERM,
                    "room_id": assigned_room["room_id"],
                    "day_of_week": slot_day,
                    "start_time": slot_start,
                    "end_time": slot_end,
                    "capacity": sec_capacity,
                    "status": "approved",
                })

                # Section Events
                section_events.append({
                    "event_id": make_section_event_id(2026, sec_ev_counter),
                    "section_id": sec_id,
                    "event_type": "proposed",
                    "event_ts": f"{AS_OF_DATE}T08:00:00Z",
                    "reason": f"Initial section proposed to meet forecast demand ({f_demand})",
                })
                sec_ev_counter += 1

                section_events.append({
                    "event_id": make_section_event_id(2026, sec_ev_counter),
                    "section_id": sec_id,
                    "event_type": "approved",
                    "event_ts": f"{AS_OF_DATE}T09:30:00Z",
                    "reason": f"Approved with room {assigned_room['room_id']} and faculty {best_fid}",
                })
                sec_ev_counter += 1

                # Workload Assignment
                wla_id = make_assignment_id(2026, wla_counter)
                wla_counter += 1

                assignments.append({
                    "assignment_id": wla_id,
                    "section_id": sec_id,
                    "faculty_id": best_fid,
                    "assigned_hours": contact_hours,
                    "status": "assigned",
                    "decision_reason_code": "STAFFED_QUALIFIED",
                })

                assignment_events.append({
                    "event_id": make_assignment_event_id(2026, wla_ev_counter),
                    "assignment_id": wla_id,
                    "event_type": "assigned",
                    "event_ts": f"{AS_OF_DATE}T09:30:00Z",
                    "reason": f"Assigned to {best_fid} (Proficiency: {best_prof}, Workload: {faculty_assigned_hours[best_fid]:.1f}/{faculty_info[best_fid]['max_weekly_hours']}h)",
                })
                wla_ev_counter += 1

                # Decision Log
                decision_logs.append({
                    "decision_id": make_decision_id(2026, dcl_counter),
                    "entity_type": "section",
                    "entity_id": sec_id,
                    "decision": "allocated",
                    "reason_code": "STAFFED_QUALIFIED",
                    "explanation_text": (
                        f"Section {sec_id} assigned to faculty {best_fid} in room {assigned_room['room_id']}. "
                        f"Proficiency={best_prof}, load={faculty_assigned_hours[best_fid]:.1f}h. "
                        f"Rejections considered: {len(rejection_reasons)}."
                    ),
                    "inputs_snapshot": json.dumps({
                        "candidates_evaluated": len(certified_fac_ids),
                        "selected_faculty": best_fid,
                        "room_id": assigned_room["room_id"],
                        "rejections": rejection_reasons[:5],
                    }),
                })
                dcl_counter += 1

                allocated_course_seats += sec_capacity
                remaining_demand -= sec_capacity
                slot_idx_cycle = (slot_idx_cycle + 1) % len(TIME_SLOTS)

            else:
                # No eligible faculty found to teach this section
                decision_logs.append({
                    "decision_id": make_decision_id(2026, dcl_counter),
                    "entity_type": "course",
                    "entity_id": cid,
                    "decision": "section_unstaffed_shortage",
                    "reason_code": "NO_QUALIFIED_FACULTY_AVAILABLE",
                    "explanation_text": (
                        f"Could not staff additional section for course {cid} in slot {slot_day} {slot_start}. "
                        f"Evaluated {len(certified_fac_ids)} certified faculty; all rejected due to workload limits, leave, or schedule conflicts."
                    ),
                    "inputs_snapshot": json.dumps({"rejections": rejection_reasons}),
                })
                dcl_counter += 1
                break

        # Reconcile unmet demand
        unmet_count = f_demand - allocated_course_seats
        if unmet_count > 0:
            unmet_reason = "no_faculty" if not eligible_candidates else "capacity_limit"
            unmet_demand_records.append({
                "unmet_id": make_unmet_id(2026, unmet_counter),
                "course_id": cid,
                "term": TARGET_TERM,
                "unmet_count": unmet_count,
                "reason_code": unmet_reason,
            })
            unmet_counter += 1
        else:
            # Fully met demand: record 0 unmet count with capacity_limit code for clean reconciliation join
            unmet_demand_records.append({
                "unmet_id": make_unmet_id(2026, unmet_counter),
                "course_id": cid,
                "term": TARGET_TERM,
                "unmet_count": 0,
                "reason_code": "capacity_limit",
            })
            unmet_counter += 1

    return {
        "section": sections,
        "section_event": section_events,
        "workload_assignment": assignments,
        "assignment_event": assignment_events,
        "unmet_demand": unmet_demand_records,
        "decision_log": decision_logs,
    }

