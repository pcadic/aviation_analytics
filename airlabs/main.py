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
# API helpers
# ======================================================
def call_airlabs(url, params):
    params["api_key"] = AIRLABS_API_KEY
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("response", [])


def fetch_realtime(movement):
    if movement == "arrival":
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


# ======================================================
# Transformation
# ======================================================
def transform(rt, info):
    info = info or {}

    dep = info.get("dep") or {}
    arr = info.get("arr") or {}
    airline = info.get("airline") or {}
    aircraft = info.get("aircraft") or {}

    return {
        # Vol
        "flight_icao": rt.get("flight_icao"),
        "flight_number": rt.get("flight_number"),
        "airline_icao": rt.get("airline_icao"),
        "status": rt.get("status"),

        # Compagnie
        "airline_name": airline.get("name"),

        # Départ
        "dep_icao": rt.get("dep_icao"),
        "dep_terminal": dep.get("terminal"),
        "dep_gate": dep.get("gate"),
        "dep_time": dep.get("scheduled"),
        "dep_estimated": dep.get("estimated"),
        "dep_actual": dep.get("actual"),
        "dep_name": dep.get("airport"),
        "dep_city": dep.get("city"),
        "dep_country": dep.get("country"),
        "dep_delayed": dep.get("delay"),

        # Arrivée
        "arr_icao": rt.get("arr_icao"),
        "arr_terminal": arr.get("terminal"),
        "arr_gate": arr.get("gate"),
        "arr_baggage": arr.get("baggage"),
        "arr_time": arr.get("scheduled"),
        "arr_estimated": arr.get("estimated"),
        "arr_actual": arr.get("actual"),
        "arr_name": arr.get("airport"),
        "arr_city": arr.get("city"),
        "arr_country": arr.get("country"),
        "arr_delayed": arr.get("delay"),

        # Avion
        "reg_number": rt.get("reg_number"),
        "aircraft_icao": rt.get("aircraft_icao"),
        "model": aircraft.get("model"),
        "manufacturer": aircraft.get("manufacturer"),
        "type": aircraft.get("type"),
        "age": aircraft.get("age"),

        # Vol technique
        "duration": info.get("duration"),

        # Meta
        "source_provider": "airlabs",
        "ingested_at": datetime.now(timezone.utc).isoformat()
    }


# ======================================================
# Main
# ======================================================
def main():
    rows = []

    for movement in ["arrival", "departure"]:
        flights = fetch_realtime(movement)
        print(f"{movement.upper()} : {len(flights)} vols")

        for f in flights:
            flight_icao = f.get("flight_icao")
            if not flight_icao:
                continue

            info = fetch_flight_info(flight_icao)
            rows.append(transform(f, info))

    if rows:
        supabase.table("flights_airlabs").upsert(
            rows,
            on_conflict="flight_icao,dep_time"
        ).execute()

    print(f"✓ {len(rows)} vols AirLabs insérés / mis à jour")


if __name__ == "__main__":
    main()
