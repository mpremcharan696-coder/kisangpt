from datetime import date, timedelta
import asyncio
import httpx


# --- Syllabus Helper Functions & Constants (Modules 1-3) ---

def is_leap_year(year):
    """Check if a year is a leap year using arithmetic modulus (Module 2)."""
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def get_days_in_month(year, month):
    """Return number of days in a month using conditionals and list (Modules 1, 2, 3)."""
    if month == 2:
        return 29 if is_leap_year(year) else 28
    if month in (4, 6, 9, 11):
        return 30
    return 31


MONTH_NAMES = [
    "",
    "January", "February", "March", "April",
    "May", "June", "July", "August",
    "September", "October", "November", "December",
]


async def get_environment(latitude, longitude):
    today = date.today()

    # Use data up to 5 days ago to avoid incomplete recent records.
    end_date = today - timedelta(days=5)
    start_date = end_date - timedelta(days=365 * 5)

    async with httpx.AsyncClient(timeout=30) as client:

        # 1. Get the 7-day weather forecast
        forecast_response = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "daily": (
                    "precipitation_sum,"
                    "precipitation_probability_max,"
                    "temperature_2m_max,"
                    "temperature_2m_min"
                ),
                "forecast_days": 7,
                "timezone": "auto",
            },
        )
        forecast_response.raise_for_status()

        # 2. Get historical weather data
        history_response = await client.get(
            "https://archive-api.open-meteo.com/v1/archive",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "daily": (
                    "precipitation_sum,"
                    "temperature_2m_max,"
                    "temperature_2m_min"
                ),
                "timezone": "auto",
            },
        )
        history_response.raise_for_status()

        # 3. Get elevation (optional; the API may be temporarily unavailable)
        elevation_m = None
        try:
            elevation_response = await client.get(
                "https://api.open-meteo.com/v1/elevation",
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                },
            )
            elevation_response.raise_for_status()
            elevation_data = elevation_response.json()
            values = elevation_data.get("elevation", [])
            if values and values[0] is not None:
                elevation_m = values[0]
        except (httpx.HTTPError, ValueError, KeyError):
            # Continue without elevation if this request fails.
            elevation_m = None

    forecast = forecast_response.json()
    historical = history_response.json()

    daily = historical["daily"]
    dates = daily["time"]
    rainfall_values = daily["precipitation_sum"]

    # Group rainfall and temperature by month and year using standard dictionaries (Module 3).
    monthly_data = {}
    yearly_data = {}
    monthly_max_temps = {}
    monthly_min_temps = {}
    yearly_max_temps = {}
    yearly_min_temps = {}

    for i in range(len(dates)):
        day_string = dates[i]
        month_key = day_string[:7]  # String slice YYYY-MM (Module 2)
        year = int(day_string[:4])   # Type conversion to int (Module 1)
        rainfall = rainfall_values[i]
        max_temp = daily["temperature_2m_max"][i]
        min_temp = daily["temperature_2m_min"][i]

        if rainfall is not None:
            if month_key not in monthly_data:
                monthly_data[month_key] = []
            monthly_data[month_key].append(rainfall)

            if year not in yearly_data:
                yearly_data[year] = []
            yearly_data[year].append(rainfall)

        if max_temp is not None:
            if month_key not in monthly_max_temps:
                monthly_max_temps[month_key] = []
            monthly_max_temps[month_key].append(max_temp)

            if year not in yearly_max_temps:
                yearly_max_temps[year] = []
            yearly_max_temps[year].append(max_temp)

        if min_temp is not None:
            if month_key not in monthly_min_temps:
                monthly_min_temps[month_key] = []
            monthly_min_temps[month_key].append(min_temp)

            if year not in yearly_min_temps:
                yearly_min_temps[year] = []
            yearly_min_temps[year].append(min_temp)

    # 4. Calculate rainfall totals for individual months.
    monthly_rainfall = []

    for month_key in sorted(monthly_data.keys()):
        parts = month_key.split("-")
        year = int(parts[0])
        month = int(parts[1])
        expected_days = get_days_in_month(year, month)

        # Check whether the requested date range covers the full month.
        expected_start = f"{year:04d}-{month:02d}-01"
        expected_end = f"{year:04d}-{month:02d}-{expected_days:02d}"

        dates_in_month = []
        for day_string in dates:
            if day_string.startswith(month_key):
                dates_in_month.append(day_string)

        month_rainfall_list = monthly_data.get(month_key, [])

        complete_month = (
            len(dates_in_month) == expected_days
            and min(dates_in_month) == expected_start
            and max(dates_in_month) == expected_end
            and len(month_rainfall_list) == expected_days
        )

        monthly_rainfall.append({
            "month": month_key,
            "rainfall_mm": round(
                sum(month_rainfall_list), 1
            ),
            "days_with_data": len(month_rainfall_list),
            "complete_month": bool(complete_month),
        })

    # 5. Calculate rainfall totals for individual years.
    yearly_rainfall = []

    for year in sorted(yearly_data.keys()):
        expected_days = 366 if is_leap_year(year) else 365
        expected_start = f"{year}-01-01"
        expected_end = f"{year}-12-31"

        dates_in_year = []
        for day_string in dates:
            if day_string.startswith(str(year)):
                dates_in_year.append(day_string)

        year_rainfall_list = yearly_data.get(year, [])

        complete_year = (
            len(dates_in_year) == expected_days
            and min(dates_in_year) == expected_start
            and max(dates_in_year) == expected_end
            and len(year_rainfall_list) == expected_days
        )

        yearly_rainfall.append({
            "year": year,
            "rainfall_mm": round(sum(year_rainfall_list), 1),
            "days_with_data": len(year_rainfall_list),
            "complete_year": bool(complete_year),
        })

    # 6. Calculate average rainfall for each calendar month.
    # Only use complete months to avoid misleading averages.
    monthly_totals = {}

    for record in monthly_rainfall:
        if record["complete_month"]:
            month_number = int(record["month"].split("-")[1])
            if month_number not in monthly_totals:
                monthly_totals[month_number] = []
            monthly_totals[month_number].append(
                record["rainfall_mm"]
            )

    average_rainfall_by_month = []

    for month_number in range(1, 13):
        totals = monthly_totals.get(month_number, [])

        average_rainfall_by_month.append({
            "month": MONTH_NAMES[month_number],
            "average_rainfall_mm": (
                round(sum(totals) / len(totals), 1)
                if totals else None
            ),
            "years_of_data": len(totals),
        })

    # Average daily maximum and minimum temperatures for
    # each calendar month, using complete months only.
    average_temperature_by_month = []
    for month_number in range(1, 13):
        max_values = []
        min_values = []
        for record in monthly_rainfall:
            if not record["complete_month"]:
                continue
            parts = record["month"].split("-")
            year = int(parts[0])
            month = int(parts[1])
            if month != month_number:
                continue
            expected_days = get_days_in_month(year, month)
            max_values_for_month = monthly_max_temps.get(
                record["month"], []
            )
            min_values_for_month = monthly_min_temps.get(
                record["month"], []
            )
            if (
                len(max_values_for_month) == expected_days
                and len(min_values_for_month) == expected_days
            ):
                max_values.append(
                    sum(max_values_for_month) / expected_days
                )
                min_values.append(
                    sum(min_values_for_month) / expected_days
                )
        average_temperature_by_month.append({
            "month": MONTH_NAMES[month_number],
            "average_daily_max_c": (
                round(sum(max_values) / len(max_values), 1)
                if max_values else None
            ),
            "average_daily_min_c": (
                round(sum(min_values) / len(min_values), 1)
                if min_values else None
            ),
            "years_of_data": len(max_values),
        })

    # Annual averages use complete calendar years only.
    annual_temperature = []
    for record in yearly_rainfall:
        if not record["complete_year"]:
            continue
        year = record["year"]
        expected_days = 366 if is_leap_year(year) else 365
        max_values = yearly_max_temps.get(year, [])
        min_values = yearly_min_temps.get(year, [])
        if (
            len(max_values) == expected_days
            and len(min_values) == expected_days
        ):
            annual_temperature.append({
                "year": year,
                "average_daily_max_c": round(
                    sum(max_values) / expected_days, 1
                ),
                "average_daily_min_c": round(
                    sum(min_values) / expected_days, 1
                ),
                "days_of_data": expected_days,
            })

    # 7. Calculate the average annual rainfall using only
    # complete calendar years.
    complete_year_totals = [
        record["rainfall_mm"]
        for record in yearly_rainfall
        if record["complete_year"]
    ]

    average_annual_rainfall = (
        round(
            sum(complete_year_totals)
            / len(complete_year_totals),
            1,
        )
        if complete_year_totals else None
    )

    # 8. Return everything in one structured result.
    valid_rainfall = [
        value for value in rainfall_values
        if value is not None
    ]

    return {
        "coordinates": {
            "latitude": latitude,
            "longitude": longitude,
        },

        "elevation_m": elevation_m,

        "forecast_7_days": forecast["daily"],

        "historical_rainfall": {
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),

            "total_rainfall_mm": round(
                sum(valid_rainfall), 1
            ),

            "valid_days": len(valid_rainfall),

            "average_annual_rainfall_mm":
                average_annual_rainfall,

            "monthly_rainfall": monthly_rainfall,

            "yearly_rainfall": yearly_rainfall,

            "average_rainfall_by_month":
                average_rainfall_by_month,

            "average_temperature_by_month":
                average_temperature_by_month,

            "annual_temperature":
                annual_temperature,
        },

        "sources": {
            "forecast": "Open-Meteo Forecast API",
            "historical": "Open-Meteo Historical Weather API",
            "elevation": "Open-Meteo Elevation API",
        },
    }


if __name__ == "__main__":
    print("Fetching environmental data...")

    result = asyncio.run(
        get_environment(12.2958, 76.6394)
    )

    print("\n--- ENVIRONMENTAL DATA ---")
    print("Elevation:", result["elevation_m"], "m")

    rainfall = result["historical_rainfall"]

    print(
        "\nTotal rainfall over historical period:",
        rainfall["total_rainfall_mm"],
        "mm",
    )

    print(
        "Average annual rainfall:",
        rainfall["average_annual_rainfall_mm"],
        "mm",
    )

    print("\n--- AVERAGE RAINFALL BY MONTH ---")

    for item in rainfall["average_rainfall_by_month"]:
        print(
            item["month"],
            ":",
            item["average_rainfall_mm"],
            "mm",
            f'({item["years_of_data"]} complete months)',
        )

    print("\n--- AVERAGE TEMPERATURE BY MONTH ---")
    for item in result["historical_rainfall"][
        "average_temperature_by_month"
    ]:
        print(item)

    print("\n--- ANNUAL TEMPERATURE AVERAGES ---")
    for item in result["historical_rainfall"]["annual_temperature"]:
        print(item)

    print("\n--- YEARLY RAINFALL ---")

    for item in rainfall["yearly_rainfall"]:
        status = (
            "Complete year"
            if item["complete_year"]
            else "Partial year or missing data"
        )

        print(
            item["year"],
            ":",
            item["rainfall_mm"],
            "mm -",
            status,
        )
