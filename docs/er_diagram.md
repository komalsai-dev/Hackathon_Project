# Entity-Relationship (ER) Diagram

The data model uses 18 normalized tables spanning Master Data, Student Planning, Demand Forecasting, Classroom/Faculty Allocation, Audit Trails, and Explainability.

```mermaid
erDiagram
    PROGRAM ||--o{ PROGRAM_COURSE : contains
    COURSE ||--o{ PROGRAM_COURSE : required_in
    COURSE ||--o{ PREREQUISITE : has_prerequisite
    COURSE ||--o{ PREREQUISITE : is_required_for
    FACULTY ||--o{ FACULTY_SKILL : possesses
    COURSE ||--o{ FACULTY_SKILL : taught_by
    FACULTY ||--o{ AVAILABILITY : has_schedule
    PROGRAM ||--o{ STUDENT_PLAN : enrolled_in
    STUDENT_PLAN ||--o{ STUDENT_PLAN_COMPLETED_COURSE : records
    COURSE ||--o{ STUDENT_PLAN_COMPLETED_COURSE : completed_in
    STUDENT_PLAN ||--o{ REGISTRATION_INTEREST : expresses
    COURSE ||--o{ REGISTRATION_INTEREST : targeted_by
    COURSE ||--o{ DEMAND_FORECAST : has_forecast
    COURSE ||--o{ SECTION : instantiates
    ROOM ||--o{ SECTION : hosts
    SECTION ||--o{ SECTION_EVENT : audits
    SECTION ||--o{ WORKLOAD_ASSIGNMENT : staffed_by
    FACULTY ||--o{ WORKLOAD_ASSIGNMENT : assigned_to
    WORKLOAD_ASSIGNMENT ||--o{ ASSIGNMENT_EVENT : audits
    COURSE ||--o{ UNMET_DEMAND : deficit_for

    PROGRAM {
        varchar program_id PK
        varchar name
        varchar level
        varchar department
        varchar status
        date effective_from
        date effective_to
    }

    COURSE {
        varchar course_id PK
        varchar code UK
        varchar title
        integer credits
        integer level
        varchar category
        real contact_hours_per_week
        varchar status
    }

    PROGRAM_COURSE {
        varchar program_id PK,FK
        varchar course_id PK,FK
        varchar requirement_type
        integer recommended_term
    }

    PREREQUISITE {
        varchar prerequisite_id PK
        varchar course_id FK
        varchar required_course_id FK
        varchar min_grade
        date effective_from
        date effective_to
    }

    FACULTY {
        varchar faculty_id PK
        varchar name
        varchar department
        varchar employment_type
        real max_weekly_hours
        varchar status
    }

    FACULTY_SKILL {
        varchar faculty_id PK,FK
        varchar course_id PK,FK
        integer proficiency
        date certified_from
    }

    AVAILABILITY {
        varchar availability_id PK
        varchar faculty_id FK
        varchar term
        varchar day_of_week
        varchar start_time
        varchar end_time
        varchar availability_type
    }

    ROOM {
        varchar room_id PK
        varchar building
        integer capacity
        varchar room_type
        integer available_slots
    }

    STUDENT_PLAN {
        varchar student_plan_id PK
        varchar student_ref
        varchar program_id FK
        varchar start_term
        varchar planned_graduation_term
        varchar status
    }

    STUDENT_PLAN_COMPLETED_COURSE {
        varchar student_plan_id PK,FK
        varchar course_id PK,FK
        varchar term
        varchar grade
    }

    REGISTRATION_INTEREST {
        varchar interest_id PK
        varchar student_plan_id FK
        varchar course_id FK
        varchar term
        integer priority
        varchar status
        date created_on
    }

    DEMAND_FORECAST {
        varchar forecast_id PK
        varchar course_id FK
        varchar target_term
        varchar window_terms_used
        varchar method
        integer forecast_demand
        integer lower_bound
        integer upper_bound
    }

    SECTION {
        varchar section_id PK
        varchar course_id FK
        varchar term
        varchar room_id FK
        varchar day_of_week
        varchar start_time
        varchar end_time
        integer capacity
        varchar status
    }

    SECTION_EVENT {
        varchar event_id PK
        varchar section_id FK
        varchar event_type
        varchar event_ts
        text reason
    }

    WORKLOAD_ASSIGNMENT {
        varchar assignment_id PK
        varchar section_id FK
        varchar faculty_id FK
        real assigned_hours
        varchar status
        varchar decision_reason_code
    }

    ASSIGNMENT_EVENT {
        varchar event_id PK
        varchar assignment_id FK
        varchar event_type
        varchar event_ts
        text reason
    }

    UNMET_DEMAND {
        varchar unmet_id PK
        varchar course_id FK
        varchar term
        integer unmet_count
        varchar reason_code
    }

    DECISION_LOG {
        varchar decision_id PK
        varchar entity_type
        varchar entity_id
        varchar decision
        varchar reason_code
        text explanation_text
        text inputs_snapshot
    }
```

