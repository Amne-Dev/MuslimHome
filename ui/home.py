"""Home page for the prayer times application."""
from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional, Sequence, Tuple

try:  # Prefer PyQt5 consistency
    from PyQt5 import QtCore, QtGui, QtWidgets  # type: ignore
except Exception:  # pragma: no cover - fallback
    try:
        from PySide2 import QtCore, QtGui, QtWidgets  # type: ignore
    except Exception:
        from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore

from weather import WeatherInfo

PRAYER_ORDER = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]


class ProgressRing(QtWidgets.QWidget):
    """Simple ring indicator for prayer completion progress."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, color: QtGui.QColor | None = None) -> None:
        super().__init__(parent)
        self._progress = 0.0
        self._accent = color or QtGui.QColor("#15803d")
        self._background = QtGui.QColor(0, 0, 0, 25)
        self.setMinimumSize(120, 120)

    def set_progress(self, value: float) -> None:
        bounded = max(0.0, min(1.0, value))
        if abs(self._progress - bounded) < 0.001:
            return
        self._progress = bounded
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # pragma: no cover - UI painting
        rect = self.rect().adjusted(8, 8, -8, -8)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        pen = QtGui.QPen(self._background, 12)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)

        sweep = int(360 * 16 * self._progress)
        gradient = QtGui.QConicalGradient(rect.center(), -90)
        gradient.setColorAt(0.0, self._accent)
        gradient.setColorAt(1.0, self._accent.lighter(130))
        pen.setColor(QtGui.QColor(self._accent))
        pen.setBrush(gradient)
        painter.setPen(pen)
        painter.drawArc(rect, -90 * 16, -sweep)

        painter.end()


class HomePage(QtWidgets.QWidget):
    """Landing page showing inspiration, prayer progress, and weather."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self._next_prayer_title_text = "Next Prayer"
        self._next_prayer_placeholder = "Prayer schedule unavailable."
        self._weather_title_text = "Current Weather"
        self._weather_placeholder = "Weather information currently unavailable."
        self._inspiration_title = "Daily Inspiration"
        self._inspiration_placeholder = "A daily verse or hadith will appear here once available."
        self._copy_label = "Copy"
        self._share_label = "Share"
        self._progress_title = "Today's Prayers"
        self._progress_placeholder = "Prayer progress will appear once times are available."
        self._progress_summary_template = "{completed}/{total} completed"
        self._weekly_title = "Weekly Overview"
        self._weekly_placeholder = "Weekly timetable will appear once prayer times load."
        self._weekly_show_text = "Show timetable"
        self._weekly_hide_text = "Hide timetable"
        self._feels_like_label = "Feels like"
        self._humidity_label = "Humidity"
        self._wind_label = "Wind"

        self._has_prayer_data = False
        self._has_weather_data = False
        self._has_inspiration = False
        self._current_inspiration: Tuple[str, Optional[str]] = ("", None)

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(16)

        self.inspiration_card = QtWidgets.QFrame()
        self.inspiration_card.setObjectName("homeCard")
        inspiration_layout = QtWidgets.QVBoxLayout(self.inspiration_card)
        inspiration_layout.setContentsMargins(24, 24, 24, 24)
        inspiration_layout.setSpacing(12)

        self.inspiration_title = QtWidgets.QLabel(self._inspiration_title)
        self.inspiration_title.setObjectName("homeCardTitle")
        title_font = QtGui.QFont(self.inspiration_title.font())
        title_font.setPointSize(14)
        title_font.setBold(True)
        self.inspiration_title.setFont(title_font)

        self.inspiration_text = QtWidgets.QLabel(self._inspiration_placeholder)
        self.inspiration_text.setObjectName("homeInspirationText")
        self.inspiration_text.setWordWrap(True)

        self.inspiration_reference = QtWidgets.QLabel("")
        self.inspiration_reference.setObjectName("homeCardCaption")
        self.inspiration_reference.setWordWrap(True)

        action_row = QtWidgets.QHBoxLayout()
        action_row.setSpacing(12)
        action_row.addStretch(1)
        self.copy_button = QtWidgets.QPushButton(self._copy_label)
        self.copy_button.setObjectName("homeActionButton")
        self.copy_button.clicked.connect(self._copy_inspiration)  # type: ignore
        self.share_button = QtWidgets.QPushButton(self._share_label)
        self.share_button.setObjectName("homeActionButton")
        self.share_button.clicked.connect(self._share_inspiration)  # type: ignore
        action_row.addWidget(self.copy_button)
        action_row.addWidget(self.share_button)

        inspiration_layout.addWidget(self.inspiration_title)
        inspiration_layout.addWidget(self.inspiration_text)
        inspiration_layout.addWidget(self.inspiration_reference)
        inspiration_layout.addLayout(action_row)

        self.next_prayer_card = QtWidgets.QFrame()
        self.next_prayer_card.setObjectName("homeCard")
        prayer_layout = QtWidgets.QVBoxLayout(self.next_prayer_card)
        prayer_layout.setContentsMargins(24, 24, 24, 24)
        prayer_layout.setSpacing(12)

        self.next_prayer_title = QtWidgets.QLabel(self._next_prayer_title_text)
        self.next_prayer_title.setObjectName("homeCardTitle")
        self.next_prayer_title.setFont(title_font)

        self.next_prayer_name = QtWidgets.QLabel(self._next_prayer_placeholder)
        self.next_prayer_name.setObjectName("homeCardPrimary")
        name_font = QtGui.QFont(self.next_prayer_name.font())
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

        self.progress_card = QtWidgets.QFrame()
        self.progress_card.setObjectName("homeCard")
        progress_layout = QtWidgets.QVBoxLayout(self.progress_card)
        progress_layout.setContentsMargins(24, 24, 24, 24)
        progress_layout.setSpacing(12)

        self.progress_title = QtWidgets.QLabel(self._progress_title)
        self.progress_title.setObjectName("homeCardTitle")
        self.progress_title.setFont(title_font)

        ring_row = QtWidgets.QHBoxLayout()
        ring_row.setSpacing(18)
        self.progress_ring = ProgressRing(color=QtGui.QColor("#15803d"))
        ring_row.addWidget(self.progress_ring, 0, QtCore.Qt.AlignCenter)

        ring_caption_layout = QtWidgets.QVBoxLayout()
        ring_caption_layout.setSpacing(6)
        self.progress_summary = QtWidgets.QLabel(self._progress_placeholder)
        self.progress_summary.setObjectName("homeCardSecondary")
        self.progress_status = QtWidgets.QLabel("")
        self.progress_status.setObjectName("homeCardCaption")
        ring_caption_layout.addWidget(self.progress_summary)
        ring_caption_layout.addWidget(self.progress_status)
        ring_caption_layout.addStretch(1)
        ring_row.addLayout(ring_caption_layout)

        progress_layout.addWidget(self.progress_title)
        progress_layout.addLayout(ring_row)

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

        self.weekly_card = QtWidgets.QFrame()
        self.weekly_card.setObjectName("homeCard")
        weekly_layout = QtWidgets.QVBoxLayout(self.weekly_card)
        weekly_layout.setContentsMargins(24, 24, 24, 24)
        weekly_layout.setSpacing(12)

        header_row = QtWidgets.QHBoxLayout()
        header_row.setSpacing(12)
        self.weekly_title = QtWidgets.QLabel(self._weekly_title)
        self.weekly_title.setObjectName("homeCardTitle")
        self.weekly_title.setFont(title_font)
        header_row.addWidget(self.weekly_title)
        header_row.addStretch(1)
        self.weekly_toggle = QtWidgets.QToolButton()
        self.weekly_toggle.setObjectName("homeActionButton")
        self.weekly_toggle.setCheckable(True)
        self.weekly_toggle.setText(self._weekly_show_text)
        self.weekly_toggle.toggled.connect(self._toggle_weekly_body)  # type: ignore
        header_row.addWidget(self.weekly_toggle)
        weekly_layout.addLayout(header_row)

        self.weekly_body = QtWidgets.QFrame()
        self.weekly_body.setObjectName("weeklyBody")
        body_layout = QtWidgets.QVBoxLayout(self.weekly_body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(12)

        self.weekly_table = QtWidgets.QTableWidget(0, len(PRAYER_ORDER) + 1)
        self.weekly_table.setObjectName("weeklyTable")
        self.weekly_table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.weekly_table.setMaximumHeight(220)
        self.weekly_table.verticalHeader().setVisible(False)
        self.weekly_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.weekly_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.weekly_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.weekly_table.horizontalHeader().setStretchLastSection(True)
        body_layout.addWidget(self.weekly_table)

        self.weekly_placeholder_label = QtWidgets.QLabel(self._weekly_placeholder)
        self.weekly_placeholder_label.setObjectName("homeCardCaption")
        self.weekly_placeholder_label.setAlignment(QtCore.Qt.AlignCenter)
        body_layout.addWidget(self.weekly_placeholder_label)

        self.weekly_body.setVisible(False)
        weekly_layout.addWidget(self.weekly_body)

        layout.addWidget(self.inspiration_card, 0, 0, 1, 2)
        layout.addWidget(self.next_prayer_card, 1, 0)
        layout.addWidget(self.progress_card, 1, 1)
        layout.addWidget(self.weather_card, 2, 0)
        layout.addWidget(self.weekly_card, 2, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)

    def apply_translations(self, translations: Dict[str, str]) -> None:
        self._next_prayer_title_text = translations.get("home_next_prayer_title", self._next_prayer_title_text)
        self._next_prayer_placeholder = translations.get("home_next_prayer_placeholder", self._next_prayer_placeholder)
        self._weather_title_text = translations.get("home_weather_title", self._weather_title_text)
        self._weather_placeholder = translations.get("home_weather_placeholder", self._weather_placeholder)
        self._inspiration_title = translations.get("home_inspiration_title", self._inspiration_title)
        self._inspiration_placeholder = translations.get("home_inspiration_placeholder", self._inspiration_placeholder)
        self._copy_label = translations.get("home_inspiration_copy", self._copy_label)
        self._share_label = translations.get("home_inspiration_share", self._share_label)
        self._progress_title = translations.get("home_progress_title", self._progress_title)
        self._progress_placeholder = translations.get("home_progress_placeholder", self._progress_placeholder)
        self._progress_summary_template = translations.get("home_progress_summary", self._progress_summary_template)
        self._weekly_title = translations.get("home_weekly_title", self._weekly_title)
        self._weekly_placeholder = translations.get("home_weekly_placeholder", self._weekly_placeholder)
        self._weekly_show_text = translations.get("home_weekly_toggle_show", self._weekly_show_text)
        self._weekly_hide_text = translations.get("home_weekly_toggle_hide", self._weekly_hide_text)
        self._feels_like_label = translations.get("weather_feels_like", self._feels_like_label)
        self._humidity_label = translations.get("weather_humidity", self._humidity_label)
        self._wind_label = translations.get("weather_wind", self._wind_label)

        self.inspiration_title.setText(self._inspiration_title)
        if not self._has_inspiration:
            self.inspiration_text.setText(self._inspiration_placeholder)
            self.inspiration_reference.clear()
        self.copy_button.setText(self._copy_label)
        self.share_button.setText(self._share_label)

        self.next_prayer_title.setText(self._next_prayer_title_text)
        if not self._has_prayer_data:
            self.next_prayer_name.setText(self._next_prayer_placeholder)
            self.next_prayer_time.clear()
            self.next_prayer_countdown.clear()

        self.progress_title.setText(self._progress_title)
        if not self._has_prayer_data:
            self.progress_summary.setText(self._progress_placeholder)
            self.progress_status.clear()

        self.weather_title.setText(self._weather_title_text)
        if not self._has_weather_data:
            self.weather_temperature.setText("--°C")
            self.weather_conditions.setText(self._weather_placeholder)
            self.weather_location.clear()

        self.weekly_title.setText(self._weekly_title)
        self.weekly_placeholder_label.setText(self._weekly_placeholder)
        if self.weekly_toggle.isChecked():
            self.weekly_toggle.setText(self._weekly_hide_text)
        else:
            self.weekly_toggle.setText(self._weekly_show_text)

    def update_inspiration(self, text: Optional[str], reference: Optional[str]) -> None:
        trimmed = (text or "").strip()
        if not trimmed:
            self._has_inspiration = False
            self.inspiration_text.setText(self._inspiration_placeholder)
            self.inspiration_reference.clear()
            self._current_inspiration = ("", None)
            return
        self._has_inspiration = True
        self.inspiration_text.setText(trimmed)
        self.inspiration_reference.setText(reference or "")
        self._current_inspiration = (trimmed, reference or None)

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

    def update_progress(self, completed: int, total: int, recent_prayer: Optional[str]) -> None:
        if total <= 0:
            self._has_prayer_data = False
            self.progress_ring.set_progress(0.0)
            self.progress_summary.setText(self._progress_placeholder)
            self.progress_status.clear()
            return

        self._has_prayer_data = True
        ratio = completed / total
        self.progress_ring.set_progress(ratio)
        summary = self._progress_summary_template.format(completed=completed, total=total)
        self.progress_summary.setText(summary)
        self.progress_status.setText(recent_prayer or "")

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

    def update_weekly_schedule(
        self,
        days: Sequence[Tuple[date, Dict[str, str]]],
        prayer_name_map: Dict[str, str],
    ) -> None:
        if not days:
            self.weekly_table.setRowCount(0)
            self.weekly_placeholder_label.show()
            return

        headers = ["Day"] + [prayer_name_map.get(name, name) for name in PRAYER_ORDER]
        self.weekly_table.setColumnCount(len(headers))
        self.weekly_table.setHorizontalHeaderLabels(headers)
        self.weekly_table.setRowCount(len(days))

        for row, (day, timings) in enumerate(days):
            day_label = day.strftime("%a %d %b")
            item = QtWidgets.QTableWidgetItem(day_label)
            item.setFlags(QtCore.Qt.ItemIsEnabled)
            self.weekly_table.setItem(row, 0, item)
            for col, prayer in enumerate(PRAYER_ORDER, start=1):
                value = timings.get(prayer, "--:--")
                cell = QtWidgets.QTableWidgetItem(value)
                cell.setFlags(QtCore.Qt.ItemIsEnabled)
                self.weekly_table.setItem(row, col, cell)

        self.weekly_table.resizeColumnsToContents()
        self.weekly_placeholder_label.hide()

    def _copy_inspiration(self) -> None:
        text, reference = self._current_inspiration
        if not text:
            return
        combined = f"{text}"
        if reference:
            combined = f"{combined} — {reference}"
        QtWidgets.QApplication.clipboard().setText(combined)
        QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), self._copy_label)

    def _share_inspiration(self) -> None:
        text, reference = self._current_inspiration
        if not text:
            return
        share_body = text
        if reference:
            share_body = f"{share_body}\n\n{reference}"
        encoded = QtCore.QUrl.toPercentEncoding(share_body)
        encoded_str = bytes(encoded).decode("utf-8")
        subject = bytes(QtCore.QUrl.toPercentEncoding("Daily inspiration")).decode("utf-8")
        url = QtCore.QUrl(f"mailto:?subject={subject}&body={encoded_str}")
        QtGui.QDesktopServices.openUrl(url)

    def _toggle_weekly_body(self, checked: bool) -> None:
        self.weekly_body.setVisible(checked)
        self.weekly_toggle.setText(self._weekly_hide_text if checked else self._weekly_show_text)