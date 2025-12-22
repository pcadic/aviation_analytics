import os
import time
import requests
from dateutil import parser
from supabase import create_client

# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# ------------------------------------------------------------------
# Utils
# ------------------------------------------------------------------

def round_to_hour(dt):
    return dt.replace(minute=0, second=0, microsecond=0)


def select_weather_time(phase, flight):
    """
    Priority order (UTC):
    actual > estimated > scheduled
    """
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


def open_meteo_hour_str(dt):
    # Open-Meteo format: YYYY-MM-DDTHH:00
    return dt.strftime("%Y-%m-%dT%H:00")


def derive_features(raw):
    is_rain = raw["precipitation"] > 0.2
    is_fog = raw["visibility"] is not None and raw["visibility"] < 1000
    is_icing = raw["temperature"] <= 0 and raw["precipitation"] > 0
    is_strong_wind = raw["wind_speed"] > 30  # km/h

    return {
        "is_rain": is_rain,
        "is_fog": is_fog,
        "is_icing": is_icing,
        "is_strong_wind": is_strong_wind,
        "severity": int(is_rain) + int(is_fog) + int(is_icing) + int(is_strong_wind),
    }


def fetch_weather(lat, lon, date, retries=3, timeout=15):
    """
    Robust Open-Meteo call with retry + backoff
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,visibility,precipitation,windspeed_10m",
        "start_date": date,
        "end_date": date,
        "timezone": "UTC",
    }

    for attempt in range(1, retries + 1):
        try:
            r = requests.get(
                OPEN_METEO_URL,
                params=params,
                timeout=timeout,
            )
            r.raise_for_status()
            return r.json()

        except requests.exceptions.RequestException as e:
            print(
                f"[Open-Meteo] Attempt {attempt}/{retries} failed "
                f"(lat={lat}, lon={lon}, date={date}) → {e}"
            )

            if attempt < retries:
                time.sleep(3 * attempt)
            else:
                print("[Open-Meteo] Giving up for this request")
                return None


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():

    # --------------------------------------------------------------
    # 1️⃣ Flights without weather
    # --------------------------------------------------------------

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

    # --------------------------------------------------------------
    # 2️⃣ Airports (lat / lon)
    # --------------------------------------------------------------

    airports = supabase.table("airports_referencess") \
        .select("icao, latitude, longitude") \
        .execute().data

    airport_map = {a["icao"]: a for a in airports}

    # --------------------------------------------------------------
    # 3️⃣ Build unique weather requests
    # --------------------------------------------------------------

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
                    "data": None,
                }

    print(f"Unique météo calls: {len(weather_cache)}")

    # --------------------------------------------------------------
    # 4️⃣ Call Open-Meteo (batch, robust)
    # --------------------------------------------------------------

    for key, w in weather_cache.items():
        date = w["dt"].date().isoformat()
        data = fetch_weather(w["lat"], w["lon"], date)

        if not data:
            continue

        hour_str = open_meteo_hour_str(w["dt"])
        if hour_str not in data["hourly"]["time"]:
            continue

        idx = data["hourly"]["time"].index(hour_str)

        raw = {
            "temperature": data["hourly"]["temperature_2m"][idx],
            "visibility": data["hourly"]["visibility"][idx],
            "precipitation": data["hourly"]["precipitation"][idx],
            "wind_speed": data["hourly"]["windspeed_10m"][idx],
        }

        features = derive_features(raw)
        w["data"] = {**raw, **features}

        # Be gentle with free API
        time.sleep(0.5)

    # --------------------------------------------------------------
    # 5️⃣ Update flights
    # --------------------------------------------------------------

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

            p = "dep" if phase == "DEP" else "arr"
            d = w["data"]

            updates.update({
                f"{p}_temperature": d["temperature"],
                f"{p}_visibility": d["visibility"],
                f"{p}_precipitation": d["precipitation"],
                f"{p}_wind_speed": d["wind_speed"],

                f"{p}_is_rain": d["is_rain"],
                f"{p}_is_fog": d["is_fog"],
                f"{p}_is_icing": d["is_icing"],
                f"{p}_is_strong_wind": d["is_strong_wind"],
                f"{p}_weather_severity": d["severity"],
            })

        if updates:
            supabase.table("flights_airlabs") \
                .update(updates) \
                .eq("flight_icao", f["flight_icao"]) \
                .eq("dep_time", f["dep_time"]) \
                .execute()

    print("Weather enrichment completed successfully")


if __name__ == "__main__":
    main()
