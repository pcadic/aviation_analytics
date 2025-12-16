import os
import requests
from datetime import datetime
from supabase import create_client, Client

# =====================
# Configuration
# =====================
AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

AIRPORT_ICAO = "CYVR"  # Vancouver
AVIATIONSTACK_URL = "http://api.aviationstack.com/v1/flights"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# =====================
# Fetch Aviationstack
# =====================
def fetch_flights():
    params = {
        "access_key": AVIATIONSTACK_API_KEY,
        "limit": 100,
        "flight_status": "active"
    }
    response = requests.get(AVIATIONSTACK_URL, params=params, timeout=30)
    response.raise_for_status()
    return response.json().get("data", [])


# =====================
# Transform record
# =====================
def transform(record):
    dep = record.get("departure") or {}
    arr = record.get("arrival") or {}
    airline = record.get("airline") or {}
    flight = record.get("flight") or {}
    aircraft = record.get("aircraft") or {}

    if dep.get("icao") == AIRPORT_ICAO:
        movement_type = "departure"
    elif arr.get("icao") == AIRPORT_ICAO:
        movement_type = "arrival"
    else:
        return None  # on ignore les autres vols

    return {
        "airport_icao": AIRPORT_ICAO,
        "movement_type": movement_type,
        "flight_date": record.get("flight_date"),
        "flight_status": record.get("flight_status"),
        "airline_name": airline.get("name"),
        "flight_number": flight.get("number"),
        "flight_icao": flight.get("icao"),

        "dep_airport": dep.get("airport"),
        "dep_icao": dep.get("icao"),
        "dep_timezone": dep.get("timezone"),
        "dep_terminal": dep.get("terminal"),
        "dep_gate": dep.get("gate"),
        "dep_delay_minutes": dep.get("delay"),
        "dep_actual": dep.get("actual"),

        "arr_airport": arr.get("airport"),
        "arr_icao": arr.get("icao"),
        "arr_timezone": arr.get("timezone"),
        "arr_terminal": arr.get("terminal"),
        "arr_gate": arr.get("gate"),
        "arr_baggage": arr.get("baggage"),
        "arr_delay_minutes": arr.get("delay"),
        "arr_actual": arr.get("actual"),

        "aircraft_icao": aircraft.get("icao"),
        "aircraft_registration": aircraft.get("registration"),

        "source_provider": "aviationstack",
        "ingested_at": datetime.utcnow().isoformat()
    }


# =====================
# Insert into Supabase
# =====================
def insert_rows(rows):
    if not rows:
        print("Aucun vol à insérer.")
        return

    supabase.table("flights").upsert(
        rows,
        on_conflict="flight_date,flight_icao,movement_type"
    ).execute()

    print(f"{len(rows)} vols insérés / mis à jour.")


# =====================
# Main
# =====================
def main():
    print("→ Fetch Aviationstack")
    raw_flights = fetch_flights()

    print(f"→ {len(raw_flights)} vols reçus")

    transformed = []
    for r in raw_flights:
        row = transform(r)
        if row:
            transformed.append(row)

    print(f"→ {len(transformed)} vols liés à {AIRPORT_ICAO}")

    insert_rows(transformed)
    print("✓ Terminé")


if __name__ == "__main__":
    main()
