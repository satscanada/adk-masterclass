from __future__ import annotations

import json
import logging
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus, urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv

from simple_litellm_agent.config import ENV_FILE

METEOSOURCE_POINT_URL = "https://www.meteosource.com/api/v1/free/point"

logger = logging.getLogger(__name__)


def _reload_dotenv_for_weather() -> None:
    """Re-read `.env` so `WEATHER_API_KEY` updates apply without restarting the API.

    Initial `load_dotenv(..., override=False)` in config does not refresh later file edits.
    """
    load_dotenv(ENV_FILE, override=True)


def fetch_current_weather(place_id: str) -> dict[str, Any]:
    """Fetch current weather for a place from the Meteosource free API.

    Args:
        place_id: Meteosource place identifier (e.g. 'calgary', 'london'). Use lowercase
            slugs without spaces when possible.

    Returns:
        A dict with status, summary, temperature in Celsius, wind, and precipitation,
        or status error with a message.
    """
    _reload_dotenv_for_weather()
    key = (os.getenv("WEATHER_API_KEY") or "").strip()
    if not key:
        logger.warning("fetch_current_weather: WEATHER_API_KEY is missing after loading %s", ENV_FILE)
        return {
            "status": "error",
            "message": "WEATHER_API_KEY is not set. Add it to your .env file.",
        }

    cleaned = (place_id or "").strip().lower()
    if not cleaned:
        return {"status": "error", "message": "place_id must not be empty."}

    params = {
        "place_id": cleaned,
        "sections": "current",
        "language": "en",
        "units": "metric",
        "key": key,
    }
    query = urlencode(params, quote_via=quote_plus)
    url = f"{METEOSOURCE_POINT_URL}?{query}"
    req = Request(url, headers={"User-Agent": "adk-masterclass-advanced-agent/1.0"})

    try:
        with urlopen(req, timeout=20) as resp:
            status = getattr(resp, "status", None) or getattr(resp, "code", "?")
            raw = resp.read().decode("utf-8")
            logger.info(
                "Meteosource API response place_id=%s http_status=%s body=%s",
                cleaned,
                status,
                raw,
            )
    except HTTPError as exc:
        err = f"Weather API HTTP error: {exc.code} {exc.reason}"
        logger.warning("fetch_current_weather: %s", err)
        return {
            "status": "error",
            "message": err,
        }
    except URLError as exc:
        err = f"Weather API network error: {exc.reason}"
        logger.warning("fetch_current_weather: %s", err)
        return {"status": "error", "message": err}
    except OSError as exc:
        err = f"Weather API error: {exc}"
        logger.warning("fetch_current_weather: %s", err)
        return {"status": "error", "message": err}

    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError:
        return {"status": "error", "message": "Invalid JSON from weather API."}

    current = data.get("current")
    if not isinstance(current, dict):
        return {
            "status": "error",
            "message": "No current weather in API response.",
            "raw": data,
        }

    temp = current.get("temperature")
    if temp is None:
        return {"status": "error", "message": "No temperature in current conditions.", "raw": data}

    wind = current.get("wind") if isinstance(current.get("wind"), dict) else {}
    precip = current.get("precipitation") if isinstance(current.get("precipitation"), dict) else {}

    return {
        "status": "success",
        "place_id": cleaned,
        "summary": str(current.get("summary", "")),
        "temperature_celsius": float(temp),
        "wind_speed": float(wind.get("speed", 0) or 0),
        "wind_dir": str(wind.get("dir", "")),
        "precipitation_type": str(precip.get("type", "") or ""),
        "cloud_cover": current.get("cloud_cover"),
        "timezone": data.get("timezone"),
    }


def celsius_to_fahrenheit_display(celsius: float) -> dict[str, Any]:
    """Convert a temperature from Celsius to Fahrenheit for user-facing replies.

    Args:
        celsius: Temperature in degrees Celsius (from the weather API when using units=metric).

    Returns:
        Both numeric values and a short formatted string with °C and °F.
    """
    fahrenheit = celsius * 9.0 / 5.0 + 32.0
    c_round = round(float(celsius), 1)
    f_round = round(fahrenheit, 1)
    return {
        "status": "success",
        "celsius": c_round,
        "fahrenheit": f_round,
        "formatted": f"{c_round} °C ({f_round} °F)",
    }
