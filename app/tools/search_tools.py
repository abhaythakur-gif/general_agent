import requests
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)
SERPAPI_BASE = "https://serpapi.com/search"
API_KEY = settings.SERPAPI_KEY


def _serp(params: dict) -> dict:
    params["api_key"] = API_KEY
    response = requests.get(SERPAPI_BASE, params=params, timeout=15)
    response.raise_for_status()
    return response.json()


def web_search(query: str) -> str:
    """Search the internet for any topic and return top results."""
    try:
        data = _serp({"engine": "google", "q": query, "num": 8})
        results = data.get("organic_results", [])
        if not results:
            return f"No results found for: {query}"
        lines = [f"Web search results for '{query}':\n"]
        for i, r in enumerate(results[:8], 1):
            lines.append(f"{i}. {r.get('title', 'No title')}\n   {r.get('link', '')}\n   {r.get('snippet', '')}\n")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"web_search failed for '{query}': {e}")
        return f"Error performing web search: {str(e)}"


def news_search(query: str) -> str:
    """Search for recent news articles on any topic."""
    try:
        data = _serp({"engine": "google_news", "q": query})
        results = data.get("news_results", [])
        if not results:
            return f"No news found for: {query}"
        lines = [f"News results for '{query}':\n"]
        for i, r in enumerate(results[:8], 1):
            lines.append(f"{i}. {r.get('title', 'No title')}\n   Source: {r.get('source', {}).get('name', 'Unknown')} | {r.get('date', '')}\n   {r.get('snippet', '')}\n")
        return "\n".join(lines)
    except Exception as e:
        return f"Error performing news search: {str(e)}"


def image_search(query: str) -> str:
    """Search Google Images and return image URLs."""
    try:
        data = _serp({"engine": "google_images", "q": query})
        results = data.get("images_results", [])
        if not results:
            return f"No images found for: {query}"
        lines = [f"Image results for '{query}':\n"]
        for i, r in enumerate(results[:5], 1):
            lines.append(f"{i}. {r.get('title', 'No title')}\n   URL: {r.get('original', '')}\n   Source: {r.get('source', '')}\n")
        return "\n".join(lines)
    except Exception as e:
        return f"Error performing image search: {str(e)}"


def places_search(query: str, location: str = "") -> str:
    """Search Google Maps for businesses or places."""
    try:
        params = {"engine": "google_maps", "q": query, "type": "search"}
        if location:
            params["ll"] = location
        data = _serp(params)
        results = data.get("local_results", [])
        if not results:
            return f"No places found for: {query}"
        lines = [f"Places results for '{query}':\n"]
        for i, r in enumerate(results[:5], 1):
            lines.append(
                f"{i}. {r.get('title', 'No title')}\n"
                f"   Address: {r.get('address', 'N/A')}\n"
                f"   Rating: {r.get('rating', 'N/A')} ({r.get('reviews', 'N/A')} reviews)\n"
                f"   Phone: {r.get('phone', 'N/A')}\n"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error performing places search: {str(e)}"


def shopping_search(query: str) -> str:
    """Search Google Shopping for product prices."""
    try:
        data = _serp({"engine": "google_shopping", "q": query})
        results = data.get("shopping_results", [])
        if not results:
            return f"No shopping results for: {query}"
        lines = [f"Shopping results for '{query}':\n"]
        for i, r in enumerate(results[:6], 1):
            lines.append(f"{i}. {r.get('title', 'No title')}\n   Price: {r.get('price', 'N/A')} | Store: {r.get('source', 'N/A')}\n   Rating: {r.get('rating', 'N/A')}\n")
        return "\n".join(lines)
    except Exception as e:
        return f"Error performing shopping search: {str(e)}"


def youtube_search(query: str) -> str:
    """Search YouTube for videos."""
    try:
        data = _serp({"engine": "youtube", "search_query": query})
        results = data.get("video_results", [])
        if not results:
            return f"No YouTube results for: {query}"
        lines = [f"YouTube results for '{query}':\n"]
        for i, r in enumerate(results[:5], 1):
            lines.append(f"{i}. {r.get('title', 'No title')}\n   Channel: {r.get('channel', {}).get('name', 'N/A')} | Views: {r.get('views', 'N/A')}\n   Link: {r.get('link', '')}\n")
        return "\n".join(lines)
    except Exception as e:
        return f"Error performing YouTube search: {str(e)}"


def jobs_search(query: str, location: str = "") -> str:
    """Search Google Jobs for job listings."""
    try:
        params = {"engine": "google_jobs", "q": query}
        if location:
            params["location"] = location
        data = _serp(params)
        results = data.get("jobs_results", [])
        if not results:
            return f"No job results for: {query}"
        lines = [f"Job results for '{query}':\n"]
        for i, r in enumerate(results[:5], 1):
            lines.append(f"{i}. {r.get('title', 'No title')}\n   Company: {r.get('company_name', 'N/A')} | Location: {r.get('location', 'N/A')}\n   {r.get('description', '')[:200]}\n")
        return "\n".join(lines)
    except Exception as e:
        return f"Error performing jobs search: {str(e)}"


def scholar_search(query: str) -> str:
    """Search Google Scholar for academic papers."""
    try:
        data = _serp({"engine": "google_scholar", "q": query})
        results = data.get("organic_results", [])
        if not results:
            return f"No scholar results for: {query}"
        lines = [f"Scholar results for '{query}':\n"]
        for i, r in enumerate(results[:5], 1):
            lines.append(f"{i}. {r.get('title', 'No title')}\n   Authors: {r.get('publication_info', {}).get('authors', [])}\n   Citations: {r.get('inline_links', {}).get('cited_by', {}).get('total', 'N/A')}\n")
        return "\n".join(lines)
    except Exception as e:
        return f"Error performing scholar search: {str(e)}"


def stock_search(ticker: str) -> str:
    """Get stock price info from Google Finance."""
    try:
        data = _serp({"engine": "google_finance", "q": ticker})
        summary = data.get("summary", {})
        if not summary:
            return f"No stock data found for: {ticker}"
        return (
            f"Stock: {ticker.upper()}\n"
            f"  Price: {summary.get('price', 'N/A')}\n"
            f"  Change: {summary.get('price_change', 'N/A')} ({summary.get('price_change_percentage', 'N/A')})\n"
            f"  Exchange: {summary.get('exchange', 'N/A')}\n"
        )
    except Exception as e:
        return f"Error performing stock search: {str(e)}"


def autocomplete_search(query: str) -> str:
    """Get Google autocomplete suggestions."""
    try:
        data = _serp({"engine": "google_autocomplete", "q": query})
        suggestions = data.get("suggestions", [])
        if not suggestions:
            return f"No suggestions for: {query}"
        lines = [s.get("value", "") for s in suggestions[:10]]
        return f"Autocomplete suggestions for '{query}':\n" + "\n".join(f"  - {l}" for l in lines)
    except Exception as e:
        return f"Error performing autocomplete search: {str(e)}"
