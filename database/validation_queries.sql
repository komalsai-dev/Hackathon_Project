-- ============================================================================
-- SQL Integrity and Validation Queries
-- Compatible with SQLite and PostgreSQL
-- ============================================================================

-- 1. Check for Orphaned ProgramCourses
SELECT pc.program_id, pc.course_id
FROM program_course pc
LEFT JOIN program p ON pc.program_id = p.program_id
LEFT JOIN course c ON pc.course_id = c.course_id
WHERE p.program_id IS NULL OR c.course_id IS NULL;

-- 2. Check for Room Double-Booking (Same room, same term, same day, overlapping time)
SELECT s1.section_id AS section_1, s2.section_id AS section_2, s1.room_id, s1.day_of_week, s1.start_time
FROM section s1
JOIN section s2 ON s1.room_id = s2.room_id
    AND s1.term = s2.term
    AND s1.day_of_week = s2.day_of_week
    AND s1.start_time = s2.start_time
    AND s1.section_id < s2.section_id;

-- 3. Check for Faculty Double-Booking (Same faculty assigned to overlapping sections)
SELECT w1.assignment_id AS assign_1, w2.assignment_id AS assign_2, w1.faculty_id, s1.term, s1.day_of_week, s1.start_time
FROM workload_assignment w1
JOIN workload_assignment w2 ON w1.faculty_id = w2.faculty_id AND w1.assignment_id < w2.assignment_id
JOIN section s1 ON w1.section_id = s1.section_id
JOIN section s2 ON w2.section_id = s2.section_id
WHERE s1.term = s2.term
  AND s1.day_of_week = s2.day_of_week
  AND s1.start_time = s2.start_time;

-- 4. Check Faculty Assigned Outside Certified Skills
SELECT w.assignment_id, w.faculty_id, s.course_id
FROM workload_assignment w
JOIN section s ON w.section_id = s.section_id
LEFT JOIN faculty_skill fs ON w.faculty_id = fs.faculty_id AND s.course_id = fs.course_id
WHERE fs.faculty_id IS NULL;

-- 5. Check Faculty Workload Hour Exceedance
SELECT f.faculty_id, f.name, f.max_weekly_hours, SUM(w.assigned_hours) AS total_assigned_hours
FROM workload_assignment w
JOIN faculty f ON w.faculty_id = f.faculty_id
GROUP BY f.faculty_id, f.name, f.max_weekly_hours
HAVING SUM(w.assigned_hours) > f.max_weekly_hours;

-- 6. Arithmetic Demand Reconciliation Check
-- Forecast Demand must equal Allocated Seats + Unmet Demand for each course
SELECT 
    df.course_id,
    df.forecast_demand,
    COALESCE(sec_agg.allocated_seats, 0) AS allocated_seats,
    COALESCE(ud.unmet_count, 0) AS unmet_demand,
    (df.forecast_demand - (COALESCE(sec_agg.allocated_seats, 0) + COALESCE(ud.unmet_count, 0))) AS discrepancy
FROM demand_forecast df
LEFT JOIN (
    SELECT course_id, SUM(capacity) AS allocated_seats
    FROM section
    WHERE status IN ('proposed', 'approved')
    GROUP BY course_id
) sec_agg ON df.course_id = sec_agg.course_id
LEFT JOIN unmet_demand ud ON df.course_id = ud.course_id
WHERE (df.forecast_demand - (COALESCE(sec_agg.allocated_seats, 0) + COALESCE(ud.unmet_count, 0))) <> 0;

-- 7. Prerequisite Direct Cycles (A -> B and B -> A)
SELECT p1.course_id AS course_a, p1.required_course_id AS course_b
FROM prerequisite p1
JOIN prerequisite p2 ON p1.course_id = p2.required_course_id AND p1.required_course_id = p2.course_id
WHERE p1.course_id < p1.required_course_id;

-- 8. Section Capacity Under-Allocation Check
SELECT s.section_id, s.course_id, s.capacity, r.capacity AS room_capacity
FROM section s
JOIN room r ON s.room_id = r.room_id
WHERE s.capacity > r.capacity;

