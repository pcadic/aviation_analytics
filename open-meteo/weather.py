import os
import requests
from dateutil import parser
from datetime import datetime
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def round_to_hour(dt):
    return dt.replace(minute=0, second=0, microsecond=0)


def select_weather_time(dep_or_arr, flight):
    if dep_or_arr == "DEP":
        return (
            flight.get("dep_actual_utc")
            or flight.get("dep_estimated_utc")
            or flight.get("dep_time_utc")
        )
    else:
        return (
            flight.get("arr_actual_utc")
            or flight.get("arr_estimated_utc")
            or flight.get("arr_time_utc")
        )


def fetch_weather(lat, lon, date):
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,visibility,precipitation,windspeed_10m",
        "start_date": date,
        "end_date": date,
        "timezone": "UTC"
    }
    r = requests.get(OPEN_METEO_URL, params=params)
    r.raise_for_status()
    return r.json()


def main():

    # 1️⃣ Charger vols sans météo
    flights = supabase.table("flights_airlabs") \
        .select("id, dep_icao, arr_icao, dep_time_utc, dep_estimated_utc, dep_actual_utc, arr_time_utc, arr_estimated_utc, arr_actual_utc") \
        .is_("dep_temperature", None) \
        .execute().data

    if not flights:
        print("No flights to process")
        return

    # 2️⃣ Charger aéroports
    airports = supabase.table("airports") \
        .select("icao, latitude, longitude") \
        .execute().data

    airport_map = {a["icao"]: a for a in airports}

    # 3️⃣ Construire besoins météo dédupliqués
    weather_cache = {}

    for f in flights:
        for phase in ("DEP", "ARR"):
            icao = f["dep_icao"] if phase == "DEP" else f["arr_icao"]
            airport = airport_map.get(icao)

            if not airport:
                continue

            time_utc = select_weather_time(phase, f)
            if not time_utc:
                continue

            dt = round_to_hour(parser.isoparse(time_utc))
            key = (icao, dt)

            if key not in weather_cache:
                weather_cache[key] = {
                    "lat": airport["latitude"],
                    "lon": airport["longitude"],
                    "dt": dt,
                    "data": None
                }

    print(f"Appels météo uniques : {len(weather_cache)}")

    # 4️⃣ Appels Open-Meteo
    for key, w in weather_cache.items():
        date = w["dt"].date().isoformat()
        data = fetch_weather(w["lat"], w["lon"], date)

        hour_index = data["hourly"]["time"].index(w["dt"].isoformat())

        w["data"] = {
            "temperature": data["hourly"]["temperature_2m"][hour_index],
            "visibility": data["hourly"]["visibility"][hour_index],
            "precipitation": data["hourly"]["precipitation"][hour_index],
            "wind_speed": data["hourly"]["windspeed_10m"][hour_index],
        }

    # 5️⃣ Mise à jour vols
    for f in flights:
        updates = {}

        for phase in ("DEP", "ARR"):
            icao = f["dep_icao"] if phase == "DEP" else f["arr_icao"]
            time_utc = select_weather_time(phase, f)

            if not time_utc:
                continue

            dt = round_to_hour(parser.isoparse(time_utc))
            w = weather_cache.get((icao, dt))
            if not w or not w["data"]:
                continue

            prefix = "dep" if phase == "DEP" else "arr"
            updates.update({
                f"{prefix}_temperature": w["data"]["temperature"],
                f"{prefix}_visibility": w["data"]["visibility"],
                f"{prefix}_precipitation": w["data"]["precipitation"],
                f"{prefix}_wind_speed": w["data"]["wind_speed"],
            })

        if updates:
            supabase.table("flights_airlabs") \
                .update(updates) \
                .eq("id", f["id"]) \
                .execute()

    print("Météo ajoutée avec succès")


if __name__ == "__main__":
    main()
