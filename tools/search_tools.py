import requests
from utils.config import settings
from utils.logger import get_logger

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
    """Search for recent news articles on a topic."""
    try:
        data = _serp({"engine": "google", "q": query, "tbm": "nws", "num": 8})
        results = data.get("news_results", [])
        if not results:
            return f"No news results found for: {query}"
        lines = [f"News results for '{query}':\n"]
        for i, r in enumerate(results[:8], 1):
            lines.append(
                f"{i}. {r.get('title', 'No title')}\n"
                f"   Source: {r.get('source', 'Unknown')} | Date: {r.get('date', 'N/A')}\n"
                f"   {r.get('snippet', '')}\n"
                f"   {r.get('link', '')}\n"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"news_search failed for '{query}': {e}")
        return f"Error performing news search: {str(e)}"


def image_search(query: str) -> str:
    """Search Google Images and return image URLs and metadata."""
    try:
        data = _serp({"engine": "google", "q": query, "tbm": "isch"})
        results = data.get("images_results", [])
        if not results:
            return f"No image results found for: {query}"
        lines = [f"Image search results for '{query}':\n"]
        for i, r in enumerate(results[:6], 1):
            lines.append(
                f"{i}. {r.get('title', 'No title')}\n"
                f"   Image URL: {r.get('original', r.get('thumbnail', 'N/A'))}\n"
                f"   Source: {r.get('source', 'N/A')}\n"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"image_search failed for '{query}': {e}")
        return f"Error performing image search: {str(e)}"


def places_search(query: str, location: str = "") -> str:
    """Search Google Maps for businesses, restaurants, or landmarks."""
    try:
        params = {"engine": "google_maps", "q": query, "type": "search"}
        if location:
            params["q"] = f"{query} in {location}"
        data = _serp(params)
        results = data.get("local_results", [])
        if not results:
            return f"No places found for: {query}"
        lines = [f"Places results for '{query}':\n"]
        for i, r in enumerate(results[:6], 1):
            lines.append(
                f"{i}. {r.get('title', 'No title')}\n"
                f"   Address: {r.get('address', 'N/A')}\n"
                f"   Rating: {r.get('rating', 'N/A')} ({r.get('reviews', 'N/A')} reviews)\n"
                f"   Phone: {r.get('phone', 'N/A')}\n"
                f"   Website: {r.get('website', 'N/A')}\n"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"places_search failed for '{query}': {e}")
        return f"Error performing places search: {str(e)}"


def shopping_search(query: str) -> str:
    """Search Google Shopping for product prices and listings."""
    try:
        data = _serp({"engine": "google", "q": query, "tbm": "shop"})
        results = data.get("shopping_results", [])
        if not results:
            return f"No shopping results found for: {query}"
        lines = [f"Shopping results for '{query}':\n"]
        for i, r in enumerate(results[:6], 1):
            lines.append(
                f"{i}. {r.get('title', 'No title')}\n"
                f"   Price: {r.get('price', 'N/A')}\n"
                f"   Store: {r.get('source', 'N/A')}\n"
                f"   Rating: {r.get('rating', 'N/A')}\n"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"shopping_search failed for '{query}': {e}")
        return f"Error performing shopping search: {str(e)}"


def youtube_search(query: str) -> str:
    """Search YouTube for videos on a topic."""
    try:
        data = _serp({"engine": "youtube", "search_query": query})
        results = data.get("video_results", [])
        if not results:
            return f"No YouTube results found for: {query}"
        lines = [f"YouTube results for '{query}':\n"]
        for i, r in enumerate(results[:6], 1):
            lines.append(
                f"{i}. {r.get('title', 'No title')}\n"
                f"   Channel: {r.get('channel', {}).get('name', 'N/A')}\n"
                f"   Views: {r.get('views', 'N/A')} | Published: {r.get('published_date', 'N/A')}\n"
                f"   URL: {r.get('link', 'N/A')}\n"
                f"   {r.get('description', '')[:120]}\n"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"youtube_search failed for '{query}': {e}")
        return f"Error performing YouTube search: {str(e)}"


def jobs_search(query: str, location: str = "") -> str:
    """Search Google Jobs for job listings."""
    try:
        q = f"{query} {location}".strip()
        data = _serp({"engine": "google_jobs", "q": q})
        results = data.get("jobs_results", [])
        if not results:
            return f"No job results found for: {query}"
        lines = [f"Job listings for '{query}':\n"]
        for i, r in enumerate(results[:6], 1):
            lines.append(
                f"{i}. {r.get('title', 'No title')}\n"
                f"   Company: {r.get('company_name', 'N/A')}\n"
                f"   Location: {r.get('location', 'N/A')}\n"
                f"   Posted: {r.get('detected_extensions', {}).get('posted_at', 'N/A')}\n"
                f"   {r.get('description', '')[:150]}\n"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"jobs_search failed for '{query}': {e}")
        return f"Error performing jobs search: {str(e)}"


def scholar_search(query: str) -> str:
    """Search Google Scholar for academic papers and research."""
    try:
        data = _serp({"engine": "google_scholar", "q": query})
        results = data.get("organic_results", [])
        if not results:
            return f"No scholar results found for: {query}"
        lines = [f"Google Scholar results for '{query}':\n"]
        for i, r in enumerate(results[:6], 1):
            pub_info = r.get("publication_info", {})
            lines.append(
                f"{i}. {r.get('title', 'No title')}\n"
                f"   Authors: {pub_info.get('authors', [{'name': 'N/A'}])[0].get('name', 'N/A') if pub_info.get('authors') else 'N/A'}\n"
                f"   Summary: {pub_info.get('summary', 'N/A')}\n"
                f"   Citations: {r.get('inline_links', {}).get('cited_by', {}).get('total', 'N/A')}\n"
                f"   {r.get('snippet', '')[:150]}\n"
            )
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"scholar_search failed for '{query}': {e}")
        return f"Error performing scholar search: {str(e)}"


def stock_search(ticker: str) -> str:
    """Search Google Finance for stock price and financial data."""
    try:
        data = _serp({"engine": "google_finance", "q": ticker})
        summary = data.get("summary", {})
        if not summary:
            return f"No stock data found for ticker: {ticker}"
        return (
            f"Stock data for {ticker}:\n"
            f"  Price: {summary.get('price', 'N/A')}\n"
            f"  Change: {summary.get('price_change', 'N/A')} ({summary.get('price_change_percentage', 'N/A')})\n"
            f"  Currency: {summary.get('currency', 'N/A')}\n"
            f"  Exchange: {summary.get('exchange', 'N/A')}"
        )
    except Exception as e:
        logger.error(f"stock_search failed for '{ticker}': {e}")
        return f"Error fetching stock data for {ticker}: {str(e)}"


def autocomplete_search(query: str) -> str:
    """Get Google autocomplete suggestions for a search query."""
    try:
        data = _serp({"engine": "google_autocomplete", "q": query})
        suggestions = data.get("suggestions", [])
        if not suggestions:
            return f"No autocomplete suggestions found for: {query}"
        lines = [f"Autocomplete suggestions for '{query}':\n"]
        for i, s in enumerate(suggestions[:10], 1):
            lines.append(f"  {i}. {s.get('value', s)}")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"autocomplete_search failed for '{query}': {e}")
        return f"Error fetching autocomplete suggestions: {str(e)}"
