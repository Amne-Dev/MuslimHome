"""Dynamic location catalog for countries and cities supported by AlAdhan."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

LOGGER = logging.getLogger(__name__)

ALADHAN_COUNTRIES_URL = "https://api.aladhan.com/v1/countries"
ALADHAN_CITIES_URL = "https://api.aladhan.com/v1/cities"

COUNTRIESNOW_COUNTRIES_URL = "https://countriesnow.space/api/v0.1/countries/iso"
COUNTRIESNOW_CITIES_URL = "https://countriesnow.space/api/v0.1/countries/cities"


class LocationCatalog:
    """Retrieves supported countries and cities, caching results and falling back to bundled data."""

    def __init__(self, fallback_path: Path) -> None:
        self._fallback_path = fallback_path
        self._fallback_catalog: List[Dict[str, Any]] = self._load_fallback_catalog()
        self._fallback_by_code: Dict[str, Dict[str, Any]] = {
            str(entry.get("code") or "").upper(): entry for entry in self._fallback_catalog if entry.get("code")
        }
        self._fallback_by_name: Dict[str, Dict[str, Any]] = {
            str(entry.get("name") or "").lower(): entry for entry in self._fallback_catalog if entry.get("name")
        }
        self._countries: Optional[List[Dict[str, str]]] = None
        self._city_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._countries_source: str = "fallback"
        self._country_name_by_code: Dict[str, str] = {
            code: entry.get("name", "") for code, entry in self._fallback_by_code.items()
        }
        self._country_code_by_name: Dict[str, str] = {
            str(entry.get("name") or "").lower(): str(entry.get("code") or "")
            for entry in self._fallback_catalog
            if entry.get("name") and entry.get("code")
        }

    def countries(self, refresh: bool = False) -> List[Dict[str, str]]:
        """Return a sorted list of supported countries."""
        if refresh:
            self._countries = None
        if self._countries is None:
            self._countries = self._load_countries()
        return list(self._countries)

    def countries_source(self) -> str:
        """Return the origin of the currently cached country list."""
        return self._countries_source

    def cities(
        self,
        country_code: Optional[str],
        country_name: Optional[str] = None,
        refresh: bool = False,
    ) -> List[Dict[str, Any]]:
        """Return cached or freshly fetched city entries for the given country."""
        key = (country_code or country_name or "").strip()
        if not key:
            return []
        cache_key = key.upper()
        if refresh and cache_key in self._city_cache:
            self._city_cache.pop(cache_key, None)
        if cache_key not in self._city_cache:
            self._city_cache[cache_key] = self._load_cities(country_code, country_name)
        return list(self._city_cache[cache_key])

    def city_record(
        self,
        country_code: Optional[str],
        country_name: Optional[str],
        city_name: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Attempt to locate the city metadata for the provided identifiers."""
        if not city_name:
            return None
        for entry in self.cities(country_code, country_name):
            if entry.get("name") == city_name:
                return entry
        for country in self._fallback_catalog:
            for city in country.get("cities", []):
                if city.get("name") == city_name:
                    return city
        return None

    def _load_countries(self) -> List[Dict[str, str]]:
        countries = self._load_countries_from_countriesnow()
        if countries:
            return countries

        countries = self._load_countries_from_aladhan()
        if countries:
            return countries

        fallback = [
            {"name": entry.get("name", ""), "code": entry.get("code") or entry.get("name", "")}
            for entry in self._fallback_catalog
            if entry.get("name")
        ]
        fallback.sort(key=lambda item: item["name"].lower())
        self._countries_source = "fallback"
        self._country_name_by_code = {
            str(item.get("code", "")).upper(): item.get("name", "") for item in fallback if item.get("code")
        }
        self._country_code_by_name = {
            item.get("name", "").lower(): item.get("code", "") for item in fallback if item.get("name")
        }
        return fallback

    def _load_cities(self, country_code: Optional[str], country_name: Optional[str]) -> List[Dict[str, Any]]:
        cities = self._load_cities_from_countriesnow(country_code, country_name)
        if cities:
            return cities

        cities = self._load_cities_from_aladhan(country_code, country_name)
        if cities:
            return cities

        normalized_code = (country_code or "").upper()
        normalized_name = (country_name or "").lower()
        fallback_entry = None
        if normalized_code and normalized_code in self._fallback_by_code:
            fallback_entry = self._fallback_by_code[normalized_code]
        elif normalized_name and normalized_name in self._fallback_by_name:
            fallback_entry = self._fallback_by_name[normalized_name]

        if fallback_entry:
            cities = []
            for city in fallback_entry.get("cities", []):
                name = city.get("name")
                if not name:
                    continue
                lat = self._safe_float(city.get("latitude"))
                lon = self._safe_float(city.get("longitude"))
                cities.append({"name": name, "latitude": lat, "longitude": lon})
            cities.sort(key=lambda item: item["name"].lower())
            return cities
        return []

    def _load_countries_from_countriesnow(self) -> List[Dict[str, str]]:
        try:
            response = requests.get(COUNTRIESNOW_COUNTRIES_URL, timeout=10)
            response.raise_for_status()
            payload = response.json()
            if payload.get("error"):
                return []
            raw_entries = payload.get("data", [])
            countries: List[Dict[str, str]] = []
            for entry in raw_entries:
                name = str(entry.get("name", "")).strip()
                code = str(entry.get("Iso2") or entry.get("iso2") or "").strip()
                if not name or not code:
                    continue
                countries.append({"name": name, "code": code})
            if countries:
                countries.sort(key=lambda item: item["name"].lower())
                self._countries_source = "remote"
                self._country_name_by_code = {item["code"].upper(): item["name"] for item in countries}
                self._country_code_by_name = {item["name"].lower(): item["code"] for item in countries}
                LOGGER.debug("Loaded %d countries from CountriesNow", len(countries))
                return countries
        except Exception:  # pragma: no cover - gracefully fall back
            LOGGER.warning("Failed to load country list from CountriesNow", exc_info=True)
        return []

    def _load_countries_from_aladhan(self) -> List[Dict[str, str]]:
        try:
            response = requests.get(ALADHAN_COUNTRIES_URL, timeout=10)
            response.raise_for_status()
            payload = response.json()
            raw_countries = payload.get("data", [])
            countries: List[Dict[str, str]] = []
            for entry in raw_countries:
                name = str(entry.get("name", "")).strip()
                code = str(entry.get("iso2") or entry.get("code") or "").strip()
                if not name or not code:
                    continue
                countries.append({"name": name, "code": code})
            if countries:
                countries.sort(key=lambda item: item["name"].lower())
                self._countries_source = "remote"
                self._country_name_by_code = {item["code"].upper(): item["name"] for item in countries}
                self._country_code_by_name = {item["name"].lower(): item["code"] for item in countries}
                LOGGER.debug("Loaded %d countries from AlAdhan", len(countries))
                return countries
        except Exception:
            LOGGER.warning("Falling back to bundled country list", exc_info=True)
        return []

    def _load_cities_from_countriesnow(
        self,
        country_code: Optional[str],
        country_name: Optional[str],
    ) -> List[Dict[str, Any]]:
        request_country = None
        if country_name:
            request_country = country_name
        elif country_code:
            request_country = self._country_name_by_code.get(country_code.strip().upper())

        if not request_country:
            return []

        try:
            response = requests.post(
                COUNTRIESNOW_CITIES_URL,
                json={"country": request_country},
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("error"):
                return []
            raw_cities = payload.get("data", [])
            if not isinstance(raw_cities, list) or not raw_cities:
                return []

            fallback_entry = None
            normalized_code = (country_code or "").upper()
            normalized_name = (country_name or "").lower()
            if normalized_code and normalized_code in self._fallback_by_code:
                fallback_entry = self._fallback_by_code[normalized_code]
            elif normalized_name and normalized_name in self._fallback_by_name:
                fallback_entry = self._fallback_by_name[normalized_name]
            fallback_lookup = {}
            if fallback_entry:
                for city in fallback_entry.get("cities", []):
                    name = str(city.get("name", "")).lower()
                    if name:
                        fallback_lookup[name] = city

            seen = set()
            cities: List[Dict[str, Any]] = []
            for item in raw_cities:
                city_name = str(item).strip()
                if not city_name:
                    continue
                key = city_name.lower()
                if key in seen:
                    continue
                seen.add(key)
                fallback_city = fallback_lookup.get(key)
                lat = self._safe_float(fallback_city.get("latitude")) if fallback_city else None
                lon = self._safe_float(fallback_city.get("longitude")) if fallback_city else None
                cities.append({"name": city_name, "latitude": lat, "longitude": lon})

            cities.sort(key=lambda entry: entry["name"].lower())
            LOGGER.debug("Loaded %d cities for %s via CountriesNow", len(cities), request_country)
            return cities
        except Exception:  # pragma: no cover - continue to other strategies
            LOGGER.debug("CountriesNow city lookup failed for %s", request_country, exc_info=True)
        return []

    def _load_cities_from_aladhan(
        self,
        country_code: Optional[str],
        country_name: Optional[str],
    ) -> List[Dict[str, Any]]:
        query_candidates = [country_code, country_name]
        for query in query_candidates:
            if not query:
                continue
            try:
                response = requests.get(ALADHAN_CITIES_URL, params={"country": query}, timeout=10)
                response.raise_for_status()
                payload = response.json()
                raw_cities = payload.get("data", [])
                if isinstance(raw_cities, list) and raw_cities:
                    cities: List[Dict[str, Any]] = []
                    for entry in raw_cities:
                        if isinstance(entry, dict):
                            name = (
                                str(
                                    entry.get("name")
                                    or entry.get("city")
                                    or entry.get("city_name")
                                    or entry.get("englishName")
                                    or entry.get("state")
                                    or ""
                                ).strip()
                            )
                            if not name:
                                continue
                            cities.append(
                                {
                                    "name": name,
                                    "latitude": self._safe_float(entry.get("latitude")),
                                    "longitude": self._safe_float(entry.get("longitude")),
                                }
                            )
                        else:
                            name = str(entry).strip()
                            if name:
                                cities.append({"name": name})
                    cities.sort(key=lambda item: item["name"].lower())
                    LOGGER.debug("Loaded %d cities for %s via AlAdhan", len(cities), query)
                    return cities
            except Exception:  # pragma: no cover - continue through candidates and fall back
                LOGGER.debug("City lookup failed for %s", query, exc_info=True)
        return []

    def _load_fallback_catalog(self) -> List[Dict[str, Any]]:
        if not self._fallback_path.exists():
            LOGGER.debug("No fallback location catalog found at %s", self._fallback_path)
            return []
        try:
            with self._fallback_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            entries = payload.get("countries", [])
            sanitized: List[Dict[str, Any]] = []
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                name = entry.get("name")
                if not name:
                    continue
                code = entry.get("code") or name
                cities = [city for city in entry.get("cities", []) if isinstance(city, dict)]
                sanitized.append({"name": name, "code": code, "cities": cities})
            LOGGER.debug("Loaded %d fallback countries", len(sanitized))
            return sanitized
        except Exception:
            LOGGER.exception("Failed to load fallback location catalog")
            return []

    @staticmethod
    def _safe_float(value: Optional[Any]) -> Optional[float]:
        try:
            if value in (None, ""):
                return None
            return float(value)
        except (TypeError, ValueError):
            return None
