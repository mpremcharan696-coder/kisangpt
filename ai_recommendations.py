
import os
import json

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError(
        "GROQ_API_KEY is missing. Check your .env file."
    )

client = Groq(api_key=api_key)

MODEL = "openai/gpt-oss-120b"


def recommend_crops(farm_data, farmer_info):
    """
    Generate preliminary crop recommendations using
    environmental data and farmer-provided information.
    """

    prompt_data = {
        "environmental_data": farm_data,
        "farmer_information": farmer_info,
    }

    system_prompt = """
You are an agricultural decision-support assistant.

Your job is to assess which crops may be suitable for a
farmer's location and explain the evidence and uncertainty.

DATA INTERPRETATION RULES:

1. Soil data:
   - Treat modelled soil classification as an estimate,
     not a physical soil test.
   - Do not invent soil pH, nutrients or soil depth.

2. Historical climate:
   - average_rainfall_by_month contains historical
     monthly rainfall averages in millimetres.
   - average_temperature_by_month contains historical
     averages of daily maximum and minimum temperatures
     for each calendar month, in degrees Celsius.
   - annual_temperature contains annual averages of daily
     maximum and minimum temperatures for complete years.
   - These summaries describe historical conditions,
     not the weather forecast.

3. Forecast:
   - forecast_7_days contains the upcoming daily forecast.
   - Use it only for short-term weather context.
   - Never present the seven-day forecast as a seasonal
     prediction or long-term climate average.

4. Water:
   - Distinguish rainfall from irrigation availability
     and groundwater measurements.
   - A borewell or well does not guarantee sufficient
     water supply.
   - Groundwater depth is measured downward from ground
     level. A missing value means it is unknown.
   - Consider the date of a groundwater measurement.
   - Never invent groundwater levels or irrigation data.

5. Crop assessment:
   - Consider soil, historical rainfall, historical
     temperatures, current forecast, planting month,
     water source and irrigation reliability.
   - Do not assume a crop is suitable from soil type alone.
   - Do not invent locally validated planting calendars,
     crop requirements, yields, market prices or profits.
   - If crop-specific requirements are not established by
     the supplied evidence, clearly state the uncertainty.
   - Do not guarantee that any crop will succeed.
   - Identify missing information needed to improve
     the assessment.

Return up to five plausible crop recommendations.
Explain the evidence for each and identify risks.

Return valid JSON only, using this structure:

{
  "recommendations": [
    {
      "crop": "Crop name",
      "suitability": "Potentially suitable / Uncertain",
      "reasons": ["Evidence-based reason"],
      "water_needs": "General needs and known uncertainties",
      "risks": ["Potential risk"],
      "missing_information": ["Information needed"]
    }
  ],
  "general_advice": ["Advice"],
  "limitations": ["Limitation"]
}
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": (
                    "Assess preliminary crop suitability using "
                    "the following JSON data. Do not assume "
                    "missing values are known.\n\n"
                    + json.dumps(prompt_data, indent=2)
                ),
            },
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    answer = response.choices[0].message.content

    if not answer:
        raise ValueError("The AI returned an empty response.")

    try:
        result = json.loads(answer)
    except json.JSONDecodeError as error:
        raise ValueError(
            "The AI did not return valid JSON."
        ) from error

    if not isinstance(result, dict):
        raise ValueError("The AI response must be a JSON object.")

    if not isinstance(result.get("recommendations"), list):
        raise ValueError(
            "The AI response is missing the recommendations list."
        )

    return result
