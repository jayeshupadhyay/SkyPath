from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from zoneinfo import ZoneInfo

DATA_PATH = os.getenv("FLIGHTS_DATA_PATH", "/data/flights.json")

app = FastAPI(title="SkyPath API", version="0.1.0")

# CORS (keep as-is)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Normalized in-memory model ----------

@dataclass(frozen=True)
class Airport:
    code: str
    country: str
    timezone: str

@dataclass(frozen=True)
class FlightN:
    flightNumber: str
    airline: str
    origin: str
    destination: str
    departure_local: datetime
    arrival_local: datetime
    departure_utc: datetime
    arrival_utc: datetime
    price: float
    aircraft: str

AIRPORTS_BY_CODE: dict[str, Airport] = {}
FLIGHTS: list[FlightN] = []
FLIGHTS_BY_ORIGIN: dict[str, list[FlightN]] = {}
NORMALIZATION_STATS: dict[str, int] = {}

MIN_LAYOVER_DOMESTIC_MIN = 45
MIN_LAYOVER_INTERNATIONAL_MIN = 90
MAX_LAYOVER_MIN = 6 * 60
MAX_STOPS = 2

def _parse_price(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_local_iso(dt_str: str) -> Optional[datetime]:
    # dataset uses ISO like "2024-03-15T08:30:00" (no tz offset)
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        return None


def _attach_tz(local_naive: datetime, tz_name: str) -> Optional[datetime]:
    try:
        return local_naive.replace(tzinfo=ZoneInfo(tz_name))
    except Exception:
        return None


@app.on_event("startup")
def load_data() -> None:
    global AIRPORTS_BY_CODE, FLIGHTS, FLIGHTS_BY_ORIGIN, NORMALIZATION_STATS

    # 1) Load raw JSON
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError:
        raise RuntimeError(f"flights.json not found at {DATA_PATH}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in flights.json: {e}")

    airports_raw = raw.get("airports", [])
    flights_raw = raw.get("flights", [])

    # 2) Build airports map
    airports_by_code: dict[str, Airport] = {}
    for a in airports_raw:
        code = str(a.get("code", "")).upper().strip()
        if not code:
            continue
        airports_by_code[code] = Airport(
            code=code,
            country=str(a.get("country", "")).upper().strip(),
            timezone=str(a.get("timezone", "")).strip(),
        )

    # 3) Normalize flights
    stats: dict[str, int] = {
        "raw_airports": len(airports_raw),
        "raw_flights": len(flights_raw),
        "kept_flights": 0,
        "dropped_invalid_airport": 0,
        "dropped_bad_price": 0,
        "dropped_bad_datetime": 0,
        "dropped_bad_timezone": 0,
        "dropped_non_positive_duration": 0,
    }

    normalized: list[FlightN] = []

    for f in flights_raw:
        origin = str(f.get("origin", "")).upper().strip()
        dest = str(f.get("destination", "")).upper().strip()

        o_air = airports_by_code.get(origin)
        d_air = airports_by_code.get(dest)
        if not o_air or not d_air:
            stats["dropped_invalid_airport"] += 1
            continue

        price = _parse_price(f.get("price"))
        if price is None:
            stats["dropped_bad_price"] += 1
            continue

        dep_naive = _parse_local_iso(str(f.get("departureTime", "")).strip())
        arr_naive = _parse_local_iso(str(f.get("arrivalTime", "")).strip())
        if dep_naive is None or arr_naive is None:
            stats["dropped_bad_datetime"] += 1
            continue

        dep_local = _attach_tz(dep_naive, o_air.timezone)
        arr_local = _attach_tz(arr_naive, d_air.timezone)
        if dep_local is None or arr_local is None:
            stats["dropped_bad_timezone"] += 1
            continue

        dep_utc = dep_local.astimezone(ZoneInfo("UTC"))
        arr_utc = arr_local.astimezone(ZoneInfo("UTC"))

        if arr_utc <= dep_utc:
            stats["dropped_non_positive_duration"] += 1
            continue

        normalized.append(
            FlightN(
                flightNumber=str(f.get("flightNumber", "")).strip(),
                airline=str(f.get("airline", "")).strip(),
                origin=origin,
                destination=dest,
                departure_local=dep_local,
                arrival_local=arr_local,
                departure_utc=dep_utc,
                arrival_utc=arr_utc,
                price=price,
                aircraft=str(f.get("aircraft", "")).strip(),
            )
        )
        stats["kept_flights"] += 1

    # 4) Build index: flights by origin, sorted by departure_utc
    flights_by_origin = defaultdict(list)
    for fl in normalized:
        flights_by_origin[fl.origin].append(fl)

    for o in flights_by_origin:
        flights_by_origin[o].sort(key=lambda x: x.departure_utc)

    # 5) Publish normalized stores
    AIRPORTS_BY_CODE = airports_by_code
    FLIGHTS = normalized
    FLIGHTS_BY_ORIGIN = dict(flights_by_origin)
    NORMALIZATION_STATS = stats

def _minutes_between(a: datetime, b: datetime) -> int:
    return int((b - a).total_seconds() // 60)

def _is_domestic_connection(airport_a: Airport, airport_b: Airport) -> bool:
    return airport_a.country == airport_b.country

def _min_layover_minutes(arrival_airport_code: str, departure_airport_code: str) -> int:
    a = AIRPORTS_BY_CODE[arrival_airport_code]
    b = AIRPORTS_BY_CODE[departure_airport_code]
    return MIN_LAYOVER_DOMESTIC_MIN if _is_domestic_connection(a, b) else MIN_LAYOVER_INTERNATIONAL_MIN

def _valid_layover(prev_flight: FlightN, next_flight: FlightN) -> Optional[int]:
    # Must connect at same airport
    if prev_flight.destination != next_flight.origin:
        return None

    layover_min = _minutes_between(prev_flight.arrival_utc, next_flight.departure_utc)
    if layover_min < 0:
        return None

    min_required = _min_layover_minutes(prev_flight.destination, next_flight.origin)
    if layover_min < min_required:
        return None
    if layover_min > MAX_LAYOVER_MIN:
        return None

    return layover_min

def _itinerary_to_dict(segments: list[FlightN], layovers: list[int]) -> dict[str, Any]:
    total_price = round(sum(s.price for s in segments), 2)
    total_duration_min = _minutes_between(segments[0].departure_utc, segments[-1].arrival_utc)

    return {
        "segments": [
            {
                "flightNumber": s.flightNumber,
                "airline": s.airline,
                "origin": s.origin,
                "destination": s.destination,
                "departureTimeLocal": s.departure_local.isoformat(),
                "arrivalTimeLocal": s.arrival_local.isoformat(),
                "price": s.price,
                "aircraft": s.aircraft,
            }
            for s in segments
        ],
        "layoversMinutes": layovers,  # length = len(segments)-1
        "totalDurationMinutes": total_duration_min,
        "totalPrice": total_price,
    }



@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "airports": len(AIRPORTS_BY_CODE),
        "flights": len(FLIGHTS),
        "stats": NORMALIZATION_STATS,
    }


@app.get("/search")
def search(
    origin: str = Query(..., min_length=3, max_length=3, description="IATA origin code"),
    destination: str = Query(..., min_length=3, max_length=3, description="IATA destination code"),
    date_str: str = Query(..., alias="date", description="YYYY-MM-DD"),
) -> List[Dict[str, Any]]:
    origin = origin.upper().strip()
    destination = destination.upper().strip()

    if origin == destination:
        return []

    if origin not in AIRPORTS_BY_CODE:
        raise HTTPException(status_code=400, detail=f"Invalid origin airport: {origin}")
    if destination not in AIRPORTS_BY_CODE:
        raise HTTPException(status_code=400, detail=f"Invalid destination airport: {destination}")

    try:
        search_date = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date. Use YYYY-MM-DD.")

    # --- 1) Get candidate first-leg flights departing on `search_date` in ORIGIN local time ---
    # Flights store departure_local with tzinfo of origin airport.
    first_legs = []
    for f in FLIGHTS_BY_ORIGIN.get(origin, []):
        if f.departure_local.date() == search_date:
            first_legs.append(f)

    # --- 2) Build itineraries up to 2 stops (max 3 segments) ---
    results: list[dict[str, Any]] = []

    # Direct
    for f1 in first_legs:
        if f1.destination == destination:
            results.append(_itinerary_to_dict([f1], []))

    # 1-stop
    for f1 in first_legs:
        if f1.destination == destination:
            continue

        for f2 in FLIGHTS_BY_ORIGIN.get(f1.destination, []):
            lay1 = _valid_layover(f1, f2)
            if lay1 is None:
                continue

            # Important: the onward flight should logically occur after arrival (already ensured)
            # and it can be next day (allowed by dataset)
            if f2.destination == destination:
                results.append(_itinerary_to_dict([f1, f2], [lay1]))

    # 2-stop
    for f1 in first_legs:
        if f1.destination == destination:
            continue

        for f2 in FLIGHTS_BY_ORIGIN.get(f1.destination, []):
            # example inside the loop for f2:
            if f2.departure_utc < f1.arrival_utc:
                continue
            if _minutes_between(f1.arrival_utc, f2.departure_utc) > MAX_LAYOVER_MIN:
                # since FLIGHTS_BY_ORIGIN is sorted by departure_utc, you can break here
                break

            lay1 = _valid_layover(f1, f2)
            if lay1 is None:
                continue

            # Avoid cycles like JFK->ORD->JFK->...
            if f2.destination == origin:
                continue

            for f3 in FLIGHTS_BY_ORIGIN.get(f2.destination, []):
                lay2 = _valid_layover(f2, f3)
                if lay2 is None:
                    continue

                if f3.destination == destination:
                    results.append(_itinerary_to_dict([f1, f2, f3], [lay1, lay2]))

    # --- 3) Sort by total travel time (shortest first) ---
    results.sort(key=lambda r: r["totalDurationMinutes"])
    return results
