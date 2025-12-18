import os
import requests
from datetime import datetime, timezone
from supabase import create_client

# ==============================
# Config
# ==============================
AIRLABS_API_KEY = os.getenv("AIRLABS_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

AIRPORT_ICAO = "CYVR"

REALTIME_URL = "https://airlabs.co/api/v9/flights"
FLIGHT_INFO_URL = "https://airlabs.co/api/v9/flight"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def call_airlabs(url, params):
    params["api_key"] = AIRLABS_API_KEY
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("response", [])


def fetch_realtime(movement_type):
    if movement_type == "arrival":
        return call_airlabs(REALTIME_URL, {"arr_icao": AIRPORT_ICAO})
    return call_airlabs(REALTIME_URL, {"dep_icao": AIRPORT_ICAO})


def fetch_flight_info(flight_icao):
    r = requests.get(
        FLIGHT_INFO_URL,
        params={"api_key": AIRLABS_API_KEY, "flight_icao": flight_icao},
        timeout=30
    )
    r.raise_for_status()
    return r.json().get("response")


def transform(realtime, info, movement_type):
    info = info or {}
    dep = info.get("dep") or {}
    arr = info.get("arr") or {}
    airline = info.get("airline") or {}
    aircraft = info.get("aircraft") or {}

    return {
        # Identité
        "flight_date": datetime.now(timezone.utc).date().isoformat(),
        "flight_status": realtime.get("status"),

        # Vol
        "flight_number": realtime.get("flight_number"),
        "flight_icao": realtime.get("flight_icao"),
        "movement_type": movement_type,

        # Compagnie
        "airline_name": airline.get("name"),
        "airline_icao": airline.get("icao"),

        # Départ
        "dep_airport": dep.get("airport") or realtime.get("dep_airport"),
        "dep_icao": realtime.get("dep_icao"),
        "dep_timezone": dep.get("timezone"),

        "dep_terminal": dep.get("terminal"),
        "dep_gate": dep.get("gate"),

        "dep_scheduled": dep.get("scheduled"),
        "dep_estimated": dep.get("estimated"),
        "dep_actual": dep.get("actual"),
        "dep_delay_minutes": dep.get("delay"),

        # Arrivée
        "arr_airport": arr.get("airport") or realtime.get("arr_airport"),
        "arr_icao": realtime.get("arr_icao"),
        "arr_timezone": arr.get("timezone"),

        "arr_terminal": arr.get("terminal"),
        "arr_gate": arr.get("gate"),
        "arr_baggage": arr.get("baggage"),

        "arr_scheduled": arr.get("scheduled"),
        "arr_estimated": arr.get("estimated"),
        "arr_actual": arr.get("actual"),
        "arr_delay_minutes": arr.get("delay"),

        # Technique
        "flight_duration_minutes": info.get("duration"),

        # Avion
        "aircraft_icao": aircraft.get("icao"),
        "aircraft_registration": aircraft.get("registration"),

        # Meta
        "source_provider": "airlabs",
        "ingested_at": datetime.now(timezone.utc).isoformat()
    }


def main():
    rows = []

    for movement_type in ["arrival", "departure"]:
        realtime_flights = fetch_realtime(movement_type)
        print(f"{movement_type.upper()} : {len(realtime_flights)} vols")

        for f in realtime_flights:
            flight_icao = f.get("flight_icao")
            if not flight_icao:
                continue

            info = fetch_flight_info(flight_icao)
            row = transform(f, info, movement_type)
            rows.append(row)

    if rows:
        supabase.table("flights_airlabs").upsert(
            rows,
            on_conflict="flight_date,flight_icao,movement_type"
        ).execute()

    print(f"✓ {len(rows)} vols AirLabs insérés / mis à jour")


if __name__ == "__main__":
    main()
