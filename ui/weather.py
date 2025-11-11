"""Weather tab UI components."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple

try:  # Prefer PyQt5 for consistency with main window
    from PyQt5 import QtCore, QtWidgets, QtGui  # type: ignore
except Exception:  # pragma: no cover - fallback path
    try:
        from PySide2 import QtCore, QtWidgets, QtGui  # type: ignore
    except Exception:
        from PySide6 import QtCore, QtWidgets, QtGui  # type: ignore

from weather import DailyForecast, WeatherInfo


class WeatherTab(QtWidgets.QWidget):
    """Simple tab that displays current weather details."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self._default_heading = "Weather"
        self._unavailable_title = "Weather unavailable"
        self._unavailable_detail = "Unable to load weather for this location right now."
        self._observed_prefix = "Observed at"
        self._feels_like_label = "Feels like"
        self._humidity_label = "Humidity"
        self._wind_label = "Wind"
        self._metric_wind_unit = "km/h"
        self._imperial_wind_unit = "mph"
        self._has_weather_data = False
        self._forecast_title_text = "7-Day Forecast"
        self._forecast_placeholder_text = "Forecast unavailable."
        self._latest_forecast: List[DailyForecast] = []
        self._icon_cache: Dict[str, QtGui.QPixmap] = {}

        self._location_label = QtWidgets.QLabel(self._default_heading)
        font = self._location_label.font()
        font.setPointSize(16)
        font.setBold(True)
        self._location_label.setFont(font)

        self._conditions_label = QtWidgets.QLabel("Conditions unavailable")
        self._temperature_label = QtWidgets.QLabel("--°C")
        temp_font = self._temperature_label.font()
        temp_font.setPointSize(32)
        temp_font.setBold(True)
        self._temperature_label.setFont(temp_font)
        self._temperature_label.setAlignment(QtCore.Qt.AlignCenter)

        self._details = QtWidgets.QLabel("")
        self._details.setAlignment(QtCore.Qt.AlignCenter)
        self._details.setWordWrap(True)

        self._observed_at_label = QtWidgets.QLabel("")
        self._observed_at_label.setObjectName("observedAtLabel")
        self._observed_at_label.setAlignment(QtCore.Qt.AlignCenter)
        observed_font = self._observed_at_label.font()
        observed_font.setPointSize(9)
        self._observed_at_label.setFont(observed_font)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._location_label, alignment=QtCore.Qt.AlignHCenter)
        layout.addSpacing(12)
        layout.addWidget(self._temperature_label)
        layout.addWidget(self._conditions_label, alignment=QtCore.Qt.AlignHCenter)
        layout.addSpacing(12)
        layout.addWidget(self._details)
        layout.addSpacing(12)
        layout.addWidget(self._observed_at_label)
        layout.addSpacing(24)

        self._forecast_title_label = QtWidgets.QLabel(self._forecast_title_text)
        forecast_title_font = self._forecast_title_label.font()
        forecast_title_font.setPointSize(12)
        forecast_title_font.setBold(True)
        self._forecast_title_label.setFont(forecast_title_font)
        self._forecast_title_label.setObjectName("forecastTitle")
        layout.addWidget(self._forecast_title_label, alignment=QtCore.Qt.AlignLeft)

        self._forecast_area = QtWidgets.QScrollArea()
        self._forecast_area.setWidgetResizable(True)
        self._forecast_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self._forecast_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self._forecast_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        self._forecast_area.setObjectName("forecastArea")
        self._forecast_area.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding,
        )
        self._forecast_area.setMinimumHeight(320)
        self._forecast_area.setMaximumHeight(16777215)

        self._forecast_container = QtWidgets.QWidget()
        self._forecast_container.setObjectName("forecastContainer")
        self._forecast_layout = QtWidgets.QGridLayout(self._forecast_container)
        self._forecast_layout.setContentsMargins(0, 0, 0, 0)
        self._forecast_layout.setHorizontalSpacing(16)
        self._forecast_layout.setVerticalSpacing(16)
        self._forecast_area.setWidget(self._forecast_container)

        layout.addWidget(self._forecast_area, stretch=1)
        self.setLayout(layout)

        self._format_units = "metric"

    def set_units(self, units: str) -> None:
        """Set display units for temperature and wind speed."""
        self._format_units = units
        self._render_forecast()

    def apply_translations(self, translations: Dict[str, str]) -> None:
        default_heading = translations.get("weather_tab_title")
        if default_heading:
            self._default_heading = default_heading
            if not self._has_weather_data:
                self._location_label.setText(default_heading)

        self._unavailable_title = translations.get("weather_unavailable", self._unavailable_title)
        self._unavailable_detail = translations.get("weather_unavailable_detail", self._unavailable_detail)
        self._observed_prefix = translations.get("weather_observed_prefix", self._observed_prefix)
        self._feels_like_label = translations.get("weather_feels_like", self._feels_like_label)
        self._humidity_label = translations.get("weather_humidity", self._humidity_label)
        self._wind_label = translations.get("weather_wind", self._wind_label)
        self._metric_wind_unit = translations.get("weather_wind_unit_metric", self._metric_wind_unit)
        self._imperial_wind_unit = translations.get("weather_wind_unit_imperial", self._imperial_wind_unit)
        self._forecast_title_text = translations.get("weather_forecast_title", self._forecast_title_text)
        self._forecast_placeholder_text = translations.get(
            "weather_forecast_unavailable",
            self._forecast_placeholder_text,
        )
        self._forecast_title_label.setText(self._forecast_title_text)

        if not self._has_weather_data:
            self._conditions_label.setText(self._unavailable_title)
            self._details.setText(self._unavailable_detail)
            self._temperature_label.setText("--°")
            self._observed_at_label.setText("")
        self._render_forecast()

    def update_weather(self, location_label: str, weather: Optional[WeatherInfo]) -> None:
        heading = location_label or self._default_heading
        self._location_label.setText(heading)

        if weather is None:
            self._temperature_label.setText("--°")
            self._conditions_label.setText(self._unavailable_title)
            self._details.setText(self._unavailable_detail)
            self._observed_at_label.setText("")
            self._has_weather_data = False
            return

        self._has_weather_data = True

        if self._format_units == "imperial":
            temperature = weather.temperature_f
            feels_like = weather.feels_like_f
            suffix = "°F"
            wind_unit = self._imperial_wind_unit
            wind_speed = self._kmh_to_mph(weather.wind_speed_kmh) if weather.wind_speed_kmh is not None else None
        else:
            temperature = weather.temperature_c
            feels_like = weather.feels_like_c
            suffix = "°C"
            wind_unit = self._metric_wind_unit
            wind_speed = weather.wind_speed_kmh

        self._temperature_label.setText(f"{temperature:.1f}{suffix}")
        self._conditions_label.setText(weather.conditions)

        detail_parts: list[str] = []
        if feels_like is not None:
            detail_parts.append(f"{self._feels_like_label} {feels_like:.1f}{suffix}")
        if weather.humidity is not None:
            detail_parts.append(f"{self._humidity_label} {weather.humidity}%")
        if wind_speed is not None:
            detail_parts.append(f"{self._wind_label} {wind_speed:.1f} {wind_unit}")
        self._details.setText(" | ".join(detail_parts) if detail_parts else "")

        self._observed_at_label.setText(self._format_observation_time(weather.observation_time_utc))

    def update_forecast(self, forecast: Sequence[DailyForecast]) -> None:
        self._latest_forecast = list(forecast)
        self._render_forecast()

    @staticmethod
    def _kmh_to_mph(speed_kmh: Optional[float]) -> Optional[float]:
        if speed_kmh is None:
            return None
        return speed_kmh * 0.621371

    def _format_observation_time(self, observed_at: Optional[datetime]) -> str:
        if observed_at is None:
            return ""
        return f"{self._observed_prefix} {observed_at.strftime('%H:%M UTC')}"

    def _render_forecast(self) -> None:
        while self._forecast_layout.count():
            item = self._forecast_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not self._latest_forecast:
            placeholder = QtWidgets.QLabel(self._forecast_placeholder_text)
            placeholder.setObjectName("forecastPlaceholder")
            placeholder.setAlignment(QtCore.Qt.AlignCenter)
            placeholder.setWordWrap(True)
            self._forecast_layout.addWidget(placeholder, 0, 0)
            self._forecast_layout.setColumnStretch(0, 1)
            return

        max_columns = 2

        for index, entry in enumerate(self._latest_forecast[:7]):
            card = QtWidgets.QFrame()
            card.setObjectName("forecastCard")
            card_layout = QtWidgets.QVBoxLayout(card)
            card_layout.setContentsMargins(18, 18, 18, 18)
            card_layout.setSpacing(8)
            # increase card height for better readability
            card.setFixedHeight(200)
            card.setMinimumWidth(150)
            card.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

            icon_label = QtWidgets.QLabel()
            icon_label.setObjectName("forecastIcon")
            icon_label.setAlignment(QtCore.Qt.AlignCenter)
            icon_label.setFixedSize(64, 64)
            icon_label.setScaledContents(True)
            icon_pix = self._icon_for_weather_code(entry.weather_code)
            if icon_pix is not None:
                icon_label.setPixmap(icon_pix)

            day_label = QtWidgets.QLabel(self._format_forecast_date(entry.date))
            day_label.setObjectName("forecastDay")
            condition_label = QtWidgets.QLabel(entry.conditions)
            condition_label.setObjectName("forecastCondition")
            condition_label.setWordWrap(True)

            max_temp, min_temp, suffix = self._format_forecast_temperatures(entry)
            temp_label = QtWidgets.QLabel(f"{max_temp}{suffix} / {min_temp}{suffix}")
            temp_label.setObjectName("forecastTemps")

            card_layout.addWidget(icon_label)
            card_layout.addWidget(day_label)
            card_layout.addWidget(condition_label)
            card_layout.addWidget(temp_label)
            card_layout.addStretch(1)

            row = index // max_columns
            column = index % max_columns
            self._forecast_layout.addWidget(card, row, column)

        for column in range(max_columns):
            self._forecast_layout.setColumnStretch(column, 1)

    def _format_forecast_temperatures(self, entry: DailyForecast) -> Tuple[str, str, str]:
        if self._format_units == "imperial":
            return (
                f"{entry.max_temperature_f:.0f}",
                f"{entry.min_temperature_f:.0f}",
                "°F",
            )
        return (
            f"{entry.max_temperature_c:.0f}",
            f"{entry.min_temperature_c:.0f}",
            "°C",
        )

    @staticmethod
    def _format_forecast_date(date_obj: datetime) -> str:
        return date_obj.strftime("%a, %d %b")

    def _icon_for_weather_code(self, code: int) -> Optional[QtGui.QPixmap]:
        category = self._categorize_weather_code(code)
        if category is None:
            return None
        cached = self._icon_cache.get(category)
        if cached is not None:
            return cached
        pixmap = self._create_weather_icon(category)
        self._icon_cache[category] = pixmap
        return pixmap

    def _categorize_weather_code(self, code: int) -> Optional[str]:
        if code in (0, 1):
            return "sun"
        if code in (2, 3, 45, 48):
            return "cloud"
        if code in {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}:
            return "rain"
        if code in {71, 73, 75, 77, 85, 86}:
            return "snow"
        if code in {95, 96, 99}:
            return "storm"
        return "cloud"

    def _create_weather_icon(self, category: str) -> QtGui.QPixmap:
        # Render a glyph into a pixmap. Using font glyphs keeps icons crisp and
        # consistent with request to use a font for icons instead of detailed
        # painted shapes.
        size = QtCore.QSize(64, 64)
        pixmap = QtGui.QPixmap(size)
        pixmap.fill(QtCore.Qt.transparent)

        glyphs = {
            "sun": "\u2600",  # ☀
            "cloud": "\u2601",  # ☁
            "rain": "\U0001F327",  # 🌧
            "snow": "\u2744",  # ❄
            "storm": "\u26A1",  # ⚡
        }
        glyph = glyphs.get(category, "\u2601")

        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        color = QtGui.QColor("#15803d")
        painter.setPen(QtGui.QPen(color))
        font = QtGui.QFont("Segoe UI Emoji", 30)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), QtCore.Qt.AlignCenter, glyph)
        painter.end()
        return pixmap
