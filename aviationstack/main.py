import os
import requests
from datetime import datetime
from supabase import create_client

AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

AIRPORT_ICAO = "CYVR"
BASE_URL = "http://api.aviationstack.com/v1/flights"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_limit(data, label):
    if len(data) == 100:
        print(f"⚠️ ALERTE: {label} atteint la limite de 100 résultats")

def fetch_flights(params):
    params["access_key"] = AVIATIONSTACK_API_KEY
    params["limit"] = 100

    r = requests.get(BASE_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("data", [])


def transform(record, movement_type):
    dep = record.get("departure") or {}
    arr = record.get("arrival") or {}
    airline = record.get("airline") or {}
    flight = record.get("flight") or {}
    aircraft = record.get("aircraft") or {}

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


def upsert(rows):
    if rows:
        supabase.table("flights").upsert(
            rows,
            on_conflict="flight_date,flight_icao,movement_type"
        ).execute()


def main():
    all_rows = []

    # ARRIVÉES
    arrivals = fetch_flights({"arr_icao": AIRPORT_ICAO})
    check_limit(arrivals, "Arrivées")
    for r in arrivals:
        all_rows.append(transform(r, "arrival"))

    # DÉPARTS
    departures = fetch_flights({"dep_icao": AIRPORT_ICAO})
    check_limit(departures, "Départs")
    for r in departures:
        all_rows.append(transform(r, "departure"))

    print(f"{len(all_rows)} vols collectés pour {AIRPORT_ICAO}")
    upsert(all_rows)


if __name__ == "__main__":
    main()
