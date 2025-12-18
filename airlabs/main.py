import os
import requests
from datetime import datetime, timezone
from supabase import create_client

# ======================================================
# Configuration
# ======================================================
AIRLABS_API_KEY = os.getenv("AIRLABS_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

AIRPORT_ICAO = "CYVR"

REALTIME_URL = "https://airlabs.co/api/v9/flights"
FLIGHT_INFO_URL = "https://airlabs.co/api/v9/flight"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ======================================================
# Helpers
# ======================================================
def call_airlabs(url, params):
    params["api_key"] = AIRLABS_API_KEY
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("response", [])


def fetch_realtime(movement_type):
    if movement_type == "arrival":
        return call_airlabs(REALTIME_URL, {"arr_icao": AIRPORT_ICAO})
    else:
        return call_airlabs(REALTIME_URL, {"dep_icao": AIRPORT_ICAO})


def fetch_flight_info(flight_icao):
    response = requests.get(
        FLIGHT_INFO_URL,
        params={
            "api_key": AIRLABS_API_KEY,
            "flight_icao": flight_icao
        },
        timeout=30
    )
    response.raise_for_status()

    data = response.json()

    if "response" not in data:
        return None

    return data["response"]


def parse_time(value):
    if not value:
        return None
    return value  # AirLabs renvoie déjà de l’ISO8601


# ======================================================
# Transformation vers le schéma Airlabs
# ======================================================
def transform(realtime, info, movement_type):
    info = info or {}

    dep_info = info.get("dep") or {}
    arr_info = info.get("arr") or {}
    airline_info = info.get("airline") or {}
    aircraft_info = info.get("aircraft") or {}

    return {
        # -------------------------
        # Flight core
        # -------------------------
        "flight_date": datetime.now(timezone.utc).date().isoformat(),
        "flight_status": realtime.get("status"),

        "airline_name": (
            airline_info.get("name")
            or realtime.get("airline_name")
        ),

        "flight_number": realtime.get("flight_number"),
        "flight_icao": realtime.get("flight_icao"),

        "movement_type": movement_type,

        # -------------------------
        # Departure (REALTIME FIRST)
        # -------------------------
        "dep_airport": (
            dep_info.get("airport")
            or realtime.get("dep_airport")
        ),
        "dep_icao": realtime.get("dep_icao"),
        "dep_timezone": dep_info.get("timezone"),
        "dep_terminal": dep_info.get("terminal"),
        "dep_gate": dep_info.get("gate"),
        "dep_delay_minutes": dep_info.get("delay"),
        "dep_actual": dep_info.get("actual"),

        # -------------------------
        # Arrival (REALTIME FIRST)
        # -------------------------
        "arr_airport": (
            arr_info.get("airport")
            or realtime.get("arr_airport")
        ),
        "arr_icao": realtime.get("arr_icao"),
        "arr_timezone": arr_info.get("timezone"),
        "arr_terminal": arr_info.get("terminal"),
        "arr_gate": arr_info.get("gate"),
        "arr_baggage": arr_info.get("baggage"),
        "arr_delay_minutes": arr_info.get("delay"),
        "arr_actual": arr_info.get("actual"),

        # -------------------------
        # Aircraft (INFO ONLY)
        # -------------------------
        "aircraft_icao": aircraft_info.get("icao"),
        "aircraft_registration": aircraft_info.get("registration"),

        # -------------------------
        # Meta
        # -------------------------
        "source_provider": "airlabs",
        "ingested_at": datetime.now(timezone.utc).isoformat()
    }



# ======================================================
# Main
# ======================================================
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
            if not info:
                continue

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
