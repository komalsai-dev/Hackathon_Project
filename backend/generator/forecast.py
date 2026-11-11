"""
Demand forecasting engine using historical term windows.

Formula:
  Demand_raw = 0.5 * H3 (2026-SU) + 0.3 * H2 (2026-SP) + 0.2 * H1 (2025-FA)
  Forecast_demand = round(Demand_raw * conversion_factor * category_factor)
  Lower_bound = max(0, round(Forecast_demand * 0.85))
  Upper_bound = round(Forecast_demand * 1.15) + 5

Demand strictly originates from historical registration windows, never from
arbitrary random numbers.
"""

import math
from typing import Dict, List, Any
from backend.generator.config import (
    HISTORICAL_TERMS,
    TARGET_TERM,
    POPULAR_ELECTIVE_BOOST,
    LOW_ENROLLMENT_DAMPENER,
)
from backend.generator.ids import make_forecast_id

def generate_forecasts(
    master_data: Dict[str, List[Dict[str, Any]]],
    history_data: Dict[str, List[Dict[str, Any]]]
) -> List[Dict[str, Any]]:
    """
    Calculate demand forecasts for all courses in TARGET_TERM ('2026-FA')
    using the last 3 historical terms ('2025-FA', '2026-SP', '2026-SU').
    """
    courses = master_data["course"]
    registration_interest = history_data["registration_interest"]

    # Count historical interest per (course_id, term)
    hist_counts: Dict[str, Dict[str, int]] = {c["course_id"]: {t: 0 for t in HISTORICAL_TERMS} for c in courses}
    for item in registration_interest:
        t = item["term"]
        cid = item["course_id"]
        if t in HISTORICAL_TERMS and cid in hist_counts:
            hist_counts[cid][t] += 1

    course_cat_map = {c["course_id"]: c["category"] for c in courses}
    window_str = ",".join(HISTORICAL_TERMS)
    method_name = "weighted_moving_average_3term"

    forecasts: List[Dict[str, Any]] = []

    for idx, c in enumerate(courses, start=1):
        cid = c["course_id"]
        cat = course_cat_map.get(cid, "standard")

        h1 = hist_counts[cid].get("2025-FA", 0)
        h2 = hist_counts[cid].get("2026-SP", 0)
        h3 = hist_counts[cid].get("2026-SU", 0)

        # 3-term weighted moving average: 0.2 for H1, 0.3 for H2, 0.5 for H3
        raw_wma = (0.2 * h1) + (0.3 * h2) + (0.5 * h3)

        # Category factor
        cat_mult = 1.0
        if cat == "popular_elective":
            cat_mult = POPULAR_ELECTIVE_BOOST
        elif cat == "low_enrollment":
            cat_mult = LOW_ENROLLMENT_DAMPENER

        # Conversion factor from interest to anticipated enrolled demand
        # (Standard academic retention factor: ~92%)
        conversion_factor = 0.92

        demand_val = max(0, int(round(raw_wma * conversion_factor * cat_mult)))
        
        # Calculate bounds
        lower_b = max(0, int(math.floor(demand_val * 0.85)))
        upper_b = int(math.ceil(demand_val * 1.15)) + 4

        forecast_id = make_forecast_id(2026, idx)
        forecasts.append({
            "forecast_id": forecast_id,
            "course_id": cid,
            "target_term": TARGET_TERM,
            "window_terms_used": window_str,
            "method": method_name,
            "forecast_demand": demand_val,
            "lower_bound": lower_b,
            "upper_bound": upper_b,
        })

    return forecasts

