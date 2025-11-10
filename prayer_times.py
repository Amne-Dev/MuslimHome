"""Utilities for detecting location and fetching daily prayer times."""
from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import datetime, date
from typing import Dict, List, Optional

import pytz
import requests
from tzlocal import get_localzone_name

LOGGER = logging.getLogger(__name__)

ALADHAN_TIMINGS_URL = "https://api.aladhan.com/v1/timings"
ALADHAN_TIMINGS_BY_CITY_URL = "https://api.aladhan.com/v1/timingsByCity"
PRAYER_ORDER = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]


@dataclass
class LocationInfo:
    city: str
    country: str
    latitude: Optional[float]
    longitude: Optional[float]
    timezone: Optional[str]


@dataclass
class PrayerInfo:
    name: str
    time: datetime


@dataclass
class PrayerDay:
    location: LocationInfo
    hijri_date: str
    gregorian_date: date
    prayers: List[PrayerInfo]

    def next_prayer(self, now: Optional[datetime] = None) -> Optional[PrayerInfo]:
        """Return the next upcoming prayer relative to *now*."""
        now = now or datetime.now(self.prayers[0].time.tzinfo)
        for info in self.prayers:
            if info.time > now:
                return info
        return None


class PrayerTimesService:
    """Fetches prayer times from the AlAdhan API."""

    def __init__(self, method: int = 3, school: int = 0) -> None:
        self.method = method
        self.school = school

    def fetch_prayer_times(
        self,
        location: LocationInfo,
        target_date: Optional[date] = None,
    ) -> PrayerDay:
        target_date = target_date or date.today()
        use_city_lookup = location.latitude is None or location.longitude is None
        LOGGER.debug(
            "Fetching prayer times for %s, %s (date=%s mode=%s)",
            location.city,
            location.country,
            target_date,
            "city" if use_city_lookup else "coordinates",
        )

        if use_city_lookup:
            params = {
                "city": location.city,
                "country": location.country,
                "method": self.method,
                "school": self.school,
                "date": target_date.strftime("%d-%m-%Y"),
            }
            LOGGER.debug("Requesting prayer times by city with params=%s", params)
            response = requests.get(ALADHAN_TIMINGS_BY_CITY_URL, params=params, timeout=10)
        else:
            params = {
                "latitude": location.latitude,
                "longitude": location.longitude,
                "method": self.method,
                "school": self.school,
                "date": target_date.strftime("%d-%m-%Y"),
            }

            LOGGER.debug("Requesting prayer times with params=%s", params)
            response = requests.get(ALADHAN_TIMINGS_URL, params=params, timeout=10)
        LOGGER.debug("Prayer times response status: %s", response.status_code)
        response.raise_for_status()

        payload = response.json()
        LOGGER.debug("Prayer times response keys: %s", list(payload.keys()))
        if payload.get("code") != 200:
            raise RuntimeError(f"Invalid response from AlAdhan API: {payload.get('status')}")

        data = payload.get("data", {})
        timings: Dict[str, str] = data.get("timings", {})
        hijri = data.get("date", {}).get("hijri", {})
        gregorian = data.get("date", {}).get("gregorian", {})

        timezone_name = self._resolve_timezone(location, data)
        tzinfo = pytz.timezone(timezone_name)
        prayers = [
            PrayerInfo(name=prayer, time=self._parse_time_string(timings.get(prayer, "00:00"), tzinfo, target_date))
            for prayer in PRAYER_ORDER
        ]

        hijri_day = hijri.get("day")
        hijri_month_en = (hijri.get("month", {}) or {}).get("en", "")
        hijri_year = hijri.get("year")
        hijri_date_text = hijri.get("date", "")
        if hijri_day and hijri_month_en and hijri_year:
            hijri_date_text = f"{hijri_day} {hijri_month_en} {hijri_year} AH"

        gregorian_date_str = gregorian.get("date")
        try:
            gregorian_date = datetime.strptime(gregorian_date_str, "%d-%m-%Y").date() if gregorian_date_str else target_date
        except (TypeError, ValueError):
            gregorian_date = target_date

        meta = data.get("meta", {})
        updated_location = replace(
            location,
            latitude=_safe_float(meta.get("latitude")) or location.latitude,
            longitude=_safe_float(meta.get("longitude")) or location.longitude,
            timezone=timezone_name,
        )

        return PrayerDay(
            location=updated_location,
            hijri_date=hijri_date_text,
            gregorian_date=gregorian_date,
            prayers=prayers,
        )

    @staticmethod
    def _parse_time_string(time_str: str, tzinfo: pytz.BaseTzInfo, target_date: date) -> datetime:
        clean = "".join(ch for ch in time_str if ch.isdigit() or ch == ":")[:5]
        if len(clean) != 5:
            clean = "00:00"
        hour, minute = map(int, clean.split(":"))
        naive = datetime(target_date.year, target_date.month, target_date.day, hour=hour, minute=minute)
        localized = tzinfo.localize(naive)
        LOGGER.debug("Parsed prayer time %s -> %s", time_str, localized)
        return localized

    @staticmethod
    def _resolve_timezone(location: LocationInfo, data: Dict[str, Dict]) -> str:
        timezone_name = (data.get("meta", {}) or {}).get("timezone") or location.timezone
        if not timezone_name:
            LOGGER.warning("Timezone missing from response; defaulting to UTC")
            timezone_name = "UTC"
        try:
            pytz.timezone(timezone_name)
        except Exception:
            LOGGER.warning("Unknown timezone '%s'; falling back to UTC", timezone_name)
            timezone_name = "UTC"
        return timezone_name


def detect_location_from_ip(timeout: int = 5) -> LocationInfo:
    """Attempt to detect approximate location using the ipinfo.io service."""
    LOGGER.debug("Requesting IP-based location from ipinfo.io (timeout=%s)", timeout)
    response = requests.get("https://ipinfo.io/json", timeout=timeout)
    LOGGER.debug("ipinfo.io response status: %s", response.status_code)
    response.raise_for_status()
    payload = response.json()
    LOGGER.debug("ipinfo.io payload keys: %s", list(payload.keys()))

    loc_token = payload.get("loc", "0,0")
    latitude, longitude = map(float, loc_token.split(","))
    LOGGER.debug("Parsed coordinates from ipinfo.io: lat=%s lon=%s", latitude, longitude)

    try:
        timezone_guess = get_localzone_name()
    except Exception:  # pragma: no cover - defensive fallback
        timezone_guess = "UTC"

    timezone = payload.get("timezone") or timezone_guess or "UTC"
    try:
        pytz.timezone(timezone)
    except Exception:
        LOGGER.warning("Falling back to UTC for unknown timezone %s", timezone)
        timezone = "UTC"

    LOGGER.debug(
        "Constructed LocationInfo from ipinfo.io: city=%s country=%s tz=%s",
        payload.get("city", ""),
        payload.get("country", ""),
        timezone,
    )

    return LocationInfo(
        city=payload.get("city", ""),
        country=payload.get("country", ""),
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
    )


def build_location_from_config(config: Dict[str, object]) -> Optional[LocationInfo]:
    """Create a LocationInfo instance if the config contains the required data."""
    location_cfg = config.get("location") if isinstance(config, dict) else None
    if not isinstance(location_cfg, dict):
        return None

    city = location_cfg.get("city", "")
    country = location_cfg.get("country", "")

    try:
        return LocationInfo(
            city=str(city),
            country=str(country),
            latitude=_safe_float(location_cfg.get("latitude")),
            longitude=_safe_float(location_cfg.get("longitude")),
            timezone=str(location_cfg.get("timezone")) if location_cfg.get("timezone") else None,
        )
    except (KeyError, TypeError, ValueError):
        LOGGER.exception("Invalid location config: %s", location_cfg)
        return None


def _safe_float(value: Optional[object]) -> Optional[float]:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
