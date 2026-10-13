
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
import ee

from environment import get_environment
from ai_recommendations import recommend_crops

class CropRecommendationRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    irrigation: str
    farm_size_acres: float = Field(gt=0)
    planting_month: str
    farming_goal: str
app = FastAPI(title="Kisan Soil Assistant")

PROJECT_ID = "kisan-511506"

ee.Initialize(project=PROJECT_ID)

dataset = ee.Image(
    "OpenLandMap/SOL/SOL_TEXTURE-CLASS_USDA-TT_M/v02"
)

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
    12: "Sand"
}


def get_soil_type(latitude, longitude):
    point = ee.Geometry.Point([longitude, latitude])

    result = dataset.select("b0").reduceRegion(
        reducer=ee.Reducer.first(),
        geometry=point,
        scale=250,
        maxPixels=1000
    ).getInfo()

    class_value = result.get("b0")

    if class_value is None:
        return None

    class_id = int(class_value)

    return SOIL_CLASSES.get(class_id, "Unknown")


@app.get("/soil")
def soil(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180)
):
    try:
        soil_type = get_soil_type(latitude, longitude)

        if soil_type is None:
            raise HTTPException(
                status_code=404,
                detail="No soil data available at this location."
            )

        return {
            "latitude": latitude,
            "longitude": longitude,
            "soil_type": soil_type,
            "depth": "Surface layer",
            "source": "OpenLandMap via Google Earth Engine",
            "resolution_meters": 250,
            "note": "Modelled soil classification, not a live soil measurement."
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Soil data retrieval failed: {str(error)}"
        )


@app.get("/environment")
async def environment(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180)
):
    try:
        # Get all environmental data using the existing function.
        data = await get_environment(latitude, longitude)

        return data

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Environmental data retrieval failed: {str(error)}"
        )


@app.post("/recommend-crops")
async def crop_recommendations(
    request: CropRecommendationRequest,
):
    try:
        # Fetch soil information using your existing function.
        soil_type = await run_in_threadpool(
            get_soil_type,
            request.latitude,
            request.longitude,
        )

        if soil_type is None:
            raise HTTPException(
                status_code=404,
                detail="No soil data available at this location.",
            )

        soil_data = {
            "latitude": request.latitude,
            "longitude": request.longitude,
            "soil_type": soil_type,
            "depth": "Surface layer",
            "source": "OpenLandMap via Google Earth Engine",
            "resolution_meters": 250,
            "note": (
                "Modelled soil classification, "
                "not a live soil measurement."
            ),
        }

        # Fetch forecast, historical rainfall and elevation.
        environment_data = await get_environment(
            request.latitude,
            request.longitude,
        )

        farm_data = {
            "soil": soil_data,
            "environment": environment_data,
        }

        farmer_info = {
            "irrigation": request.irrigation,
            "farm_size_acres": request.farm_size_acres,
            "planting_month": request.planting_month,
            "farming_goal": request.farming_goal,
        }

        # Call Groq without blocking the event loop.
        result = await run_in_threadpool(
            recommend_crops,
            farm_data,
            farmer_info,
        )

        return {
            "location": {
                "latitude": request.latitude,
                "longitude": request.longitude,
            },
            "recommendations": result,
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Crop recommendation failed: {str(error)}",
        )
