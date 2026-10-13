
from ai_recommendations import recommend_crops

farm_data = {
    "soil": {
        "soil_type": "Clay loam",
        "depth": "Surface layer",
        "resolution_meters": 250,
        "note": "Modelled classification, not a soil test",
    },
    "elevation_m": 748,
    "historical_rainfall": {
        "average_annual_rainfall_mm": 1201.8,
        "average_rainfall_by_month": [
            {"month": "January", "average_rainfall_mm": 5.4},
            {"month": "February", "average_rainfall_mm": 1.5},
            {"month": "May", "average_rainfall_mm": 171.9},
            {"month": "July", "average_rainfall_mm": 197.9},
            {"month": "October", "average_rainfall_mm": 205.9},
        ],
    },
}

farmer_info = {
    "irrigation": "Unknown",
    "farm_size_acres": None,
    "planting_month": "Unknown",
    "farming_goal": "Not specified",
}

result = recommend_crops(farm_data, farmer_info)

print(result)
