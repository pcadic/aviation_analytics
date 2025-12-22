import os
import requests
from dateutil import parser
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


# -----------------------
# Utils
# -----------------------

def round_to_hour(dt):
    return dt.replace(minute=0, second=0, microsecond=0)


def select_weather_time(phase, flight):
    if phase == "DEP":
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


def derive_features(w):
    is_rain = w["precipitation"] > 0.2
    is_fog = w["visibility"] is not None and w["visibility"] < 1000
    is_icing = w["temperature"] <= 0 and w["precipitation"] > 0
    is_strong_wind = w["wind_speed"] > 30  # km/h

    return {
        "is_rain": is_rain,
        "is_fog": is_fog,
        "is_icing": is_icing,
        "is_strong_wind": is_strong_wind,
        "severity": sum([is_rain, is_fog, is_icing, is_strong_wind])
    }


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


# -----------------------
# Main
# -----------------------

def main():

    # 1️⃣ Flights sans météo
    flights = supabase.table("flights_airlabs") \
        .select("""
            flight_icao,
            dep_time,
            dep_icao, arr_icao,
            dep_time_utc, dep_estimated_utc, dep_actual_utc,
            arr_time_utc, arr_estimated_utc, arr_actual_utc
        """) \
        .is_("dep_temperature", None) \
        .execute().data


    if not flights:
        print("No flights to enrich")
        return

    # 2️⃣ Airports
    airports = supabase.table("airports") \
        .select("icao, latitude, longitude") \
        .execute().data

    airport_map = {a["icao"]: a for a in airports}

    # 3️⃣ Déduplication des besoins météo
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

    print(f"Unique météo calls: {len(weather_cache)}")

    # 4️⃣ Appels Open-Meteo
    for key, w in weather_cache.items():
        date = w["dt"].date().isoformat()
        data = fetch_weather(w["lat"], w["lon"], date)

        hour_idx = data["hourly"]["time"].index(w["dt"].isoformat())

        raw = {
            "temperature": data["hourly"]["temperature_2m"][hour_idx],
            "visibility": data["hourly"]["visibility"][hour_idx],
            "precipitation": data["hourly"]["precipitation"][hour_idx],
            "wind_speed": data["hourly"]["windspeed_10m"][hour_idx],
        }

        features = derive_features(raw)

        w["data"] = {**raw, **features}

    # 5️⃣ Mise à jour des vols
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
            d = w["data"]

            updates.update({
                f"{prefix}_temperature": d["temperature"],
                f"{prefix}_visibility": d["visibility"],
                f"{prefix}_precipitation": d["precipitation"],
                f"{prefix}_wind_speed": d["wind_speed"],

                f"{prefix}_is_rain": d["is_rain"],
                f"{prefix}_is_fog": d["is_fog"],
                f"{prefix}_is_icing": d["is_icing"],
                f"{prefix}_is_strong_wind": d["is_strong_wind"],
                f"{prefix}_weather_severity": d["severity"],
            })

        if updates:
            supabase.table("flights_airlabs") \
                .update(updates) \
                .eq("flight_icao", f["flight_icao"]) \
                .eq("dep_time", f["dep_time"]) \
                .execute()

    print("Weather + features successfully added")


if __name__ == "__main__":
    main()
