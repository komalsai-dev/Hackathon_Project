-- ============================================================================
-- Course Demand Forecasting and Faculty Allocation Schema
-- Fully portable ANSI SQL: Compatible with both SQLite and PostgreSQL.
-- ============================================================================

-- Master Tables
CREATE TABLE IF NOT EXISTS program (
    program_id VARCHAR(16) PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    level VARCHAR(20) NOT NULL CHECK (level IN ('Undergraduate', 'Graduate')),
    department VARCHAR(80) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('active', 'inactive', 'deprecated')),
    effective_from DATE NOT NULL,
    effective_to DATE NOT NULL,
    CHECK (effective_from <= effective_to)
);

CREATE TABLE IF NOT EXISTS course (
    course_id VARCHAR(16) PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    title VARCHAR(150) NOT NULL,
    credits INTEGER NOT NULL CHECK (credits BETWEEN 1 AND 6),
    level INTEGER NOT NULL CHECK (level BETWEEN 100 AND 800),
    category VARCHAR(30) NOT NULL CHECK (category IN ('core', 'popular_elective', 'low_enrollment', 'standard')),
    contact_hours_per_week REAL NOT NULL CHECK (contact_hours_per_week > 0),
    status VARCHAR(20) NOT NULL CHECK (status IN ('active', 'inactive', 'deprecated'))
);

CREATE TABLE IF NOT EXISTS program_course (
    program_id VARCHAR(16) NOT NULL,
    course_id VARCHAR(16) NOT NULL,
    requirement_type VARCHAR(20) NOT NULL CHECK (requirement_type IN ('core', 'elective')),
    recommended_term INTEGER NOT NULL CHECK (recommended_term BETWEEN 1 AND 10),
    PRIMARY KEY (program_id, course_id),
    FOREIGN KEY (program_id) REFERENCES program(program_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES course(course_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS prerequisite (
    prerequisite_id VARCHAR(16) PRIMARY KEY,
    course_id VARCHAR(16) NOT NULL,
    required_course_id VARCHAR(16) NOT NULL,
    min_grade VARCHAR(5) NOT NULL CHECK (min_grade IN ('A', 'B', 'C', 'D')),
    effective_from DATE NOT NULL,
    effective_to DATE NOT NULL,
    CHECK (course_id <> required_course_id),
    CHECK (effective_from <= effective_to),
    FOREIGN KEY (course_id) REFERENCES course(course_id) ON DELETE CASCADE,
    FOREIGN KEY (required_course_id) REFERENCES course(course_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS faculty (
    faculty_id VARCHAR(16) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(80) NOT NULL,
    employment_type VARCHAR(20) NOT NULL CHECK (employment_type IN ('full_time', 'adjunct')),
    max_weekly_hours REAL NOT NULL CHECK (max_weekly_hours > 0),
    status VARCHAR(20) NOT NULL CHECK (status IN ('active', 'on_leave', 'retired'))
);

CREATE TABLE IF NOT EXISTS faculty_skill (
    faculty_id VARCHAR(16) NOT NULL,
    course_id VARCHAR(16) NOT NULL,
    proficiency INTEGER NOT NULL CHECK (proficiency BETWEEN 1 AND 3),
    certified_from DATE NOT NULL,
    PRIMARY KEY (faculty_id, course_id),
    FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES course(course_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS availability (
    availability_id VARCHAR(16) PRIMARY KEY,
    faculty_id VARCHAR(16) NOT NULL,
    term VARCHAR(20) NOT NULL,
    day_of_week VARCHAR(10) NOT NULL CHECK (day_of_week IN ('MWF', 'TTH', 'M', 'T', 'W', 'TH', 'F')),
    start_time VARCHAR(10) NOT NULL,
    end_time VARCHAR(10) NOT NULL,
    availability_type VARCHAR(20) NOT NULL CHECK (availability_type IN ('available', 'leave')),
    FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS room (
    room_id VARCHAR(16) PRIMARY KEY,
    building VARCHAR(50) NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    room_type VARCHAR(30) NOT NULL CHECK (room_type IN ('lecture_hall', 'classroom', 'seminar', 'computer_lab')),
    available_slots INTEGER NOT NULL CHECK (available_slots >= 0)
);

-- Plan and Demand Tables
CREATE TABLE IF NOT EXISTS student_plan (
    student_plan_id VARCHAR(16) PRIMARY KEY,
    student_ref VARCHAR(16) NOT NULL,
    program_id VARCHAR(16) NOT NULL,
    start_term VARCHAR(20) NOT NULL,
    planned_graduation_term VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('active', 'graduated', 'withdrawn', 'on_leave')),
    FOREIGN KEY (program_id) REFERENCES program(program_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS student_plan_completed_course (
    student_plan_id VARCHAR(16) NOT NULL,
    course_id VARCHAR(16) NOT NULL,
    term VARCHAR(20) NOT NULL,
    grade VARCHAR(5) NOT NULL CHECK (grade IN ('A', 'B', 'C', 'D', 'F')),
    PRIMARY KEY (student_plan_id, course_id),
    FOREIGN KEY (student_plan_id) REFERENCES student_plan(student_plan_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES course(course_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS registration_interest (
    interest_id VARCHAR(16) PRIMARY KEY,
    student_plan_id VARCHAR(16) NOT NULL,
    course_id VARCHAR(16) NOT NULL,
    term VARCHAR(20) NOT NULL,
    priority INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 5),
    status VARCHAR(20) NOT NULL CHECK (status IN ('active', 'fulfilled', 'cancelled', 'waitlisted')),
    created_on DATE NOT NULL,
    FOREIGN KEY (student_plan_id) REFERENCES student_plan(student_plan_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES course(course_id) ON DELETE CASCADE
);

-- Result and Event Tables
CREATE TABLE IF NOT EXISTS demand_forecast (
    forecast_id VARCHAR(20) PRIMARY KEY,
    course_id VARCHAR(16) NOT NULL,
    target_term VARCHAR(20) NOT NULL,
    window_terms_used VARCHAR(80) NOT NULL,
    method VARCHAR(50) NOT NULL,
    forecast_demand INTEGER NOT NULL CHECK (forecast_demand >= 0),
    lower_bound INTEGER NOT NULL CHECK (lower_bound >= 0),
    upper_bound INTEGER NOT NULL CHECK (upper_bound >= lower_bound),
    FOREIGN KEY (course_id) REFERENCES course(course_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS section (
    section_id VARCHAR(20) PRIMARY KEY,
    course_id VARCHAR(16) NOT NULL,
    term VARCHAR(20) NOT NULL,
    room_id VARCHAR(16) NOT NULL,
    day_of_week VARCHAR(10) NOT NULL CHECK (day_of_week IN ('MWF', 'TTH', 'M', 'T', 'W', 'TH', 'F')),
    start_time VARCHAR(10) NOT NULL,
    end_time VARCHAR(10) NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    status VARCHAR(20) NOT NULL CHECK (status IN ('proposed', 'approved', 'changed', 'cancelled')),
    FOREIGN KEY (course_id) REFERENCES course(course_id) ON DELETE CASCADE,
    FOREIGN KEY (room_id) REFERENCES room(room_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS section_event (
    event_id VARCHAR(20) PRIMARY KEY,
    section_id VARCHAR(20) NOT NULL,
    event_type VARCHAR(20) NOT NULL CHECK (event_type IN ('proposed', 'approved', 'changed', 'cancelled')),
    event_ts VARCHAR(30) NOT NULL,
    reason TEXT NOT NULL,
    FOREIGN KEY (section_id) REFERENCES section(section_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS workload_assignment (
    assignment_id VARCHAR(20) PRIMARY KEY,
    section_id VARCHAR(20) NOT NULL,
    faculty_id VARCHAR(16) NOT NULL,
    assigned_hours REAL NOT NULL CHECK (assigned_hours > 0),
    status VARCHAR(20) NOT NULL CHECK (status IN ('assigned', 'unassigned', 'flagged', 'reallocated')),
    decision_reason_code VARCHAR(50) NOT NULL,
    FOREIGN KEY (section_id) REFERENCES section(section_id) ON DELETE CASCADE,
    FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS assignment_event (
    event_id VARCHAR(20) PRIMARY KEY,
    assignment_id VARCHAR(20) NOT NULL,
    event_type VARCHAR(20) NOT NULL CHECK (event_type IN ('assigned', 'unassigned', 'flagged', 'reallocated')),
    event_ts VARCHAR(30) NOT NULL,
    reason TEXT NOT NULL,
    FOREIGN KEY (assignment_id) REFERENCES workload_assignment(assignment_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS unmet_demand (
    unmet_id VARCHAR(20) PRIMARY KEY,
    course_id VARCHAR(16) NOT NULL,
    term VARCHAR(20) NOT NULL,
    unmet_count INTEGER NOT NULL CHECK (unmet_count >= 0),
    reason_code VARCHAR(50) NOT NULL CHECK (reason_code IN ('no_faculty', 'no_room', 'capacity_limit', 'prereq_gap', 'zero_demand')),
    FOREIGN KEY (course_id) REFERENCES course(course_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS decision_log (
    decision_id VARCHAR(20) PRIMARY KEY,
    entity_type VARCHAR(30) NOT NULL,
    entity_id VARCHAR(30) NOT NULL,
    decision VARCHAR(50) NOT NULL,
    reason_code VARCHAR(50) NOT NULL,
    explanation_text TEXT NOT NULL,
    inputs_snapshot TEXT NOT NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_course_code ON course(code);
CREATE INDEX IF NOT EXISTS idx_reg_interest_term ON registration_interest(term, course_id);
CREATE INDEX IF NOT EXISTS idx_section_term ON section(term, course_id);
CREATE INDEX IF NOT EXISTS idx_wla_faculty ON workload_assignment(faculty_id);
CREATE INDEX IF NOT EXISTS idx_faculty_skill ON faculty_skill(faculty_id, course_id);

