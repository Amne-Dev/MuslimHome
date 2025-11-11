"""Home page for the prayer times application."""
from __future__ import annotations

from typing import Dict, Optional

try:  # Prefer PyQt5 consistency
    from PyQt5 import QtCore, QtGui, QtWidgets  # type: ignore
except Exception:  # pragma: no cover - fallback
    try:
        from PySide2 import QtCore, QtGui, QtWidgets  # type: ignore
    except Exception:
        from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore

from weather import WeatherInfo


class HomePage(QtWidgets.QWidget):
    """Landing page showing the next prayer and current weather."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self._next_prayer_title_text = "Next Prayer"
        self._next_prayer_placeholder = "Prayer schedule unavailable."
        self._weather_title_text = "Current Weather"
        self._weather_placeholder = "Weather information currently unavailable."
        self._feels_like_label = "Feels like"
        self._humidity_label = "Humidity"
        self._wind_label = "Wind"

        self._has_prayer_data = False
        self._has_weather_data = False

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(16)

        self.next_prayer_card = QtWidgets.QFrame()
        self.next_prayer_card.setObjectName("homeCard")
        prayer_layout = QtWidgets.QVBoxLayout(self.next_prayer_card)
        prayer_layout.setContentsMargins(24, 24, 24, 24)
        prayer_layout.setSpacing(12)

        self.next_prayer_title = QtWidgets.QLabel(self._next_prayer_title_text)
        self.next_prayer_title.setObjectName("homeCardTitle")
        title_font = self.next_prayer_title.font()
        title_font.setPointSize(14)
        title_font.setBold(True)
        self.next_prayer_title.setFont(title_font)

        self.next_prayer_name = QtWidgets.QLabel(self._next_prayer_placeholder)
        self.next_prayer_name.setObjectName("homeCardPrimary")
        name_font = self.next_prayer_name.font()
        name_font.setPointSize(24)
        name_font.setBold(True)
        self.next_prayer_name.setFont(name_font)

        self.next_prayer_time = QtWidgets.QLabel("")
        self.next_prayer_time.setObjectName("homeCardSecondary")

        self.next_prayer_countdown = QtWidgets.QLabel("")
        self.next_prayer_countdown.setObjectName("homeCardCaption")

        prayer_layout.addWidget(self.next_prayer_title)
        prayer_layout.addWidget(self.next_prayer_name)
        prayer_layout.addWidget(self.next_prayer_time)
        prayer_layout.addWidget(self.next_prayer_countdown)
        prayer_layout.addStretch(1)

        self.weather_card = QtWidgets.QFrame()
        self.weather_card.setObjectName("homeCard")
        weather_layout = QtWidgets.QVBoxLayout(self.weather_card)
        weather_layout.setContentsMargins(24, 24, 24, 24)
        weather_layout.setSpacing(12)

        self.weather_title = QtWidgets.QLabel(self._weather_title_text)
        self.weather_title.setObjectName("homeCardTitle")
        self.weather_title.setFont(title_font)

        self.weather_temperature = QtWidgets.QLabel("--°C")
        self.weather_temperature.setObjectName("homeCardPrimary")
        self.weather_temperature.setFont(name_font)

        self.weather_conditions = QtWidgets.QLabel(self._weather_placeholder)
        self.weather_conditions.setObjectName("homeCardSecondary")
        self.weather_conditions.setWordWrap(True)

        self.weather_location = QtWidgets.QLabel("")
        self.weather_location.setObjectName("homeCardCaption")
        self.weather_location.setWordWrap(True)

        weather_layout.addWidget(self.weather_title)
        weather_layout.addWidget(self.weather_temperature)
        weather_layout.addWidget(self.weather_conditions)
        weather_layout.addWidget(self.weather_location)
        weather_layout.addStretch(1)

        layout.addWidget(self.next_prayer_card, 0, 0)
        layout.addWidget(self.weather_card, 0, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)

    def apply_translations(self, translations: Dict[str, str]) -> None:
        self._next_prayer_title_text = translations.get("home_next_prayer_title", "Next Prayer")
        self._next_prayer_placeholder = translations.get(
            "home_next_prayer_placeholder",
            "Prayer schedule unavailable.",
        )
        self._weather_title_text = translations.get("home_weather_title", "Current Weather")
        self._weather_placeholder = translations.get(
            "home_weather_placeholder",
            "Weather information currently unavailable.",
        )
        self._feels_like_label = translations.get("weather_feels_like", self._feels_like_label)
        self._humidity_label = translations.get("weather_humidity", self._humidity_label)
        self._wind_label = translations.get("weather_wind", self._wind_label)

        self.next_prayer_title.setText(self._next_prayer_title_text)
        if not self._has_prayer_data:
            self.next_prayer_name.setText(self._next_prayer_placeholder)
            self.next_prayer_time.clear()
            self.next_prayer_countdown.clear()

        self.weather_title.setText(self._weather_title_text)
        if not self._has_weather_data:
            self.weather_temperature.setText("--°C")
            self.weather_conditions.setText(self._weather_placeholder)
            self.weather_location.clear()

    def update_next_prayer(
        self,
        prayer_name: Optional[str],
        prayer_time_text: Optional[str],
        countdown_text: Optional[str],
    ) -> None:
        if prayer_name and prayer_time_text:
            self._has_prayer_data = True
            self.next_prayer_name.setText(prayer_name)
            self.next_prayer_time.setText(prayer_time_text)
            self.next_prayer_countdown.setText(countdown_text or "")
        else:
            self._has_prayer_data = False
            self.next_prayer_name.setText(self._next_prayer_placeholder)
            self.next_prayer_time.clear()
            self.next_prayer_countdown.clear()

    def update_weather(self, location_label: str, weather: Optional[WeatherInfo]) -> None:
        if weather is None:
            self._has_weather_data = False
            self.weather_temperature.setText("--°C")
            self.weather_conditions.setText(self._weather_placeholder)
            self.weather_location.setText(location_label)
            return

        self._has_weather_data = True
        self.weather_temperature.setText(f"{weather.temperature_c:.1f}°C")
        self.weather_conditions.setText(weather.conditions)

        details = []
        if weather.feels_like_c is not None:
            details.append(f"{self._feels_like_label} {weather.feels_like_c:.1f}°C")
        if weather.humidity is not None:
            details.append(f"{self._humidity_label} {weather.humidity}%")
        if weather.wind_speed_kmh is not None:
            details.append(f"{self._wind_label} {weather.wind_speed_kmh:.1f} km/h")
        self.weather_location.setText(" | ".join(details) if details else location_label)