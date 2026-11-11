# Data Dictionary

Comprehensive dictionary for all 18 relational entities across Master, Transactional/Demand, Event, and Evaluation layers.

---

## 1. Master Tables

### `program`
Represents an academic degree program offered by a university department.

| Field | Type | Nullable | Uniqueness | Allowed Values / Range | Units | Validation Rule | Description |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- | :--- |
| `program_id` | VARCHAR(16) | No | PK | `PRG-000001` .. `PRG-999999` | - | Regex `^PRG-\d{6}$` | Unique identifier for the program |
| `name` | VARCHAR(120) | No | No | String | - | Length 3-120 | Full degree program name |
| `level` | VARCHAR(20) | No | No | `'Undergraduate'`, `'Graduate'` | - | Enum check | Academic degree tier |
| `department` | VARCHAR(80) | No | No | Valid university department | - | Length 2-80 | Department owning the degree program |
| `status` | VARCHAR(20) | No | No | `'active'`, `'inactive'`, `'deprecated'` | - | Enum check | Lifecycle state of program |
| `effective_from` | DATE | No | No | ISO-8601 Date | Days | `effective_from <= effective_to` | Start date of curriculum validity |
| `effective_to` | DATE | No | No | ISO-8601 Date | Days | `effective_from <= effective_to` | Expiration date of curriculum validity |

---

### `course`
Catalog course offerings across all departments.

| Field | Type | Nullable | Uniqueness | Allowed Values / Range | Units | Validation Rule | Description |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- | :--- |
| `course_id` | VARCHAR(16) | No | PK | `CRS-000001` .. `CRS-999999` | - | Regex `^CRS-\d{6}$` | Immutable course identifier |
| `code` | VARCHAR(20) | No | Unique | E.g. `CS-100-001` | - | Unique string | Human-readable departmental course code |
| `title` | VARCHAR(150) | No | No | String | - | Length 3-150 | Descriptive title of course |
| `credits` | INTEGER | No | No | 1 to 6 | Credits | `1 <= credits <= 6` | Credit hours awarded |
| `level` | INTEGER | No | No | 100 to 800 | - | `100 <= level <= 800` | Course numerical rigor tier |
| `category` | VARCHAR(30) | No | No | `'core'`, `'popular_elective'`, `'low_enrollment'`, `'standard'` | - | Enum check | Categorical demand profile |
| `contact_hours_per_week` | REAL | No | No | 1.0 to 6.0 | Hours/Week | `contact_hours > 0` | Scheduled faculty lecture hours per week |
| `status` | VARCHAR(20) | No | No | `'active'`, `'inactive'`, `'deprecated'` | - | Enum check | Course catalog status |

---

### `program_course`
Bridge table (N:M) defining course requirements per degree program.

| Field | Type | Nullable | Uniqueness | Allowed Values / Range | Units | Validation Rule | Description |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- | :--- |
| `program_id` | VARCHAR(16) | No | Composite PK | Valid `program.program_id` | - | FK to `program` | Program reference |
| `course_id` | VARCHAR(16) | No | Composite PK | Valid `course.course_id` | - | FK to `course` | Required/elective course reference |
| `requirement_type` | VARCHAR(20) | No | No | `'core'`, `'elective'` | - | Enum check | Requirement classification |
| `recommended_term`| INTEGER | No | No | 1 to 10 | Terms | `1 <= recommended_term <= 10` | Suggested student curriculum semester |

---

### `prerequisite`
Defines sequential dependencies between courses. Must form an acyclic graph.

| Field | Type | Nullable | Uniqueness | Allowed Values / Range | Units | Validation Rule | Description |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- | :--- |
| `prerequisite_id` | VARCHAR(16) | No | PK | `PRQ-000001` .. `PRQ-999999` | - | Regex `^PRQ-\d{6}$` | Prerequisite rule identifier |
| `course_id` | VARCHAR(16) | No | No | Valid `course.course_id` | - | FK to `course` | Advanced course requiring completion |
| `required_course_id` | VARCHAR(16) | No | No | Valid `course.course_id` | - | FK to `course`; `!= course_id` | Foundational course that must be completed |
| `min_grade` | VARCHAR(5) | No | No | `'A'`, `'B'`, `'C'`, `'D'` | Letter | Enum check | Minimum passing grade required |
| `effective_from` | DATE | No | No | ISO-8601 Date | Days | `effective_from <= effective_to` | Rule start date |
| `effective_to` | DATE | No | No | ISO-8601 Date | Days | `effective_from <= effective_to` | Rule end date |

---

### `faculty`
Instructors and professors eligible to teach courses.

| Field | Type | Nullable | Uniqueness | Allowed Values / Range | Units | Validation Rule | Description |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- | :--- |
| `faculty_id` | VARCHAR(16) | No | PK | `FAC-000001` .. `FAC-999999` | - | Regex `^FAC-\d{6}$` | Faculty employee ID |
| `name` | VARCHAR(100) | No | No | String | - | Length 3-100 | Full name of instructor |
| `department` | VARCHAR(80) | No | No | Valid department | - | Length 2-80 | Primary academic home department |
| `employment_type` | VARCHAR(20) | No | No | `'full_time'`, `'adjunct'` | - | Enum check | Contract employment category |
| `max_weekly_hours`| REAL | No | No | 6.0 to 20.0 | Hours/Week | `max_weekly_hours > 0` | Hard cap on weekly teaching load |
| `status` | VARCHAR(20) | No | No | `'active'`, `'on_leave'`, `'retired'` | - | Enum check | Current active/leave status |

---

### `faculty_skill`
Bridge table (N:M) defining which courses an instructor is certified to teach.

| Field | Type | Nullable | Uniqueness | Allowed Values / Range | Units | Validation Rule | Description |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- | :--- |
| `faculty_id` | VARCHAR(16) | No | Composite PK | Valid `faculty.faculty_id` | - | FK to `faculty` | Certified instructor |
| `course_id` | VARCHAR(16) | No | Composite PK | Valid `course.course_id` | - | FK to `course` | Course certified to teach |
| `proficiency` | INTEGER | No | No | 1 to 3 | Tier | `1 <= proficiency <= 3` | Teaching proficiency (3=expert) |
| `certified_from` | DATE | No | No | ISO-8601 Date | Days | Valid date | Certification effective date |

---

### `availability`
Weekly timetable availability blocks and approved leaves.

| Field | Type | Nullable | Uniqueness | Allowed Values / Range | Units | Validation Rule | Description |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- | :--- |
| `availability_id` | VARCHAR(16) | No | PK | `AVL-000001` .. `AVL-999999` | - | Regex `^AVL-\d{6}$` | Availability entry ID |
| `faculty_id` | VARCHAR(16) | No | No | Valid `faculty.faculty_id` | - | FK to `faculty` | Faculty reference |
| `term` | VARCHAR(20) | No | No | E.g. `2026-FA` | - | Valid term identifier | Term of availability |
| `day_of_week` | VARCHAR(10) | No | No | `'MWF'`, `'TTH'`, `'M'`, `'T'`, `'W'`, `'TH'`, `'F'` | - | Enum check | Days offered |
| `start_time` | VARCHAR(10) | No | No | `HH:MM:SS` | Time | Valid time | Slot start time |
| `end_time` | VARCHAR(10) | No | No | `HH:MM:SS` | Time | `start_time < end_time` | Slot end time |
| `availability_type` | VARCHAR(20) | No | No | `'available'`, `'leave'` | - | Enum check | Slot status |

---

### `room`
Classroom and lecture hall inventory.

| Field | Type | Nullable | Uniqueness | Allowed Values / Range | Units | Validation Rule | Description |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- | :--- |
| `room_id` | VARCHAR(16) | No | PK | `ROM-0001` .. `ROM-9999` | - | Regex `^ROM-\d{4}$` | Room inventory ID |
| `building` | VARCHAR(50) | No | No | String | - | Length 3-50 | Building location and room number |
| `capacity` | INTEGER | No | No | 20, 30, 40, 60, 120 | Seats | `capacity > 0` | Physical seating capacity |
| `room_type` | VARCHAR(30) | No | No | `'lecture_hall'`, `'classroom'`, `'seminar'`, `'computer_lab'` | - | Enum check | Physical room configuration |
| `available_slots` | INTEGER | No | No | 0 to 20 | Slots | `>= 0` | Weekly timetable slots |

---

## 2. Plan and Demand Tables

### `student_plan`
Synthetic learner degree progression profiles.

| Field | Type | Nullable | Uniqueness | Allowed Values / Range | Units | Validation Rule | Description |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- | :--- |
| `student_plan_id` | VARCHAR(16) | No | PK | `STP-000001` .. `STP-999999` | - | Regex `^STP-\d{6}$` | Degree plan ID |
| `student_ref` | VARCHAR(16) | No | No | `STU-000001` .. `STU-999999` | - | Regex `^STU-\d{6}$` | Synthetic anonymous student reference |
| `program_id` | VARCHAR(16) | No | No | Valid `program.program_id` | - | FK to `program` | Program enrolled |
| `start_term` | VARCHAR(20) | No | No | Valid term string | - | Format `YYYY-TT` | Matriculation semester |
| `planned_graduation_term` | VARCHAR(20) | No | No | Valid term string | - | `start_term <= planned_grad` | Anticipated graduation semester |
| `status` | VARCHAR(20) | No | No | `'active'`, `'graduated'`, `'withdrawn'`, `'on_leave'` | - | Enum check | Enrollment status |

---

### `student_plan_completed_course`
Historical transcripts of completed coursework with earned grades.

| Field | Type | Nullable | Uniqueness | Allowed Values / Range | Units | Validation Rule | Description |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- | :--- |
| `student_plan_id` | VARCHAR(16) | No | Composite PK | Valid `student_plan.student_plan_id` | - | FK to `student_plan` | Student plan |
| `course_id` | VARCHAR(16) | No | Composite PK | Valid `course.course_id` | - | FK to `course` | Course completed |
| `term` | VARCHAR(20) | No | No | Valid term | - | Format `YYYY-TT` | Semester completed |
| `grade` | VARCHAR(5) | No | No | `'A'`, `'B'`, `'C'`, `'D'`, `'F'` | Letter | Enum check | Earned letter grade |

---

### `registration_interest`
Student elective and core course demand expressions.

| Field | Type | Nullable | Uniqueness | Allowed Values / Range | Units | Validation Rule | Description |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- | :--- |
| `interest_id` | VARCHAR(16) | No | PK | `INT-000001` .. `INT-999999` | - | Regex `^INT-\d{6}$` | Registration intent ID |
| `student_plan_id` | VARCHAR(16) | No | No | Valid `student_plan.student_plan_id` | - | FK to `student_plan` | Interested student |
| `course_id` | VARCHAR(16) | No | No | Valid `course.course_id` | - | FK to `course` | Target course |
| `term` | VARCHAR(20) | No | No | Valid term string | - | Format `YYYY-TT` | Semester intended |
| `priority` | INTEGER | No | No | 1 to 5 | Rank | `1 <= priority <= 5` | Student priority choice (1=highest) |
| `status` | VARCHAR(20) | No | No | `'active'`, `'fulfilled'`, `'cancelled'`, `'waitlisted'` | - | Enum check | Request status |
| `created_on` | DATE | No | No | ISO-8601 Date | Days | Valid date | Request timestamp |

---

## 3. Results, Allocation, and Event Tables

### `demand_forecast`
Calculated course demand projections for the upcoming target semester.

| Field | Type | Nullable | Uniqueness | Allowed Values / Range | Units | Validation Rule | Description |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- | :--- |
| `forecast_id` | VARCHAR(20) | No | PK | `DFC-2026-000001` .. | - | Regex `^DFC-\d{4}-\d{6}$` | Forecast record ID |
| `course_id` | VARCHAR(16) | No | No | Valid `course.course_id` | - | FK to `course` | Forecast course |
| `target_term` | VARCHAR(20) | No | No | `'2026-FA'` | - | Matches target term | Forecast semester |
| `window_terms_used` | VARCHAR(80) | No | No | Comma-delimited list | - | 3 historical terms | Historical basis window |
| `method` | VARCHAR(50) | No | No | `'weighted_moving_average_3term'` | - | Known algorithm | Forecasting method |
| `forecast_demand` | INTEGER | No | No | `>= 0` | Students | `>= 0` | Projected student demand |
| `lower_bound` | INTEGER | No | No | `>= 0` | Students | `<= upper_bound` | 85% confidence lower threshold |
| `upper_bound` | INTEGER | No | No | `>= lower_bound` | Students | `>= lower_bound` | 115% confidence upper threshold |

---

### `section`
Actual scheduled classroom course sections.

| Field | Type | Nullable | Uniqueness | Allowed Values / Range | Units | Validation Rule | Description |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- | :--- |
| `section_id` | VARCHAR(20) | No | PK | `SEC-2026-000001` .. | - | Regex `^SEC-\d{4}-\d{6}$` | Unique section ID |
| `course_id` | VARCHAR(16) | No | No | Valid `course.course_id` | - | FK to `course` | Course offered |
| `term` | VARCHAR(20) | No | No | E.g. `'2026-FA'` | - | Valid term string | Semester offered |
| `room_id` | VARCHAR(16) | No | No | Valid `room.room_id` | - | FK to `room` | Allocated classroom |
| `day_of_week` | VARCHAR(10) | No | No | `'MWF'`, `'TTH'` | - | Enum check | Meeting days |
| `start_time` | VARCHAR(10) | No | No | `HH:MM:SS` | Time | Valid time | Class start time |
| `end_time` | VARCHAR(10) | No | No | `HH:MM:SS` | Time | `start_time < end_time` | Class end time |
| `capacity` | INTEGER | No | No | 1 to 120 | Seats | `capacity <= room.capacity` | Enrolled seating capacity |
| `status` | VARCHAR(20) | No | No | `'proposed'`, `'approved'`, `'changed'`, `'cancelled'` | - | Enum check | Section status |

---

### `section_event`
Audit trail of section state changes.

| Field | Type | Nullable | Uniqueness | Allowed Values / Range | Units | Validation Rule | Description |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- | :--- |
| `event_id` | VARCHAR(20) | No | PK | `SEV-2026-000001` .. | - | Regex `^SEV-\d{4}-\d{6}$` | Event record ID |
| `section_id` | VARCHAR(20) | No | No | Valid `section.section_id` | - | FK to `section` | Target section |
| `event_type` | VARCHAR(20) | No | No | `'proposed'`, `'approved'`, `'changed'`, `'cancelled'` | - | Enum check | State change type |
| `event_ts` | VARCHAR(30) | No | No | ISO-8601 Timestamp | UTC | Valid ISO timestamp | Audit timestamp |
| `reason` | TEXT | No | No | String | - | Non-empty | Business rationale for transition |

---

### `workload_assignment`
Instructor assignments to scheduled sections.

| Field | Type | Nullable | Uniqueness | Allowed Values / Range | Units | Validation Rule | Description |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- | :--- |
| `assignment_id` | VARCHAR(20) | No | PK | `WLA-2026-000001` .. | - | Regex `^WLA-\d{4}-\d{6}$` | Workload assignment ID |
| `section_id` | VARCHAR(20) | No | No | Valid `section.section_id` | - | FK to `section` | Assigned section |
| `faculty_id` | VARCHAR(16) | No | No | Valid `faculty.faculty_id` | - | FK to `faculty` | Assigned instructor |
| `assigned_hours` | REAL | No | No | 1.0 to 6.0 | Hours/Week | `assigned_hours > 0` | Contact hours credited |
| `status` | VARCHAR(20) | No | No | `'assigned'`, `'unassigned'`, `'flagged'`, `'reallocated'` | - | Enum check | Workload assignment status |
| `decision_reason_code`| VARCHAR(50) | No | No | String code | - | Known code | Formal decision reason code |

---

### `assignment_event`
Audit trail of faculty assignments.

| Field | Type | Nullable | Uniqueness | Allowed Values / Range | Units | Validation Rule | Description |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- | :--- |
| `event_id` | VARCHAR(20) | No | PK | `AEV-2026-000001` .. | - | Regex `^AEV-\d{4}-\d{6}$` | Event ID |
| `assignment_id` | VARCHAR(20) | No | No | Valid `workload_assignment.assignment_id` | - | FK to `workload_assignment` | Target assignment |
| `event_type` | VARCHAR(20) | No | No | `'assigned'`, `'unassigned'`, `'flagged'`, `'reallocated'` | - | Enum check | Event action |
| `event_ts` | VARCHAR(30) | No | No | ISO-8601 Timestamp | UTC | Valid ISO timestamp | Audit timestamp |
| `reason` | TEXT | No | No | String | - | Non-empty | Audit rationale |

---

### `unmet_demand`
Tracks student demand that could not be satisfied.

| Field | Type | Nullable | Uniqueness | Allowed Values / Range | Units | Validation Rule | Description |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- | :--- |
| `unmet_id` | VARCHAR(20) | No | PK | `UMD-2026-000001` .. | - | Regex `^UMD-\d{4}-\d{6}$` | Record ID |
| `course_id` | VARCHAR(16) | No | No | Valid `course.course_id` | - | FK to `course` | Course with deficit |
| `term` | VARCHAR(20) | No | No | E.g. `'2026-FA'` | - | Valid term string | Semester |
| `unmet_count` | INTEGER | No | No | `>= 0` | Students | `>= 0` | Number of unaccommodated seats |
| `reason_code` | VARCHAR(50) | No | No | `'no_faculty'`, `'no_room'`, `'capacity_limit'`, `'prereq_gap'`, `'zero_demand'` | - | Enum check | Core operational root cause |

---

### `decision_log`
Comprehensive explainability log of every allocation, staffing, and rejection decision.

| Field | Type | Nullable | Uniqueness | Allowed Values / Range | Units | Validation Rule | Description |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- | :--- |
| `decision_id` | VARCHAR(20) | No | PK | `DCL-2026-000001` .. | - | Regex `^DCL-\d{4}-\d{6}$` | Decision log ID |
| `entity_type` | VARCHAR(30) | No | No | `'section'`, `'course'`, `'faculty'` | - | Non-empty | Target entity class |
| `entity_id` | VARCHAR(30) | No | No | Valid entity ID | - | Non-empty | Target entity ID |
| `decision` | VARCHAR(50) | No | No | E.g. `'allocated'`, `'rejected'` | - | Non-empty | Final decision outcome |
| `reason_code` | VARCHAR(50) | No | No | E.g. `'STAFFED_QUALIFIED'` | - | Non-empty | Standardized reason code |
| `explanation_text`| TEXT | No | No | String | - | Non-empty | Plain English human-readable explanation |
| `inputs_snapshot` | TEXT | No | No | JSON string | - | Valid JSON format | Serialized snapshot of criteria evaluated |

