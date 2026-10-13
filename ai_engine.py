"""
ai_engine.py
============
Groq AI Engine for Intelligent Agricultural Budgeting & Crop Lifecycle Tasks.
Powered by Groq LLM (openai/gpt-oss-120b / qwen/qwen3.8-27b).

Generates and enriches:
1. Itemized Cultivation Budget for ANY crop & land area.
2. Growth-stage and day-specific field tasks with step-by-step instructions,
   materials, equipment, duration, safety precautions, and costs.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL = "openai/gpt-oss-120b"

_client: Optional[Groq] = None

def get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=API_KEY)
    return _client


def _clean_json_response(raw_text: str) -> Dict[str, Any]:
    """Extract and parse valid JSON from LLM response text."""
    # Look for code block or first { to last }
    text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start : end + 1]

    try:
        return json.loads(text)
    except Exception as e:
        # Fallback regex extraction or simple repair
        text_fixed = re.sub(r",\s*([\]}])", r"\1", text)
        return json.loads(text_fixed)


def generate_budget_ai(crop_name: str, acres: float = 1.0, season: str = "Kharif") -> Dict[str, Any]:
    """
    Generate an itemized cultivation budget for any crop and acreage using AI.
    """
    client = get_client()
    system_prompt = """
You are an expert Indian agricultural economist and agronomist adhering to ICAR and State Agricultural University (SAU) benchmarks.
Generate an accurate, itemized cultivation budget for the requested crop and land area in acres in Indian Rupees (INR).
Ensure NO double-counting across categories:
- Seed (certified seed quantity and cost)
- Fertilizer (Urea, DAP, MOP, FYM / Compost, micronutrients)
- Labour (person-days and operations: sowing, weeding, fertilizer, harvesting)
- Machinery (tractor ploughing, rotavator, threshing hours)
- Irrigation (electricity/diesel pump events)
- Harvesting & Post-Harvest (mechanical or manual contract)
- Other (seed treatment, bio-pesticides, transport to mandi)

Return valid JSON strictly adhering to this structure:
{
  "crop_name": "Crop Name",
  "season": "Kharif / Rabi / Summer",
  "acres": 1.0,
  "yield_per_acre_quintals": 18.0,
  "expected_yield_quintals": 18.0,
  "market_price_per_quintal": 2200.0,
  "gross_revenue": 39600.0,
  "total_cultivation_cost": 22000.0,
  "net_profit": 17600.0,
  "roi_percent": 80.0,
  "breakdown": {
    "seed": 2000.0,
    "fertilizer": 6000.0,
    "labour": 5500.0,
    "machinery": 4500.0,
    "irrigation": 1800.0,
    "harvesting": 1500.0,
    "other": 700.0
  },
  "line_items": [
    {
      "category": "seed",
      "name": "Certified Seed",
      "quantity": 10.0,
      "unit": "kg",
      "cost": 2000.0
    },
    {
      "category": "fertilizer",
      "name": "Urea (46% N)",
      "quantity": 90.0,
      "unit": "kg",
      "cost": 484.0
    },
    {
      "category": "fertilizer",
      "name": "DAP (18:46:0)",
      "quantity": 50.0,
      "unit": "kg",
      "cost": 1350.0
    },
    {
      "category": "labour",
      "name": "Weeding & Intercultivation",
      "quantity": 4.0,
      "unit": "person-days",
      "cost": 1500.0
    },
    {
      "category": "machinery",
      "name": "Tractor Ploughing & Tilth",
      "quantity": 2.0,
      "unit": "hours",
      "cost": 2200.0
    }
  ]
}
"""

    user_prompt = f"Calculate complete cultivation budget for Crop: '{crop_name}', Land Area: {acres} acres, Season: '{season}'. Scale all quantities and costs precisely for {acres} acres. Return valid JSON only."

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=2000
        )
        data = _clean_json_response(response.choices[0].message.content)
        data["crop"] = data.get("crop_name", crop_name)
        data["acres"] = acres
        return data
    except Exception as e:
        # Fallback heuristic calculation if AI call times out
        base_cost_per_acre = 16000.0
        total_cost = base_cost_per_acre * acres
        gross_rev = 35000.0 * acres
        return {
            "crop": crop_name,
            "crop_name": crop_name,
            "season": season,
            "acres": acres,
            "yield_per_acre_quintals": 15.0,
            "expected_yield_quintals": round(15.0 * acres, 1),
            "market_price_per_quintal": 2300.0,
            "gross_revenue": gross_rev,
            "total_cultivation_cost": total_cost,
            "net_profit": gross_rev - total_cost,
            "roi_percent": round(((gross_rev - total_cost) / total_cost) * 100, 2),
            "breakdown": {
                "seed": round(total_cost * 0.12, 2),
                "fertilizer": round(total_cost * 0.30, 2),
                "labour": round(total_cost * 0.25, 2),
                "machinery": round(total_cost * 0.18, 2),
                "irrigation": round(total_cost * 0.08, 2),
                "harvesting": round(total_cost * 0.05, 2),
                "other": round(total_cost * 0.02, 2),
            },
            "line_items": [
                {"category": "seed", "name": f"Certified {crop_name} Seed", "quantity": round(10.0 * acres, 1), "unit": "kg", "cost": round(total_cost * 0.12, 2)},
                {"category": "fertilizer", "name": "Basal Fertilizers (NPK / DAP / Urea)", "quantity": round(120.0 * acres, 1), "unit": "kg", "cost": round(total_cost * 0.30, 2)},
                {"category": "labour", "name": "Manual Weeding & Field Labour", "quantity": round(6.0 * acres, 1), "unit": "person-days", "cost": round(total_cost * 0.25, 2)},
                {"category": "machinery", "name": "Tractor Tillage & Sowing", "quantity": round(3.0 * acres, 1), "unit": "hours", "cost": round(total_cost * 0.18, 2)},
            ]
        }


def generate_tasks_ai(crop_name: str, day: int = 0, acres: float = 1.0) -> Dict[str, Any]:
    """
    Generate agricultural tasks for any crop and day using AI.
    """
    client = get_client()
    system_prompt = """
You are an expert Indian agricultural extension officer.
Generate actionable, growth-stage-specific farming tasks for the specified crop on the requested day in the crop cycle (Day 0 = Sowing Day, negative days = pre-sowing land prep, positive days = vegetative/flowering/harvesting stages).

Return valid JSON strictly adhering to this structure:
{
  "crop": "Crop Name",
  "crop_day": 0,
  "acres": 1.0,
  "tasks_count": 2,
  "daily_total": 4500.0,
  "tasks": [
    {
      "task_name": "Specific Agricultural Task Title",
      "growth_stage": "e.g. Sowing & Emergence",
      "purpose": "Why this task is necessary",
      "step_by_step_instructions": "1. Step one... 2. Step two...",
      "materials_required": [
        { "item_name": "Input / Material", "quantity_per_acre": 5.0, "unit": "kg" }
      ],
      "equipment_needed": "e.g. Seed drill / Tractor / Sprayer",
      "estimated_duration": "1 day",
      "safety_precautions": "e.g. Wear gloves when handling treated seed",
      "task_total": 2500.0
    }
  ]
}
"""

    user_prompt = f"Provide scheduled agricultural tasks for Crop: '{crop_name}', Crop Cycle Day: {day}, Cultivated Land Area: {acres} acres. Scale materials and costs for {acres} acres. Return valid JSON only."

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=2000
        )
        data = _clean_json_response(response.choices[0].message.content)
        data["crop"] = crop_name
        data["crop_day"] = day
        data["acres"] = acres
        if "tasks" in data:
            data["tasks_count"] = len(data["tasks"])
            data["daily_total"] = round(sum(t.get("task_total", 0.0) for t in data["tasks"]), 2)
        return data
    except Exception as e:
        # Graceful fallback task
        return {
            "crop": crop_name,
            "crop_day": day,
            "acres": acres,
            "tasks_count": 1,
            "daily_total": 1200.0 * acres,
            "tasks": [
                {
                    "task_name": f"{crop_name} Field Operations & Stage Inspection",
                    "growth_stage": "Sowing Day" if day == 0 else f"Day {day} Management",
                    "purpose": f"Ensure optimal growth environment and nutrient uptake for {crop_name}.",
                    "step_by_step_instructions": f"1. Inspect soil moisture and tilth. 2. Verify row-to-row spacing. 3. Monitor for early pests or moisture deficit.",
                    "materials_required": [{"item_name": f"Certified {crop_name} inputs", "quantity_per_acre": 5.0, "unit": "kg"}],
                    "equipment_needed": "Hand tools / Tractor implement",
                    "estimated_duration": "4-6 hours",
                    "safety_precautions": "Use protective clothing and follow local agricultural guidelines.",
                    "task_total": round(1200.0 * acres, 2)
                }
            ]
        }


if __name__ == "__main__":
    print("Testing generate_budget_ai for Ragi (2.5 acres)...")
    b = generate_budget_ai("Ragi", 2.5)
    print("Budget:", b.get("total_cultivation_cost"), "Revenue:", b.get("gross_revenue"))

    print("\nTesting generate_tasks_ai for Groundnut (Day 0, 2.5 acres)...")
    t = generate_tasks_ai("Groundnut", 0, 2.5)
    print("Tasks Count:", t.get("tasks_count"), "Tasks:", [x.get("task_name") for x in t.get("tasks", [])])
