"""Weather data retrieval for the prayer times application."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Sequence, Tuple

import requests

LOGGER = logging.getLogger(__name__)

WEATHER_ENDPOINT = "https://api.open-meteo.com/v1/forecast"

# Open-Meteo weather codes mapped to simple descriptions.
WEATHER_CODE_MAP = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


@dataclass
class WeatherInfo:
    """Snapshot of current weather conditions."""

    temperature_c: float
    feels_like_c: Optional[float]
    humidity: Optional[int]
    wind_speed_kmh: Optional[float]
    conditions: str
    observation_time_utc: Optional[datetime]

    @property
    def temperature_f(self) -> float:
        return self.temperature_c * 9.0 / 5.0 + 32.0

    @property
    def feels_like_f(self) -> Optional[float]:
        if self.feels_like_c is None:
            return None
        return self.feels_like_c * 9.0 / 5.0 + 32.0


@dataclass
class DailyForecast:
    """Represents a single day's forecast."""

    date: datetime
    min_temperature_c: float
    max_temperature_c: float
    weather_code: int
    conditions: str

    @property
    def min_temperature_f(self) -> float:
        return self.min_temperature_c * 9.0 / 5.0 + 32.0

    @property
    def max_temperature_f(self) -> float:
        return self.max_temperature_c * 9.0 / 5.0 + 32.0


class WeatherService:
    """Thin wrapper around the Open-Meteo API for current conditions and forecast."""

    def fetch_current_weather(self, latitude: float, longitude: float, timeout: int = 8) -> WeatherInfo:
        current, _ = self.fetch_weather(latitude, longitude, days=1, timeout=timeout)
        return current

    def fetch_weather(
        self,
        latitude: float,
        longitude: float,
        *,
        days: int = 7,
        timeout: int = 8,
    ) -> Tuple[WeatherInfo, List[DailyForecast]]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min",
            "windspeed_unit": "kmh",
            "timezone": "UTC",
            "forecast_days": max(days, 1),
        }
        LOGGER.debug("Requesting weather bundle from Open-Meteo with params=%s", params)
        response = requests.get(WEATHER_ENDPOINT, params=params, timeout=timeout)
        LOGGER.debug("Open-Meteo response status: %s", response.status_code)
        response.raise_for_status()

        payload = response.json()
        LOGGER.debug("Open-Meteo payload keys: %s", list(payload.keys()))

        current = self._parse_current(payload.get("current", {}))
        forecast = self._parse_forecast(payload.get("daily", {}))
        return current, forecast

    def _parse_current(self, current: dict) -> WeatherInfo:
        temperature_raw = current.get("temperature_2m")
        if temperature_raw is None:
            raise ValueError("Weather payload missing temperature")

        apparent = current.get("apparent_temperature")
        humidity = current.get("relative_humidity_2m")
        wind_speed = current.get("wind_speed_10m")
        code_raw = current.get("weather_code", 0)
        timestamp = current.get("time")
        observed_at = None
        if timestamp:
            try:
                observed_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(timezone.utc)
            except ValueError:
                LOGGER.debug("Failed to parse observation timestamp %s", timestamp)

        try:
            code = int(code_raw)
        except (TypeError, ValueError):
            code = 0

        description = WEATHER_CODE_MAP.get(code, f"Weather code {code}")
        feels_like = float(apparent) if apparent is not None else None
        humidity_int = int(humidity) if humidity is not None else None
        wind_speed_float = float(wind_speed) if wind_speed is not None else None

        return WeatherInfo(
            temperature_c=float(temperature_raw),
            feels_like_c=feels_like,
            humidity=humidity_int,
            wind_speed_kmh=wind_speed_float,
            conditions=description,
            observation_time_utc=observed_at,
        )

    def _parse_forecast(self, daily: dict) -> List[DailyForecast]:
        dates: Sequence[str] = daily.get("time", []) or []
        max_temps: Sequence[Optional[float]] = daily.get("temperature_2m_max", []) or []
        min_temps: Sequence[Optional[float]] = daily.get("temperature_2m_min", []) or []
        codes: Sequence[Optional[int]] = daily.get("weather_code", []) or []

        forecast: List[DailyForecast] = []
        for index, iso_date in enumerate(dates):
            try:
                date_obj = datetime.fromisoformat(str(iso_date))
            except ValueError:
                LOGGER.debug("Skipping forecast entry with invalid date %s", iso_date)
                continue

            max_temp_raw = max_temps[index] if index < len(max_temps) else None
            min_temp_raw = min_temps[index] if index < len(min_temps) else None
            code_raw = codes[index] if index < len(codes) else 0

            try:
                max_temp_c = float(max_temp_raw) if max_temp_raw is not None else float("nan")
                min_temp_c = float(min_temp_raw) if min_temp_raw is not None else float("nan")
            except (TypeError, ValueError):
                LOGGER.debug("Skipping forecast entry with invalid temperature values")
                continue

            try:
                weather_code = int(code_raw) if code_raw is not None else 0
            except (TypeError, ValueError):
                weather_code = 0

            conditions = WEATHER_CODE_MAP.get(weather_code, f"Weather code {weather_code}")

            forecast.append(
                DailyForecast(
                    date=date_obj,
                    min_temperature_c=min_temp_c,
                    max_temperature_c=max_temp_c,
                    weather_code=weather_code,
                    conditions=conditions,
                )
            )

        LOGGER.debug("Parsed %d forecast entries", len(forecast))
        return forecast
