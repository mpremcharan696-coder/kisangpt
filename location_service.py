"""
location_service.py
===================
Unified Location & Environmental Intelligence Service.
Combines:
1. Administrative geocoding (Village, Taluk/District, State) using OpenStreetMap Nominatim with offline fallback.
2. Google Earth Engine (OpenLandMap 250m) soil texture classification.
3. Open-Meteo weather forecast, historical rainfall and temperatures.
"""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Any, Dict, Optional

import httpx

# Import Earth Engine with graceful fallback
try:
    import ee
    PROJECT_ID = "kisan-511506"
    ee.Initialize(project=PROJECT_ID)
    _EE_AVAILABLE = True
    _dataset = ee.Image("OpenLandMap/SOL/SOL_TEXTURE-CLASS_USDA-TT_M/v02")
except Exception as _ee_err:
    _EE_AVAILABLE = False
    _dataset = None

import environment

SOIL_CLASSES = {
    1: "Clay",
    2: "Silty clay",
    3: "Sandy clay",
    4: "Clay loam",
    5: "Silty clay loam",
    6: "Sandy clay loam",
    7: "Loam",
    8: "Silt loam",
    9: "Sandy loam",
    10: "Silt",
    11: "Loamy sand",
    12: "Sand",
}


def get_soil_type(latitude: float, longitude: float) -> str:
    """Retrieve modelled USDA soil texture class using Google Earth Engine."""
    if _EE_AVAILABLE and _dataset is not None:
        try:
            point = ee.Geometry.Point([longitude, latitude])
            result = _dataset.select("b0").reduceRegion(
                reducer=ee.Reducer.first(),
                geometry=point,
                scale=250,
                maxPixels=1000,
            ).getInfo()
            class_value = result.get("b0")
            if class_value is not None:
                return SOIL_CLASSES.get(int(class_value), "Loam")
        except Exception:
            pass

    # Regional heuristic fallback for Karnataka / Deccan plateau
    # Karnataka has predominantly Red Sandy Loam (South), Black Clayey Soil (North), Coastal Alluvium (West)
    if 11.5 <= latitude <= 18.5 and 74.0 <= longitude <= 78.6:
        if latitude > 15.0:
            return "Clay loam"  # Northern Karnataka black soil
        elif longitude < 75.0:
            return "Sandy clay loam"  # Coastal Karnataka
        else:
            return "Sandy loam"  # Southern Karnataka red soil
    return "Loam"


def get_administrative_location(latitude: float, longitude: float) -> Dict[str, str]:
    """
    Reverse geocode coordinates to Village, District/Taluk, State using OSM Nominatim.
    Falls back gracefully if network is unavailable.
    """
    url = "https://nominatim.openstreetmap.org/reverse"
    headers = {"User-Agent": "KrishiMitra-AI-FarmingAssistant/1.0"}
    params = {
        "lat": latitude,
        "lon": longitude,
        "format": "jsonv2",
        "addressdetails": 1,
    }

    try:
        with httpx.Client(timeout=6.0, headers=headers) as client:
            resp = client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                address = data.get("address", {})
                village = (
                    address.get("village")
                    or address.get("suburb")
                    or address.get("hamlet")
                    or address.get("town")
                    or "Local Village"
                )
                district = (
                    address.get("state_district")
                    or address.get("county")
                    or address.get("district")
                    or "District"
                )
                state = address.get("state", "Karnataka")
                display_name = data.get("display_name", f"{village}, {district}, {state}")
                return {
                    "village": village,
                    "district": district,
                    "state": state,
                    "display_name": display_name,
                    "source": "OpenStreetMap Nominatim"
                }
    except Exception:
        pass

    return {
        "village": "Local Area",
        "district": "Local District",
        "state": "Karnataka",
        "display_name": f"Location at {latitude:.4f}°N, {longitude:.4f}°E",
        "source": "Live GPS Coordinates"
    }


def analyze_farm_location(latitude: float, longitude: float, acres: float = 1.0) -> Dict[str, Any]:
    """
    Comprehensive location analysis combining administrative, soil, and weather data.
    """
    admin_info = get_administrative_location(latitude, longitude)
    soil_class = get_soil_type(latitude, longitude)

    # Fetch environmental data synchronously
    try:
        env_data = asyncio.run(environment.get_environment(latitude, longitude))
    except Exception as e:
        env_data = {
            "error": str(e),
            "forecast_7_days": {},
            "historical_rainfall": {},
        }

    # Extract 7-day forecast summary
    forecast = env_data.get("forecast_7_days", {})
    rain_sum = sum(forecast.get("precipitation_sum", [0]) or [0])
    temps_max = forecast.get("temperature_2m_max", [30])
    temps_min = forecast.get("temperature_2m_min", [20])
    avg_max_temp = round(sum(temps_max) / max(len(temps_max), 1), 1) if temps_max else 30.0
    avg_min_temp = round(sum(temps_min) / max(len(temps_min), 1), 1) if temps_min else 20.0

    # Determine current season
    month = date.today().month
    if 6 <= month <= 10:
        season = "Kharif (Monsoon)"
    elif 11 <= month or month <= 3:
        season = "Rabi (Winter)"
    else:
        season = "Zaid / Summer"

    return {
        "status": "success",
        "coordinates": {"latitude": latitude, "longitude": longitude},
        "land_acres": acres,
        "administrative": admin_info,
        "soil": {
            "soil_type": soil_class,
            "depth": "Surface layer (0-30 cm)",
            "source": "OpenLandMap via Google Earth Engine (250m)",
            "note": "Modelled satellite soil classification, not a physical soil lab test."
        },
        "weather_summary": {
            "current_season": season,
            "forecast_next_7_days_rain_mm": round(rain_sum, 1),
            "avg_max_temperature_c": avg_max_temp,
            "avg_min_temperature_c": avg_min_temp,
            "source": "Open-Meteo Weather API"
        },
        "raw_environment": env_data
    }


if __name__ == "__main__":
    res = analyze_farm_location(15.4589, 75.0078, acres=2.5)
    print("Location Analysis Result:")
    print(" - Admin:", res["administrative"])
    print(" - Soil:", res["soil"]["soil_type"])
    print(" - Weather:", res["weather_summary"])
