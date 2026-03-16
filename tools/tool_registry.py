from tools.travel_tools import (
    search_flights,
    search_hotels,
    search_tourist_places,
)
from tools.weather_tools import (
    get_current_weather,
    get_weather_forecast,
    get_air_quality,
    get_astronomy,
    get_historical_weather,
    search_timezone,
)
from tools.search_tools import (
    web_search,
    news_search,
    image_search,
    places_search,
    shopping_search,
    youtube_search,
    jobs_search,
    scholar_search,
    stock_search,
    autocomplete_search,
)

# Maps tool name (string) → Python function
tool_registry: dict = {
    "get_current_weather": get_current_weather,
    "get_weather_forecast": get_weather_forecast,
    "get_air_quality": get_air_quality,
    "get_astronomy": get_astronomy,
    "get_historical_weather": get_historical_weather,
    "search_timezone": search_timezone,
    "web_search": web_search,
    "news_search": news_search,
    "image_search": image_search,
    "places_search": places_search,
    "shopping_search": shopping_search,
    "youtube_search": youtube_search,
    "jobs_search": jobs_search,
    "scholar_search": scholar_search,
    "stock_search": stock_search,
    "autocomplete_search": autocomplete_search,
    # Travel
    "search_flights":        search_flights,
    "search_hotels":         search_hotels,
    "search_tourist_places": search_tourist_places,
}

# Metadata for UI display and prompt generation
tool_metadata: dict = {
    "get_current_weather": {
        "name": "get_current_weather",
        "description": "Get current weather conditions (temperature, humidity, wind, UV index) for any city.",
        "inputs": ["city"],
        "category": "Weather",
        "api_source": "WeatherAPI.com",
    },
    "get_weather_forecast": {
        "name": "get_weather_forecast",
        "description": "Get weather forecast for next 1-10 days including rain chance and sunrise/sunset.",
        "inputs": ["city", "days (1-10)"],
        "category": "Weather",
        "api_source": "WeatherAPI.com",
    },
    "get_air_quality": {
        "name": "get_air_quality",
        "description": "Get air quality index including CO, NO2, O3, PM2.5, PM10 levels for a city.",
        "inputs": ["city"],
        "category": "Weather",
        "api_source": "WeatherAPI.com",
    },
    "get_astronomy": {
        "name": "get_astronomy",
        "description": "Get sunrise, sunset, moonrise, moonset and moon phase for a city and date.",
        "inputs": ["city", "date (YYYY-MM-DD)"],
        "category": "Weather",
        "api_source": "WeatherAPI.com",
    },
    "get_historical_weather": {
        "name": "get_historical_weather",
        "description": "Get historical weather data for a city on a specific past date.",
        "inputs": ["city", "date (YYYY-MM-DD)"],
        "category": "Weather",
        "api_source": "WeatherAPI.com",
    },
    "search_timezone": {
        "name": "search_timezone",
        "description": "Get current local time, timezone ID, and UTC offset for any city.",
        "inputs": ["city"],
        "category": "Weather",
        "api_source": "WeatherAPI.com",
    },
    "web_search": {
        "name": "web_search",
        "description": "Search the internet for any topic and return top organic results with snippets.",
        "inputs": ["query"],
        "category": "Search",
        "api_source": "SerpAPI (Google)",
    },
    "news_search": {
        "name": "news_search",
        "description": "Search for recent news articles with source, date, and snippet.",
        "inputs": ["query"],
        "category": "Search",
        "api_source": "SerpAPI (Google News)",
    },
    "image_search": {
        "name": "image_search",
        "description": "Search Google Images and return image URLs and source info.",
        "inputs": ["query"],
        "category": "Search",
        "api_source": "SerpAPI (Google Images)",
    },
    "places_search": {
        "name": "places_search",
        "description": "Search Google Maps for businesses with address, rating, phone and website.",
        "inputs": ["query", "location (optional)"],
        "category": "Search",
        "api_source": "SerpAPI (Google Maps)",
    },
    "shopping_search": {
        "name": "shopping_search",
        "description": "Search Google Shopping for product prices, stores and ratings.",
        "inputs": ["query"],
        "category": "Search",
        "api_source": "SerpAPI (Google Shopping)",
    },
    "youtube_search": {
        "name": "youtube_search",
        "description": "Search YouTube for videos with channel, views, date and description.",
        "inputs": ["query"],
        "category": "Search",
        "api_source": "SerpAPI (YouTube)",
    },
    "jobs_search": {
        "name": "jobs_search",
        "description": "Search Google Jobs for job listings with company, location and description.",
        "inputs": ["query", "location (optional)"],
        "category": "Search",
        "api_source": "SerpAPI (Google Jobs)",
    },
    "scholar_search": {
        "name": "scholar_search",
        "description": "Search Google Scholar for academic papers with authors and citation count.",
        "inputs": ["query"],
        "category": "Search",
        "api_source": "SerpAPI (Google Scholar)",
    },
    "stock_search": {
        "name": "stock_search",
        "description": "Get stock price, percentage change and exchange info from Google Finance.",
        "inputs": ["ticker (e.g. AAPL, TSLA)"],
        "category": "Search",
        "api_source": "SerpAPI (Google Finance)",
    },
    "autocomplete_search": {
        "name": "autocomplete_search",
        "description": "Get Google autocomplete suggestions for a search query.",
        "inputs": ["query"],
        "category": "Search",
        "api_source": "SerpAPI (Google Autocomplete)",
    },
    "search_flights": {
        "name": "search_flights",
        "description": "Search Google Flights for one-way flights between Indian cities. Accepts city names (e.g. Mumbai, Delhi, Bangalore, Hyderabad, Chennai, Kolkata, Pune, Goa, Jaipur, Kochi) or IATA codes. Date accepts any format: '15 April 2026', '15/04/2026', '2026-04-15'.",
        "inputs": ["origin (city name or IATA, e.g. Mumbai)", "destination (city name or IATA, e.g. Delhi)", "date (any format, e.g. 15 April 2026)", "adults (default 1, optional)", "currency (default INR, optional)"],
        "category": "Travel",
        "api_source": "SerpAPI (Google Flights)",
    },
    "search_hotels": {
        "name": "search_hotels",
        "description": "Search Google Hotels for available hotels in any Indian city. Just provide the destination city name (e.g. Mumbai, Goa, Jaipur, Udaipur). Check-in and check-out dates are handled automatically.",
        "inputs": ["destination (city name, e.g. Goa)", "currency (default INR, optional)"],
        "category": "Travel",
        "api_source": "SerpAPI (Google Hotels)",
    },
    "search_tourist_places": {
        "name": "search_tourist_places",
        "description": "Find top tourist attractions and places to visit in any Indian city. Just provide the destination city name (e.g. Jaipur, Goa, Agra, Varanasi). Returns attraction name, address, rating, opening hours and website.",
        "inputs": ["destination (city name, e.g. Jaipur)"],
        "category": "Travel",
        "api_source": "SerpAPI (Google Maps)",
    },
}


def get_tool(name: str):
    """Return the callable tool function by name."""
    if name not in tool_registry:
        raise ValueError(f"Tool '{name}' is not registered.")
    return tool_registry[name]


def list_tools() -> list:
    """Return all tool metadata as a list."""
    return list(tool_metadata.values())


def get_tools_for_agent(tool_names: list) -> dict:
    """Return subset of tool_registry for the given tool names (enforces per-agent isolation)."""
    return {name: tool_registry[name] for name in tool_names if name in tool_registry}
