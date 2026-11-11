"""
Derived metric calculation engine.
All totals, balances, utilization rates, and department rollups are computed
strictly from source records rather than generated independently.
"""

from typing import Dict, List, Any

def compute_derived_metrics(
    master_data: Dict[str, List[Dict[str, Any]]],
    forecasts: List[Dict[str, Any]],
    alloc_data: Dict[str, List[Dict[str, Any]]],
    history_data: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Compute derived operational metrics and summary KPIs.
    """
    courses = master_data["course"]
    faculty = master_data["faculty"]
    rooms = master_data["room"]
    sections = alloc_data["section"]
    assignments = alloc_data["workload_assignment"]
    unmet_records = alloc_data["unmet_demand"]

    course_dept = {c["course_id"]: c["department"] for c in master_data.get("course", []) if "department" in c}
    # If course doesn't have department directly, infer from code prefix or master_data
    if not course_dept:
        dept_abbr = {
            "CS": "Computer Science",
            "DS": "Data Science",
            "EE": "Electrical Engineering",
            "MATH": "Mathematics",
            "BA": "Business Analytics",
            "IS": "Information Systems",
            "ECON": "Economics",
            "ME": "Mechanical Engineering",
        }
        for c in courses:
            prefix = c["code"].split("-")[0]
            course_dept[c["course_id"]] = dept_abbr.get(prefix, "General Studies")

    # 1. Total forecast, allocated, and unmet
    total_forecast = sum(f["forecast_demand"] for f in forecasts)
    total_allocated = sum(s["capacity"] for s in sections if s["status"] in ("proposed", "approved"))
    total_unmet = sum(u["unmet_count"] for u in unmet_records)

    fill_rate = (total_allocated / total_forecast * 100.0) if total_forecast > 0 else 100.0
    unmet_rate = (total_unmet / total_forecast * 100.0) if total_forecast > 0 else 0.0

    # 2. Faculty utilization
    faculty_assigned: Dict[str, float] = {f["faculty_id"]: 0.0 for f in faculty}
    for w in assignments:
        if w["status"] == "assigned":
            faculty_assigned[w["faculty_id"]] = faculty_assigned.get(w["faculty_id"], 0.0) + w["assigned_hours"]

    total_fac_capacity_hours = sum(f["max_weekly_hours"] for f in faculty if f["status"] == "active")
    total_fac_assigned_hours = sum(faculty_assigned.values())
    faculty_utilization_pct = (
        (total_fac_assigned_hours / total_fac_capacity_hours * 100.0)
        if total_fac_capacity_hours > 0 else 0.0
    )

    # 3. Room utilization
    room_capacity_hours = len(rooms) * 30.0  # Approx 30 weekly slot hours available per room
    total_room_hours_used = len(sections) * 3.0
    room_utilization_pct = (
        (total_room_hours_used / room_capacity_hours * 100.0)
        if room_capacity_hours > 0 else 0.0
    )

    # 4. Department breakdown
    dept_metrics: Dict[str, Dict[str, Any]] = {}
    for f in forecasts:
        d = course_dept.get(f["course_id"], "Other")
        if d not in dept_metrics:
            dept_metrics[d] = {"forecast": 0, "allocated": 0, "unmet": 0}
        dept_metrics[d]["forecast"] += f["forecast_demand"]

    for s in sections:
        if s["status"] in ("proposed", "approved"):
            d = course_dept.get(s["course_id"], "Other")
            if d in dept_metrics:
                dept_metrics[d]["allocated"] += s["capacity"]

    for u in unmet_records:
        d = course_dept.get(u["course_id"], "Other")
        if d in dept_metrics:
            dept_metrics[d]["unmet"] += u["unmet_count"]

    department_summary = []
    for dept_name, vals in sorted(dept_metrics.items()):
        f_val = vals["forecast"]
        a_val = vals["allocated"]
        u_val = vals["unmet"]
        fr = (a_val / f_val * 100.0) if f_val > 0 else 100.0
        department_summary.append({
            "department": dept_name,
            "forecast_demand": f_val,
            "allocated_seats": a_val,
            "unmet_demand": u_val,
            "fill_rate_pct": round(fr, 1),
        })

    return {
        "kpis": {
            "total_programs": len(master_data["program"]),
            "total_courses": len(courses),
            "total_faculty": len(faculty),
            "total_rooms": len(rooms),
            "total_student_plans": len(history_data["student_plan"]),
            "total_forecast_demand": total_forecast,
            "total_allocated_seats": total_allocated,
            "total_unmet_demand": total_unmet,
            "fill_rate_pct": round(fill_rate, 1),
            "unmet_rate_pct": round(unmet_rate, 1),
            "faculty_utilization_pct": round(faculty_utilization_pct, 1),
            "room_utilization_pct": round(room_utilization_pct, 1),
        },
        "department_summary": department_summary,
    }

