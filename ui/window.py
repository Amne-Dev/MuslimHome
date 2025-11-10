"""Main window for the prayer times application."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List, Optional

try:  # Prefer PyQt5, fall back to Qt for Python
    from PyQt5 import QtCore, QtGui, QtWidgets  # type: ignore
except Exception:  # pragma: no cover - fallback path
    try:
        from PySide2 import QtCore, QtGui, QtWidgets  # type: ignore
    except Exception:
        from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore

from prayer_times import PrayerInfo


class PrayerTimesWindow(QtWidgets.QMainWindow):
    """Main application window displaying prayer times and controls."""

    def __init__(self) -> None:
        super().__init__()
        self.translations: Dict[str, Any] = {}
        self.prayer_name_map: Dict[str, str] = {}
        self._is_rtl = False
        self._last_location: tuple[str, str] = ("", "")
        self._location_set = False
        self._hijri_display: str = ""
        self._gregorian_display: str = ""
        self._prayer_info: Dict[str, PrayerInfo] = {}
        self._active_prayer: Optional[str] = None

        self.setObjectName("PrayerWindow")
        self.setWindowTitle("Prayer Times")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.resize(500, 620)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        outer_layout = QtWidgets.QVBoxLayout(central)
        outer_layout.setContentsMargins(24, 24, 24, 24)
        outer_layout.setSpacing(20)

        self.location_label = QtWidgets.QLabel()
        self.location_label.setObjectName("locationLabel")
        location_font = QtGui.QFont()
        location_font.setPointSize(18)
        location_font.setBold(True)
        self.location_label.setFont(location_font)
        outer_layout.addWidget(self.location_label)

        self.date_label = QtWidgets.QLabel()
        self.date_label.setObjectName("dateLabel")
        self.date_label.setWordWrap(True)
        outer_layout.addWidget(self.date_label)

        self.hijri_label = QtWidgets.QLabel()
        self.hijri_label.setObjectName("hijriLabel")
        self.hijri_label.setWordWrap(True)
        outer_layout.addWidget(self.hijri_label)

        self.next_prayer_label = QtWidgets.QLabel()
        self.next_prayer_label.setObjectName("nextPrayerLabel")
        next_font = QtGui.QFont()
        next_font.setPointSize(12)
        next_font.setBold(True)
        self.next_prayer_label.setFont(next_font)
        self.next_prayer_label.setWordWrap(True)
        outer_layout.addWidget(self.next_prayer_label)

        self.prayer_container = QtWidgets.QWidget()
        self.prayer_container.setObjectName("prayerContainer")
        self.prayer_layout = QtWidgets.QGridLayout(self.prayer_container)
        self.prayer_layout.setContentsMargins(0, 0, 0, 0)
        self.prayer_layout.setHorizontalSpacing(16)
        self.prayer_layout.setVerticalSpacing(16)
        self.prayer_layout.setColumnStretch(0, 1)
        self.prayer_layout.setColumnStretch(1, 1)
        self.prayer_container.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        outer_layout.addWidget(self.prayer_container)

        button_row = QtWidgets.QHBoxLayout()
        button_row.setSpacing(12)

        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.refresh_button.setObjectName("PrimaryButton")
        button_row.addWidget(self.refresh_button)

        self.settings_button = QtWidgets.QPushButton("Settings")
        self.settings_button.setObjectName("SecondaryButton")
        button_row.addWidget(self.settings_button)

        self.language_button = QtWidgets.QPushButton("العربية")
        self.language_button.setObjectName("GhostButton")
        button_row.addWidget(self.language_button)

        button_row.addStretch()
        outer_layout.addLayout(button_row)

        self.status_label = QtWidgets.QLabel()
        self.status_label.setObjectName("statusLabel")
        self.status_label.setWordWrap(True)
        outer_layout.addWidget(self.status_label)

        outer_layout.addStretch()

        self.prayer_cards: Dict[str, Dict[str, Any]] = {}
        self._display_order: List[str] = []
        self._build_default_cards()

        self.refresh_button.clicked.connect(self._emit_refresh)  # type: ignore
        self.language_button.clicked.connect(self._emit_language_toggle)  # type: ignore
        self.settings_button.clicked.connect(self._emit_open_settings)  # type: ignore

        self._refresh_handler: Optional[Callable[[], None]] = None
        self._language_handler: Optional[Callable[[], None]] = None
        self._settings_handler: Optional[Callable[[], None]] = None

        self._apply_styles()

    # -- Event handler wiring -------------------------------------------------
    def on_refresh(self, handler: Callable[[], None]) -> None:
        self._refresh_handler = handler

    def on_language_toggle(self, handler: Callable[[], None]) -> None:
        self._language_handler = handler

    def on_settings_open(self, handler: Callable[[], None]) -> None:
        self._settings_handler = handler

    def _emit_refresh(self) -> None:
        if self._refresh_handler:
            self._refresh_handler()

    def _emit_language_toggle(self) -> None:
        if self._language_handler:
            self._language_handler()

    def _emit_open_settings(self) -> None:
        if self._settings_handler:
            self._settings_handler()

    # -- UI updates -----------------------------------------------------------
    def apply_translations(
        self,
        translations: Dict[str, Any],
        prayer_name_map: Dict[str, str],
        is_rtl: bool,
    ) -> None:
        self.translations = translations
        self.prayer_name_map = prayer_name_map

        self.setWindowTitle(translations.get("app_title", "Prayer Times"))
        self.refresh_button.setText(translations.get("refresh", "Refresh"))
        self.language_button.setText(translations.get("language_toggle", "Language"))
        self.settings_button.setText(translations.get("settings_button", "Settings"))

        if self._location_set:
            self.update_location(*self._last_location)
        else:
            self.location_label.setText(translations.get("location_label", "Location"))

        if self._gregorian_display:
            self.update_gregorian_date(self._gregorian_display)
        else:
            self.date_label.setText(translations.get("today_label", "Today"))

        if self._hijri_display:
            self.update_hijri_date(self._hijri_display)
        else:
            self.hijri_label.setText(translations.get("hijri_label", "Hijri Date"))

        self.next_prayer_label.setText(translations.get("next_prayer", "Next Prayer"))

        for name, card in self.prayer_cards.items():
            card["name"].setText(self.prayer_name_map.get(name, name))

        self._set_layout_direction(is_rtl)
        self._highlight_prayer(self._active_prayer)
        self._update_prayer_countdowns(None)

    def update_location(self, city: str, country: str) -> None:
        self._last_location = (city, country)
        self._location_set = bool(city or country)
        if city and country:
            text = f"{city}, {country}"
        else:
            text = city or country or ""
        label_text = self.translations.get("location_label", "Location")
        self.location_label.setText(f"{label_text}: {text}" if text else label_text)

    def update_hijri_date(self, hijri_date: str) -> None:
        self._hijri_display = hijri_date
        label = self.translations.get("hijri_label", "Hijri Date")
        self.hijri_label.setText(f"{label}: {hijri_date}")

    def update_gregorian_date(self, gregorian_date: str) -> None:
        self._gregorian_display = gregorian_date
        label = self.translations.get("today_label", "Today")
        self.date_label.setText(f"{label}: {gregorian_date}" if gregorian_date else label)

    def update_prayers(self, prayers: Iterable[PrayerInfo]) -> None:
        prayers_list = sorted(list(prayers), key=lambda info: info.time)
        self._prayer_info = {info.name: info for info in prayers_list}

        if prayers_list:
            order = [info.name for info in prayers_list]
            self._rebuild_prayer_layout(order)
            for info in prayers_list:
                card = self._ensure_prayer_card(info.name)
                localized_name = self.prayer_name_map.get(info.name, info.name)
                card["name"].setText(localized_name)
                card["time"].setText(info.time.strftime("%H:%M"))
        else:
            for card in self.prayer_cards.values():
                card["time"].setText("--:--")
                card["countdown"].clear()

        self._highlight_prayer(self._active_prayer)
        self._update_prayer_countdowns(None)

    def update_next_prayer(
        self,
        prayer_name: Optional[str],
        countdown_text: Optional[str],
        reference_time: Optional[datetime] = None,
    ) -> None:
        label = self.translations.get("next_prayer", "Next Prayer")
        if prayer_name and countdown_text:
            localized_name = self.prayer_name_map.get(prayer_name, prayer_name)
            until_text = self.translations.get("until", "in")
            self.next_prayer_label.setText(f"{label}: {localized_name} {until_text} {countdown_text}")
        else:
            self.next_prayer_label.setText(label)

        self._active_prayer = prayer_name
        self._highlight_prayer(prayer_name)
        self._update_prayer_countdowns(reference_time)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def _set_layout_direction(self, rtl: bool) -> None:
        if rtl == self._is_rtl:
            return
        direction = QtCore.Qt.RightToLeft if rtl else QtCore.Qt.LeftToRight
        self.setLayoutDirection(direction)
        self.prayer_container.setLayoutDirection(direction)
        self._is_rtl = rtl

    def _build_default_cards(self) -> None:
        for name in ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]:
            self._ensure_prayer_card(name)
        self._rebuild_prayer_layout(["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"])

    def _ensure_prayer_card(self, prayer_name: str) -> Dict[str, Any]:
        card = self.prayer_cards.get(prayer_name)
        if card is not None:
            return card

        frame = QtWidgets.QFrame()
        frame.setObjectName("prayerCard")
        frame.setProperty("state", "default")
        frame.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)

        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(6)

        name_label = QtWidgets.QLabel(prayer_name)
        name_label.setObjectName("prayerName")
        name_label.setProperty("active", False)

        time_label = QtWidgets.QLabel("--:--")
        time_label.setObjectName("prayerTime")

        countdown_label = QtWidgets.QLabel("")
        countdown_label.setObjectName("prayerCountdown")
        countdown_label.setWordWrap(True)

        layout.addWidget(name_label)
        layout.addWidget(time_label)
        layout.addWidget(countdown_label)
        layout.addStretch()

        card = {
            "frame": frame,
            "name": name_label,
            "time": time_label,
            "countdown": countdown_label,
        }
        self.prayer_cards[prayer_name] = card
        return card

    def _rebuild_prayer_layout(self, order: List[str]) -> None:
        self._display_order = order
        for index in reversed(range(self.prayer_layout.count())):
            item = self.prayer_layout.takeAt(index)
            widget = item.widget()
            if widget is not None:
                widget.setParent(self.prayer_container)

        for card in self.prayer_cards.values():
            card["frame"].hide()

        for idx, name in enumerate(order):
            card = self._ensure_prayer_card(name)
            card["frame"].show()
            row = idx // 2
            col = idx % 2
            self.prayer_layout.addWidget(card["frame"], row, col)

    def _highlight_prayer(self, prayer_name: Optional[str]) -> None:
        for name, card in self.prayer_cards.items():
            is_active = prayer_name == name
            frame = card["frame"]
            frame.setProperty("state", "active" if is_active else "default")
            frame.style().unpolish(frame)
            frame.style().polish(frame)

            name_label = card["name"]
            name_label.setProperty("active", is_active)
            name_label.style().unpolish(name_label)
            name_label.style().polish(name_label)

    def _update_prayer_countdowns(self, reference_time: Optional[datetime]) -> None:
        if not self._prayer_info:
            return

        if reference_time is None:
            sample = next(iter(self._prayer_info.values()), None)
            if sample is None:
                return
            tzinfo = sample.time.tzinfo
            reference_time = datetime.now(tz=tzinfo) if tzinfo else datetime.now()

        for name, card in self.prayer_cards.items():
            info = self._prayer_info.get(name)
            countdown_label: QtWidgets.QLabel = card["countdown"]
            if not info:
                countdown_label.clear()
                continue

            delta = info.time - reference_time
            seconds = int(delta.total_seconds())
            if seconds <= -60:
                countdown_label.setText(self.translations.get("prayer_passed", "Completed"))
            elif -60 < seconds < 60:
                countdown_label.setText(self.translations.get("prayer_now", "Now"))
            else:
                hours, remainder = divmod(seconds, 3600)
                minutes = remainder // 60
                hours = abs(hours)
                minutes = abs(minutes)
                if hours > 0:
                    chunk = f"{hours}h {minutes}m"
                else:
                    chunk = f"{minutes}m"
                prefix = self.translations.get("until", "in")
                countdown_label.setText(f"{prefix} {chunk}")

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                font-family: 'Ubuntu', 'Segoe UI', sans-serif;
            }

            #PrayerWindow {
                background-color: #f5f6fa;
            }

            QLabel#locationLabel {
                color: #0f172a;
            }

            QLabel#dateLabel, QLabel#hijriLabel, QLabel#statusLabel {
                color: #475569;
                font-size: 13px;
            }

            QLabel#nextPrayerLabel {
                color: #1e293b;
                font-size: 14px;
            }

            QPushButton#PrimaryButton {
                padding: 10px 20px;
                border-radius: 8px;
                background-color: #1d4ed8;
                color: #ffffff;
                font-weight: 600;
            }

            QPushButton#PrimaryButton:hover {
                background-color: #155bcb;
            }

            QPushButton#SecondaryButton {
                padding: 10px 20px;
                border-radius: 8px;
                border: 1px solid #cbd5e1;
                background-color: #ffffff;
                color: #1e293b;
                font-weight: 600;
            }

            QPushButton#SecondaryButton:hover {
                border-color: #94a3b8;
            }

            QPushButton#GhostButton {
                padding: 10px 18px;
                border-radius: 8px;
                border: none;
                background-color: transparent;
                color: #1e293b;
                font-weight: 600;
            }

            QPushButton#GhostButton:hover {
                background-color: #e2e8f0;
            }

            QFrame#prayerCard {
                background-color: #ffffff;
                border-radius: 16px;
                border: 1px solid #e2e8f0;
                padding: 18px;
            }

            QFrame#prayerCard[state="active"] {
                border-color: #1d4ed8;
                box-shadow: 0px 8px 20px rgba(37, 99, 235, 0.15);
            }

            QLabel#prayerName {
                font-size: 16px;
                font-weight: 600;
                color: #1e293b;
            }

            QLabel#prayerName[active="true"] {
                color: #1d4ed8;
            }

            QLabel#prayerTime {
                font-size: 32px;
                color: #0f172a;
                font-weight: 600;
            }

            QLabel#prayerCountdown {
                color: #475569;
                font-size: 12px;
            }
            """
        )
