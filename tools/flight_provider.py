"""
Optional flight data from the internet (free tier).

Uses Amadeus for Developers when AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET
are set. Free self-service tier: https://developers.amadeus.com/
If credentials are missing or the API fails, callers should fall back to mock data.
"""

import os
import re
from datetime import datetime, timedelta
from typing import Any, List, Optional

# Amadeus is optional
try:
    from amadeus import Client, ResponseError
    _AMADEUS_AVAILABLE = True
except ImportError:
    _AMADEUS_AVAILABLE = False


# Common IATA carrier codes -> display name
_CARRIER_NAMES = {
    "HA": "Hawaiian Airlines",
    "UA": "United Airlines",
    "AS": "Alaska Airlines",
    "AA": "American Airlines",
    "DL": "Delta Air Lines",
    "WN": "Southwest Airlines",
    "NK": "Spirit Airlines",
    "B6": "JetBlue",
    "F9": "Frontier Airlines",
}


def _parse_iso_duration(duration_str: str) -> float:
    """Parse ISO 8601 duration (e.g. PT5H30M) to hours."""
    if not duration_str:
        return 0.0
    # PT5H30M or PT2H
    hours = 0.0
    minutes = 0.0
    h = re.search(r"(\d+)H", duration_str)
    m = re.search(r"(\d+)M", duration_str)
    if h:
        hours = float(h.group(1))
    if m:
        minutes = float(m.group(1))
    return hours + minutes / 60.0


def _is_red_eye(iso_datetime_str: str) -> bool:
    """True if time is before 6am or 10pm or later (typical red-eye)."""
    try:
        dt = datetime.fromisoformat(iso_datetime_str.replace("Z", "+00:00"))
        hour = dt.hour
        return hour >= 22 or hour < 6
    except Exception:
        return False


def _format_time(iso_datetime_str: str) -> str:
    """Format ISO datetime to '10:30 AM'."""
    try:
        dt = datetime.fromisoformat(iso_datetime_str.replace("Z", "+00:00"))
        h = dt.hour % 12 or 12
        am_pm = "AM" if dt.hour < 12 else "PM"
        return f"{h}:{dt.minute:02d} {am_pm}"
    except Exception:
        return ""


def fetch_flights_amadeus(
    origin: str,
    destination: str,
    departure_start: str,
    departure_end: str,
    trip_duration_days: int = 7,
    max_departure_dates: int = 5,
) -> Optional[List[dict]]:
    """
    Fetch real flight options from Amadeus (free tier).

    Returns a list of options in the same format as the mock in mcp_server.search_flights,
    or None if credentials are missing, Amadeus is not installed, or the API fails.

    Set environment variables:
      AMADEUS_CLIENT_ID
      AMADEUS_CLIENT_SECRET

    Get free keys: https://developers.amadeus.com/register
    """
    if not _AMADEUS_AVAILABLE:
        return None
    client_id = os.getenv("AMADEUS_CLIENT_ID")
    client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None

    start = datetime.fromisoformat(departure_start).date()
    end = datetime.fromisoformat(departure_end).date()
    # Sample a few departure dates to stay within free tier
    step = max(1, (end - start).days // max_departure_dates) if (end - start).days >= max_departure_dates else 1
    departure_dates = []
    d = start
    while d <= end and len(departure_dates) < max_departure_dates:
        departure_dates.append(d.isoformat())
        d += timedelta(days=step)

    options = []
    try:
        amadeus = Client(client_id=client_id, client_secret=client_secret)
    except Exception:
        return None

    for dep_date in departure_dates:
        return_date_obj = datetime.fromisoformat(dep_date).date() + timedelta(days=trip_duration_days)
        return_date = return_date_obj.isoformat()
        try:
            response = amadeus.shopping.flight_offers_search.get(
                originLocationCode=origin,
                destinationLocationCode=destination,
                departureDate=dep_date,
                returnDate=return_date,
                adults="1",
            )
        except ResponseError:
            continue
        except Exception:
            continue

        data = getattr(response, "data", None) or getattr(response, "result", {}).get("data", [])
        if not data:
            continue

        for offer in data[:3]:  # At most 3 options per date to limit size
            try:
                itineraries = offer.get("itineraries", [])
                if not itineraries:
                    continue
                outbound = itineraries[0]
                out_segments = outbound.get("segments", [])
                if not out_segments:
                    continue

                first_dep = out_segments[0].get("departure", {}).get("at", "")
                first_dep_date = first_dep[:10] if len(first_dep) >= 10 else dep_date
                departure_time = _format_time(first_dep) or "—"
                duration_str = outbound.get("duration", "") or ""
                total_duration_hours = _parse_iso_duration(duration_str)
                if total_duration_hours <= 0 and out_segments:
                    for seg in out_segments:
                        total_duration_hours += _parse_iso_duration(seg.get("duration", ""))

                return_dep_time = ""
                return_date_str = return_date
                if len(itineraries) > 1:
                    ret = itineraries[1]
                    ret_segments = ret.get("segments", [])
                    if ret_segments:
                        return_dep_time = ret_segments[0].get("departure", {}).get("at", "")
                        return_date_str = return_dep_time[:10] if len(return_dep_time) >= 10 else return_date

                price_data = offer.get("price", {}) or {}
                total = price_data.get("total", "0")
                try:
                    price = int(float(total))
                except (TypeError, ValueError):
                    price = 0

                carrier_code = (out_segments[0].get("carrierCode") or out_segments[0].get("operating", {}).get("carrierCode") or "").strip()
                airline = _CARRIER_NAMES.get(carrier_code.upper(), carrier_code or "Airline")

                stops_out = max(0, len(out_segments) - 1)
                stops_ret = max(0, len(itineraries[1].get("segments", [])) - 1) if len(itineraries) > 1 else 0
                stops = stops_out + stops_ret

                options.append({
                    "departure_date": first_dep_date,
                    "return_date": return_date_str,
                    "departure_time": departure_time,
                    "return_time": _format_time(return_dep_time) if return_dep_time else "—",
                    "price": price,
                    "airline": airline,
                    "stops": stops,
                    "duration_hours": round(total_duration_hours, 1),
                    "is_red_eye_outbound": _is_red_eye(first_dep),
                    "is_red_eye_return": _is_red_eye(return_dep_time) if return_dep_time else False,
                    "departure_day_of_week": datetime.fromisoformat(first_dep_date).strftime("%A"),
                })
            except (KeyError, TypeError, IndexError):
                continue

    return options if options else None
