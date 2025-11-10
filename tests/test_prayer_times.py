from datetime import date

import pytz
import responses

from prayer_times import (
    ALADHAN_TIMINGS_BY_CITY_URL,
    ALADHAN_TIMINGS_URL,
    LocationInfo,
    PrayerTimesService,
)


def build_payload(timezone: str, latitude: float, longitude: float) -> dict:
    return {
        "code": 200,
        "data": {
            "timings": {
                "Fajr": "05:10",
                "Dhuhr": "12:30",
                "Asr": "15:45",
                "Maghrib": "18:12",
                "Isha": "19:30",
            },
            "date": {
                "hijri": {
                    "day": "27",
                    "month": {"en": "Rabi al-Thani"},
                    "year": "1447",
                    "date": "27-04-1447",
                },
                "gregorian": {
                    "date": "09-11-2025",
                },
            },
            "meta": {
                "timezone": timezone,
                "latitude": latitude,
                "longitude": longitude,
            },
        },
    }


def test_fetch_prayer_times_with_coordinates():
    service = PrayerTimesService(method=3, school=0)
    location = LocationInfo(
        city="Tangier",
        country="MA",
        latitude=35.7673,
        longitude=-5.7998,
        timezone="Africa/Casablanca",
    )

    payload = build_payload("Africa/Casablanca", 35.7673, -5.7998)

    with responses.RequestsMock() as mock:
        mock.add(
            responses.GET,
            ALADHAN_TIMINGS_URL,
            json=payload,
            status=200,
        )
        prayer_day = service.fetch_prayer_times(location, target_date=date(2025, 11, 9))
        assert mock.calls[0].request.url.startswith(ALADHAN_TIMINGS_URL)
        call_count = len(mock.calls)
    assert call_count == 1

    assert len(prayer_day.prayers) == 5
    assert prayer_day.location.timezone == "Africa/Casablanca"
    assert prayer_day.hijri_date == "27 Rabi al-Thani 1447 AH"

    # Ensure times are localized
    fajr_time = prayer_day.prayers[0].time
    assert getattr(fajr_time.tzinfo, "zone", None) == "Africa/Casablanca"


def test_fetch_prayer_times_by_city_only():
    service = PrayerTimesService(method=3, school=0)
    location = LocationInfo(
        city="Casablanca",
        country="MA",
        latitude=None,
        longitude=None,
        timezone=None,
    )

    payload = build_payload("Africa/Casablanca", 33.5731, -7.5898)

    with responses.RequestsMock() as mock:
        mock.add(
            responses.GET,
            ALADHAN_TIMINGS_BY_CITY_URL,
            json=payload,
            status=200,
        )
        prayer_day = service.fetch_prayer_times(location)
        assert mock.calls[0].request.url.startswith(ALADHAN_TIMINGS_BY_CITY_URL)
        call_count = len(mock.calls)
    assert call_count == 1

    assert prayer_day.location.latitude == 33.5731
    assert prayer_day.location.longitude == -7.5898
    assert prayer_day.location.timezone == "Africa/Casablanca"
    assert prayer_day.prayers[-1].time.strftime("%H:%M") == "19:30"