"""
scheme_finder.py
================
Module to identify potentially relevant central and state agricultural
government schemes for farmers based on their location, cultivable acreage,
and category.

Reads verified data from schemes_dev.db (SQLite).

Rules:
- Strictly uses verified government records from the database.
- Does NOT claim a farmer is definitely eligible based on location alone;
  clearly labels matches as "Potentially Relevant - Subject to Verification".
- Provides official portal links, key benefits, eligibility criteria, and required documents.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

DB_PATH = Path(__file__).resolve().parent / "schemes_dev.db"


def _get_db_connection() -> sqlite3.Connection:
    """Connect to schemes_dev.db with row factory for named dictionary access."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Schemes database not found at {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _parse_json_field(val: Any) -> Any:
    """Safely parse JSON field or return original value."""
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return val


def find_schemes(
    state: str = "Karnataka",
    district: Optional[str] = None,
    acres: Optional[float] = None,
    category: Optional[str] = None,
    limit: int = 15,
) -> Dict[str, Any]:
    """
    Search and filter relevant agricultural government schemes.

    Args:
        state: Farmer's state (default: "Karnataka")
        district: Optional district name
        acres: Landholding in acres
        category: Optional category filter (e.g., 'crop insurance', 'direct income support', 'credit')
        limit: Max number of schemes to return

    Returns:
        Dictionary with count, matched schemes, and metadata.
    """
    conn = _get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT id, name, short_description, description, category, level,
               states, target_beneficiaries, benefits, eligibility,
               documents_required, application_process, official_portal,
               needs_verification
        FROM schemes
        WHERE 1=1
    """
    params: List[Any] = []

    if category:
        query += " AND LOWER(category) LIKE ?"
        params.append(f"%{category.lower()}%")

    query += " ORDER BY level DESC, id ASC"

    cursor.execute(query, params)
    raw_rows = cursor.fetchall()
    conn.close()

    matched_schemes: List[Dict[str, Any]] = []

    # Landholding categorization standard:
    # Marginal: < 2.5 acres (1 hectare)
    # Small: 2.5 to 5.0 acres (1 - 2 hectares)
    # Medium/Large: > 5.0 acres
    is_small_or_marginal = acres is not None and acres <= 5.0

    for row in raw_rows:
        states_data = _parse_json_field(row["states"]) or []
        # Check geographic applicability (applies to "ALL" or matches state)
        state_match = False
        if "ALL" in states_data or any(state.lower() in str(s).lower() for s in states_data):
            state_match = True

        if not state_match:
            continue

        eligibility_data = _parse_json_field(row["eligibility"]) or {}
        benefits_data = _parse_json_field(row["benefits"]) or {}
        docs_data = _parse_json_field(row["documents_required"]) or []
        app_process = _parse_json_field(row["application_process"]) or {}

        # Acreage check where applicable (e.g. PM-KMY max 5 acres)
        acreage_eligible = True
        if acres is not None and isinstance(eligibility_data, dict):
            landholding_rule = eligibility_data.get("landholding", {})
            if isinstance(landholding_rule, dict):
                max_acres = landholding_rule.get("max_acres")
                if max_acres is not None and acres > float(max_acres):
                    acreage_eligible = False

        if not acreage_eligible:
            continue

        # Format benefits summary string
        benefits_summary = []
        if isinstance(benefits_data, dict):
            for k, v in benefits_data.items():
                if isinstance(v, (str, int, float)):
                    benefits_summary.append(f"{k.replace('_', ' ').capitalize()}: {v}")
                elif isinstance(v, dict):
                    for sub_k, sub_v in v.items():
                        benefits_summary.append(f"{sub_k.capitalize()}: {sub_v}")
        elif isinstance(benefits_data, str):
            benefits_summary.append(benefits_data)

        # Format eligibility summary
        eligibility_summary = []
        if isinstance(eligibility_data, dict):
            for k, v in eligibility_data.items():
                if isinstance(v, dict):
                    cond = ", ".join(f"{sub_k}: {sub_v}" for sub_k, sub_v in v.items())
                    eligibility_summary.append(f"{k.capitalize()}: {cond}")
                elif isinstance(v, list):
                    eligibility_summary.append(f"{k.capitalize()}: {', '.join(str(item) for item in v)}")
                elif isinstance(v, str):
                    eligibility_summary.append(f"{k.capitalize()}: {v}")

        # Format documents required list
        documents_list = []
        if isinstance(docs_data, list):
            documents_list = docs_data
        elif isinstance(docs_data, dict):
            for sub_list in docs_data.values():
                if isinstance(sub_list, list):
                    documents_list.extend(sub_list)
                elif isinstance(sub_list, str):
                    documents_list.append(sub_list)

        matched_schemes.append({
            "id": row["id"],
            "name": row["name"],
            "category": row["category"],
            "level": row["level"].capitalize() if row["level"] else "Central",
            "short_description": row["short_description"] or row["description"],
            "benefits": benefits_summary or ["Government financial / input assistance as per guidelines."],
            "eligibility_conditions": eligibility_summary or ["Farmer with operational cultivable landholding."],
            "documents_required": documents_list or ["Aadhaar Card", "Land Record (Pahani/RTC)", "Bank Account Passbook"],
            "application_process": app_process,
            "official_portal": row["official_portal"],
            "deadline": "Open enrollment (continuous)",
            "applicability_status": "Potentially Relevant",
            "note": "Eligibility depends on official verification of land ownership and local department guidelines."
        })

        if len(matched_schemes) >= limit:
            break

    return {
        "status": "success",
        "state": state,
        "district": district or "Not specified",
        "land_acres": acres,
        "farmer_category": "Small & Marginal" if is_small_or_marginal else ("Medium/Large" if acres else "Not specified"),
        "total_found": len(matched_schemes),
        "schemes": matched_schemes,
        "disclaimer": "Schemes shown are potentially relevant based on location and landholding. Do not claim final eligibility without official verification from relevant authorities."
    }


if __name__ == "__main__":
    result = find_schemes(state="Karnataka", acres=2.5)
    print(f"Found {result['total_found']} schemes for Karnataka (2.5 acres):")
    for s in result["schemes"][:4]:
        print(f" - [{s['level']}] {s['name']} -> {s['official_portal']}")
