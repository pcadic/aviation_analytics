import os
import requests
from datetime import datetime
from supabase import create_client

# =====================
# Config
# =====================
AIRLABS_API_KEY = os.getenv("AIRLABS_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

AIRPORT_ICAO = "CYVR"

REALTIME_URL = "https://airlabs.co/api/v9/flights"
FLIGHT_INFO_URL = "https://airlabs.co/api/v9/flight"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# =====================
# Helpers
# =====================
def call_api(url, params):
    params["api_key"] = AIRLABS_API_KEY
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("response", [])


def fetch_realtime(arr_or_dep):
    if arr_or_dep == "arrival":
        return call_api(REALTIME_URL, {"arr_icao": AIRPORT_ICAO})
    else:
        return call_api(REALTIME_URL, {"dep_icao": AIRPORT_ICAO})


def fetch_flight_info(flight_icao):
    data = call_api(FLIGHT_INFO_URL, {"flight_icao": flight_icao})
    return data[0] if data else None


def transform(realtime, info, movement_type):
    dep = info.get("dep") or {}
    arr = info.get("arr") or {}
    airline = info.get("airline") or {}
    aircraft = info.get("aircraft") or {}

    scheduled = dep.get("scheduled") if movement_type == "departure" else arr.get("scheduled")
    actual = dep.get("actual") if movement_type == "departure" else arr.get("actual")

    return {
        "flight_date": datetime.utcnow().date().isoformat(),
        "flight_icao": realtime.get("flight_icao"),
        "flight_number": realtime.get("flight_number"),
        "airline_name": airline.get("name"),

        "movement_type": movement_type,
        "dep_icao": dep.get("icao"),
        "arr_icao": arr.get("icao"),

        "scheduled_time": scheduled,
        "actual_time": actual,
        "reference_time": actual or scheduled,

        "flight_status": realtime.get("status"),

        "aircraft_icao": aircraft.get("icao"),
        "aircraft_registration": aircraft.get("registration"),

        "source_provider": "airlabs",
        "ingested_at": datetime.utcnow().isoformat()
    }


# =====================
# Main
# =====================
def main():
    rows = []

    for movement in ["arrival", "departure"]:
        realtime_flights = fetch_realtime(movement)
        print(f"{movement}: {len(realtime_flights)} vols")

        for f in realtime_flights:
            flight_icao = f.get("flight_icao")
            if not flight_icao:
                continue

            info = fetch_flight_info(flight_icao)
            if not info:
                continue

            rows.append(transform(f, info, movement))

    if rows:
        supabase.table("flights_airlabs").upsert(
            rows,
            on_conflict="flight_date,flight_icao,movement_type"
        ).execute()

    print(f"{len(rows)} vols AirLabs insérés")


if __name__ == "__main__":
    main()
