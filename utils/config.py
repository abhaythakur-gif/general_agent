import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    SERPAPI_KEY: str = os.getenv("SERPAPI_KEY", "")
    WEATHER_API_KEY: str = os.getenv("weather_api_key", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./agent_platform.db")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
