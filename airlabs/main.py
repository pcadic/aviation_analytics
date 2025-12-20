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

    return {
        # =====================
        # Vol (Realtime)
        # =====================
        "flight_icao": rt.get("flight_icao"),
        "flight_number": rt.get("flight_number"),
        "airline_icao": rt.get("airline_icao"),
        "status": rt.get("status"),

        # =====================
        # Compagnie (Flight Info)
        # =====================
        "airline_name": info.get("airline_name"),

        # =====================
        # Départ
        # =====================
        "dep_icao": rt.get("dep_icao"),
        "dep_terminal": info.get("dep_terminal"),
        "dep_gate": info.get("dep_gate"),
        "dep_time": info.get("dep_time"),
        "dep_estimated": info.get("dep_estimated"),
        "dep_actual": info.get("dep_actual"),
        "dep_time_utc": info.get("dep_time_utc"),
        "dep_estimated_utc": info.get("dep_estimated_utc"),
        "dep_actual_utc": info.get("dep_actual_utc"),
        "dep_name": info.get("dep_name"),
        "dep_city": info.get("dep_city"),
        "dep_country": info.get("dep_country"),
        "dep_delayed": info.get("dep_delayed"),

        # =====================
        # Arrivée
        # =====================
        "arr_icao": rt.get("arr_icao"),
        "arr_terminal": info.get("arr_terminal"),
        "arr_gate": info.get("arr_gate"),
        "arr_baggage": info.get("arr_baggage"),
        "arr_time": info.get("arr_time"),
        "arr_estimated": info.get("arr_estimated"),
        "arr_actual": info.get("arr_actual"),
        "arr_time_utc": info.get("arr_time_utc"),
        "arr_estimated_utc": info.get("arr_estimated_utc"),
        "arr_actual_utc": info.get("arr_actual_utc"),
        "arr_name": info.get("arr_name"),
        "arr_city": info.get("arr_city"),
        "arr_country": info.get("arr_country"),
        "arr_delayed": info.get("arr_delayed"),

        # =====================
        # Avion
        # =====================
        "reg_number": rt.get("reg_number"),
        "aircraft_icao": rt.get("aircraft_icao"),
        "model": info.get("model"),
        "manufacturer": info.get("manufacturer"),
        "type": info.get("type"),
        "age": info.get("age"),

        # =====================
        # Vol technique
        # =====================
        "duration": info.get("duration"),

        # =====================
        # Meta
        # =====================
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
