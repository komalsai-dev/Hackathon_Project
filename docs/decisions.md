# Business Logic & Decision Rules

This document specifies the mathematical formulations, constraint logic, tie-break mechanisms, and standardized reason codes used across the forecasting and allocation pipeline.

---

## 1. Demand Forecasting Model

### Basis Window
Demand projections for the upcoming target semester (`2026-FA`) are computed strictly from historical student registration interest across the three preceding semesters:
* $H_1$: `2025-FA` (weight $w_1 = 0.20$)
* $H_2$: `2026-SP` (weight $w_2 = 0.30$)
* $H_3$: `2026-SU` (weight $w_3 = 0.50$, most recent)

### Formulation
$$\text{Raw Demand} = 0.20 \cdot H_1 + 0.30 \cdot H_2 + 0.50 \cdot H_3$$

### Category Conversion & Lift Multipliers
* **Conversion Factor:** $\alpha = 0.92$ (accounts for historical attrition between expressed interest and enrolled attendance).
* **Category Lift:**
  * `popular_elective`: Multiplier $\beta = 1.30$ (+30% surge based on popularity trending).
  * `low_enrollment`: Multiplier $\beta = 0.65$ (-35% dampening).
  * `core` / `standard`: Multiplier $\beta = 1.00$.

$$\text{Forecast Demand} = \max\left(0, \operatorname{round}(\text{Raw Demand} \cdot \alpha \cdot \beta)\right)$$

### Confidence Bounds
* **Lower Bound:** $\max(0, \lfloor 0.85 \cdot \text{Forecast Demand} \rfloor)$
* **Upper Bound:** $\lceil 1.15 \cdot \text{Forecast Demand} \rceil + 4$

---

## 2. Section Sizing & Room Allocation

1. **Target Demand per Section:**
   $$\text{Target Capacity} = \min(\text{Remaining Course Demand}, 40)$$
2. **Best-Fit Room Selection:**
   * Finds the smallest available classroom with $\text{Room Capacity} \ge \text{Target Capacity}$.
   * If all rooms of sufficient capacity are occupied during a slot, the largest available room is assigned.
   * Prevents classroom double-booking: A room can only host one section per time slot:
     $$\text{Unique Key} = (\text{room\_id}, \text{day\_of\_week}, \text{start\_time})$$

---

## 3. Faculty Workload Allocation & Ranking Heuristics

### Eligibility Filters (Hard Constraints)
An instructor $F$ is eligible to teach section $S$ for course $C$ at time slot $(D, T)$ if and only if:
1. **Skill Certification:** $(F, C) \in \text{FacultySkill}$.
2. **Slot Availability:** $(F, D, T) \in \text{Availability}$ with `availability_type == 'available'`.
3. **Active Status:** $F.\text{status} \ne \text{'on\_leave'}$.
4. **No Schedule Collision:** $F$ is not assigned to another section during slot $(D, T)$.
5. **Workload Cap:** 
   $$F.\text{assigned\_hours} + C.\text{contact\_hours\_per\_week} \le F.\text{max\_weekly\_hours}$$
   *(Full-time cap: 16.0 hrs/week; Adjunct cap: 8.0 hrs/week)*.

### Deterministic Tie-Breaking & Ranking
Eligible candidates are ranked by the following hierarchy:
1. **Proficiency Tier (Descending):** Priority given to Level 3 (Expert) instructors over Level 2 or 1.
2. **Current Workload (Ascending):** Priority given to instructors with fewer assigned weekly hours to balance department load.
3. **Faculty Identifier (Ascending):** Deterministic tie-break using alphabetical/numerical ID (`FAC-000001` before `FAC-000002`).

---

## 4. Arithmetic Reconciliation Identity

For every course in the catalog, the total forecast demand is strictly accounted for:
$$\text{Forecast Demand} = \sum_{S \in \text{Active Sections}} \text{Capacity}(S) + \text{Unmet Demand}$$

---

## 5. Standard Reason Codes

| Entity | Code | Meaning | Context |
| :--- | :--- | :--- | :--- |
| `workload_assignment` | `STAFFED_QUALIFIED` | Successfully assigned qualified instructor | Normal staffing |
| `unmet_demand` | `zero_demand` | Course had 0 forecast demand | No sections needed |
| `unmet_demand` | `no_faculty` | No certified instructor available within hours/schedule | Staffing constraint |
| `unmet_demand` | `no_room` | Classrooms fully booked during timetable slots | Facility constraint |
| `unmet_demand` | `capacity_limit` | Facility reached physical capacity limit | Facility limit |
| `decision_log` | `ZERO_FORECAST_DEMAND` | Forecast is 0; skipping section creation | Planning decision |
| `decision_log` | `NO_QUALIFIED_FACULTY_AVAILABLE` | Certified instructors rejected due to load/leave | Rejection log |
| `decision_log` | `NO_ROOM_AVAILABLE` | No room meets capacity requirements in slot | Rejection log |
| `ground_truth` | `FACULTY_LACKS_CERTIFIED_SKILL` | Assigned instructor lacks certified skill | Injected anomaly |
| `ground_truth` | `WORKLOAD_HOURS_EXCEEDED` | Instructor hours exceed max weekly limit | Injected anomaly |
| `ground_truth` | `SECTION_CAPACITY_UNDERSIZED` | Section capacity reduced below threshold | Injected anomaly |
| `ground_truth` | `PREREQUISITE_NOT_COMPLETED` | Registration interest submitted without prereq | Injected anomaly |
| `ground_truth` | `SCHEDULE_TIME_COLLISION` | Instructor double-booked in overlapping slot | Injected anomaly |

