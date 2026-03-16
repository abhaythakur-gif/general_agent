"""
travel_tools.py
---------------
Flight and hotel search tools powered by SerpAPI's Google Flights
and Google Hotels engines.

Tool functions (registered in tool_registry.py):
  search_flights        — search flights by city name and date (any format)
  search_hotels         — hotel search by destination city only
  search_tourist_places — top tourist attractions by destination city only

City name → IATA mapping covers all major Indian airports.
Date accepts any common format: "15 April 2026", "15/04/2026", "2026-04-15", etc.
"""

import re
import requests
from datetime import datetime
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

SERPAPI_BASE = "https://serpapi.com/search"
API_KEY = settings.SERPAPI_KEY

# ─── Indian city → IATA airport code ─────────────────────────────────────────
INDIA_AIRPORTS: dict = {
    # Metro cities
    "mumbai":       "BOM",
    "delhi":        "DEL",
    "new delhi":    "DEL",
    "bangalore":    "BLR",
    "bengaluru":    "BLR",
    "hyderabad":    "HYD",
    "chennai":      "MAA",
    "madras":       "MAA",
    "kolkata":      "CCU",
    "calcutta":     "CCU",
    # Major cities
    "pune":         "PNQ",
    "ahmedabad":    "AMD",
    "jaipur":       "JAI",
    "kochi":        "COK",
    "cochin":       "COK",
    "goa":          "GOI",
    "panaji":       "GOI",
    "lucknow":      "LKO",
    "bhopal":       "BHO",
    "indore":       "IDR",
    "nagpur":       "NAG",
    "surat":        "STV",
    "vadodara":     "BDQ",
    "amritsar":     "ATQ",
    "chandigarh":   "IXC",
    "patna":        "PAT",
    "ranchi":       "IXR",
    "bhubaneswar":  "BBI",
    "visakhapatnam": "VTZ",
    "vizag":        "VTZ",
    "coimbatore":   "CJB",
    "madurai":      "IXM",
    "tiruchirappalli": "TRZ",
    "trichy":       "TRZ",
    "mangalore":    "IXE",
    "mangaluru":    "IXE",
    "thiruvananthapuram": "TRV",
    "trivandrum":   "TRV",
    "kozhikode":    "CCJ",
    "calicut":      "CCJ",
    "guwahati":     "GAU",
    "imphal":       "IMF",
    "agartala":     "IXA",
    "dibrugarh":    "DIB",
    "jorhat":       "JRH",
    "silchar":      "IXS",
    "varanasi":     "VNS",
    "dehradun":     "DED",
    "jammu":        "IXJ",
    "srinagar":     "SXR",
    "leh":          "IXL",
    "udaipur":      "UDR",
    "jodhpur":      "JDH",
    "aurangabad":   "IXU",
    "raipur":       "RPR",
    "hubli":        "HBX",
    "belgaum":      "IXG",
    "port blair":   "IXZ",
}

# Date format patterns to try when parsing user-supplied dates
_DATE_FORMATS = [
    "%Y-%m-%d",      # 2026-04-15
    "%d-%m-%Y",      # 15-04-2026
    "%d/%m/%Y",      # 15/04/2026
    "%m/%d/%Y",      # 04/15/2026
    "%d %B %Y",      # 15 April 2026
    "%d %b %Y",      # 15 Apr 2026
    "%B %d %Y",      # April 15 2026
    "%b %d %Y",      # Apr 15 2026
    "%B %d, %Y",     # April 15, 2026
    "%b %d, %Y",     # Apr 15, 2026
    "%d.%m.%Y",      # 15.04.2026
]


def _resolve_airport(city: str) -> str:
    """Convert a city name to IATA code. Falls back to the input uppercased."""
    key = city.strip().lower()
    code = INDIA_AIRPORTS.get(key)
    if code:
        return code
    # Try partial match — e.g. "new delhi airport" still finds DEL
    for city_key, iata in INDIA_AIRPORTS.items():
        if city_key in key or key in city_key:
            return iata
    # Assume user already passed an IATA code
    return city.strip().upper()


def _parse_date(date_str: str) -> str:
    """Parse any common date format and return YYYY-MM-DD. Raises ValueError if unparseable."""
    date_str = date_str.strip()
    # Already correct format
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str
    # Normalise multiple spaces
    date_str = re.sub(r"\s+", " ", date_str)
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(
        f"Could not parse date '{date_str}'. "
        "Please use formats like: '15 April 2026', '15/04/2026', or '2026-04-15'."
    )


def _serp(params: dict) -> dict:
    params["api_key"] = API_KEY
    response = requests.get(SERPAPI_BASE, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


# ─── FLIGHTS ──────────────────────────────────────────────────────────────────

def search_flights(
    origin: str,
    destination: str,
    date: str,
    adults: int = 1,
    currency: str = "INR",
) -> str:
    """
    Search Google Flights for available flights from origin to destination.
    origin and destination accept Indian city names (e.g. 'Mumbai', 'Delhi', 'Bangalore')
    or IATA codes (e.g. 'BOM', 'DEL', 'BLR').
    date accepts any common format: '15 April 2026', '15/04/2026', '2026-04-15'.
    """
    if not API_KEY:
        return "Error: SERPAPI_KEY is not configured. Add it to your .env file."

    # Resolve city names → IATA codes
    departure_id = _resolve_airport(origin)
    arrival_id   = _resolve_airport(destination)

    # Normalise date to YYYY-MM-DD
    try:
        outbound_date = _parse_date(date)
    except ValueError as e:
        return str(e)

    try:
        params = {
            "engine":        "google_flights",
            "departure_id":  departure_id,
            "arrival_id":    arrival_id,
            "outbound_date": outbound_date,
            "adults":        str(adults),
            "currency":      currency.upper(),
            "type":          "2",   # one-way
            "hl":            "en",
        }

        logger.info({
            "event":    "search_flights",
            "origin":   origin,   "departure_id": departure_id,
            "dest":     destination, "arrival_id": arrival_id,
            "date":     outbound_date,
        })

        data = _serp(params)

        best        = data.get("best_flights", [])
        others      = data.get("other_flights", [])
        all_flights = (best or []) + (others or [])

        if not all_flights:
            return (
                f"No flights found from {origin} ({departure_id}) to "
                f"{destination} ({arrival_id}) on {outbound_date}. "
                "The route may not exist or the date may be too far ahead."
            )

        lines = [
            f"✈️  Flights from {origin.title()} ({departure_id}) → "
            f"{destination.title()} ({arrival_id})  |  {outbound_date}  "
            f"|  {adults} adult(s)  |  {currency.upper()}\n"
        ]

        for i, flight in enumerate(all_flights[:6], 1):
            legs           = flight.get("flights", [])
            price          = flight.get("price", "N/A")
            total_duration = flight.get("total_duration", "N/A")
            stops          = len(legs) - 1 if legs else 0
            stop_label     = "Non-stop" if stops == 0 else f"{stops} stop(s)"

            if legs:
                first_leg = legs[0]
                last_leg  = legs[-1]
                dep_time  = first_leg.get("departure_airport", {}).get("time", "N/A")
                arr_time  = last_leg.get("arrival_airport", {}).get("time", "N/A")
                airline   = first_leg.get("airline", "N/A")
                flight_no = first_leg.get("flight_number", "N/A")
            else:
                dep_time = arr_time = airline = flight_no = "N/A"

            carbon     = flight.get("carbon_emissions", {})
            carbon_str = (
                f"{carbon.get('this_flight', 0) // 1000} kg CO₂"
                if carbon.get("this_flight") else "N/A"
            )

            lines.append(
                f"{i}. {airline} {flight_no}  |  {stop_label}\n"
                f"   Departs: {dep_time}  →  Arrives: {arr_time}\n"
                f"   Duration: {total_duration} min  |  Price: {currency.upper()} {price}\n"
                f"   Carbon: {carbon_str}\n"
            )

        return "\n".join(lines)

    except requests.HTTPError as e:
        logger.error({"event": "search_flights_error", "error": str(e)})
        return f"Flight search failed (HTTP {e.response.status_code if e.response else '?'}): {e}"
    except Exception as e:
        logger.error({"event": "search_flights_error", "error": str(e)})
        return f"Error searching flights: {str(e)}"


# ─── HOTELS ───────────────────────────────────────────────────────────────────

def search_hotels(destination: str, currency: str = "INR") -> str:
    """
    Search Google Hotels for available hotels in a destination city.
    destination accepts any Indian city name (e.g. 'Mumbai', 'Goa', 'Jaipur').
    Check-in is set to tomorrow and check-out to 2 days from now automatically.
    """
    if not API_KEY:
        return "Error: SERPAPI_KEY is not configured. Add it to your .env file."

    # Auto-generate check-in (tomorrow) and check-out (day after tomorrow)
    from datetime import date, timedelta
    today         = date.today()
    check_in_date  = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    check_out_date = (today + timedelta(days=2)).strftime("%Y-%m-%d")

    try:
        params = {
            "engine":         "google_hotels",
            "q":              f"hotels in {destination}",
            "check_in_date":  check_in_date,
            "check_out_date": check_out_date,
            "adults":         "2",
            "currency":       currency.upper(),
            "hl":             "en",
            "gl":             "in",
        }

        logger.info({
            "event":       "search_hotels",
            "destination": destination,
            "check_in":    check_in_date,
            "check_out":   check_out_date,
        })

        data = _serp(params)

        properties = data.get("properties", [])
        if not properties:
            return (
                f"No hotels found in '{destination}'. "
                "Try a broader or different city name."
            )

        lines = [f"🏨  Hotels in {destination.title()} | {currency.upper()}:\n"]

        for i, hotel in enumerate(properties[:6], 1):
            name        = hotel.get("name", "N/A")
            rating      = hotel.get("overall_rating", "N/A")
            reviews     = hotel.get("reviews", "N/A")
            price       = hotel.get("rate_per_night", {}).get("lowest", "N/A")
            total_price = hotel.get("total_rate", {}).get("lowest", "N/A")
            star_class  = hotel.get("hotel_class", "")
            amenities   = hotel.get("amenities", [])
            amenity_str = ", ".join(amenities[:5]) if amenities else "N/A"
            link        = hotel.get("link", "")

            lines.append(
                f"{i}. {name}  {star_class}\n"
                f"   Rating: {rating}/5  ({reviews} reviews)\n"
                f"   Price: {currency.upper()} {price}/night  (Total: {currency.upper()} {total_price})\n"
                f"   Amenities: {amenity_str}\n"
                f"   {link}\n"
            )

        return "\n".join(lines)

    except requests.HTTPError as e:
        logger.error({"event": "search_hotels_error", "error": str(e)})
        return f"Hotel search failed (HTTP {e.response.status_code if e.response else '?'}): {e}"
    except Exception as e:
        logger.error({"event": "search_hotels_error", "error": str(e)})
        return f"Error searching hotels: {str(e)}"


# ─── TOURIST PLACES ──────────────────────────────────────────────────────────

def search_tourist_places(destination: str) -> str:
    """
    Search for top tourist attractions and places to visit in a destination city.
    destination accepts any Indian city name (e.g. 'Jaipur', 'Goa', 'Agra', 'Varanasi').
    Returns top attractions with address, rating, reviews and website.
    """
    if not API_KEY:
        return "Error: SERPAPI_KEY is not configured. Add it to your .env file."

    try:
        query = f"tourist attractions in {destination.strip()}"
        params = {
            "engine": "google_maps",
            "q":      query,
            "type":   "search",
            "hl":     "en",
            "gl":     "in",
        }

        logger.info({"event": "search_tourist_places", "destination": destination})

        data = _serp(params)
        results = data.get("local_results", [])

        if not results:
            # Fallback: try organic Google search for tourist places
            fallback_params = {
                "engine": "google",
                "q":      f"top tourist places to visit in {destination}",
                "num":    8,
            }
            fallback_data = _serp(fallback_params)
            organic = fallback_data.get("organic_results", [])
            if not organic:
                return f"No tourist places found for '{destination}'. Try a different city name."

            lines = [f"🏔️  Top tourist places in {destination.title()} (web results):\n"]
            for i, r in enumerate(organic[:6], 1):
                lines.append(
                    f"{i}. {r.get('title', 'N/A')}\n"
                    f"   {r.get('snippet', '')}\n"
                    f"   {r.get('link', '')}\n"
                )
            return "\n".join(lines)

        lines = [f"🏔️  Tourist attractions in {destination.title()}:\n"]

        for i, place in enumerate(results[:8], 1):
            name       = place.get("title", "N/A")
            address    = place.get("address", "N/A")
            rating     = place.get("rating", "N/A")
            reviews    = place.get("reviews", "N/A")
            category   = place.get("type", "")
            website    = place.get("website", "")
            hours      = place.get("hours", "")
            description = place.get("description", "")

            lines.append(
                f"{i}. {name}" + (f"  [{category}]" if category else "") + "\n"
                f"   📍 {address}\n"
                f"   ⭐ {rating}/5  ({reviews} reviews)"
                + (f"  |  🕒 {hours}" if hours else "") + "\n"
                + (f"   {description[:120]}\n" if description else "")
                + (f"   🌐 {website}\n" if website else "")
            )

        return "\n".join(lines)

    except requests.HTTPError as e:
        logger.error({"event": "search_tourist_places_error", "error": str(e)})
        return f"Tourist places search failed (HTTP {e.response.status_code if e.response else '?'}): {e}"
    except Exception as e:
        logger.error({"event": "search_tourist_places_error", "error": str(e)})
        return f"Error searching tourist places: {str(e)}"
