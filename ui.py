"""PyQt5 GUI for the prayer times application.""""""PyQt5 GUI for the prayer times application."""

from __future__ import annotationsfrom __future__ import annotations



from datetime import datetimefrom datetime import datetime

from typing import Any, Callable, Dict, Iterable, List, Optionalfrom typing import Any, Callable, Dict, Iterable, List, Optional



# Try to import Qt bindings - prefer PyQt5, fall back to PySide2 or PySide6.# Try to import Qt bindings - prefer PyQt5, fall back to PySide2 or PySide6.

try:

    from PyQt5 import QtCore, QtGui, QtWidgets  # type: ignore    # -- Event handler wiring -------------------------------------------------

except Exception:    def on_refresh(self, handler: Callable[[], None]) -> None:

    try:        self._refresh_handler = handler

        from PySide2 import QtCore, QtGui, QtWidgets  # type: ignore

    except Exception:    def on_language_toggle(self, handler: Callable[[], None]) -> None:

        from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore        self._language_handler = handler



from prayer_times import PrayerInfo    def on_settings_open(self, handler: Callable[[], None]) -> None:

        self._settings_handler = handler



class PrayerTimesWindow(QtWidgets.QMainWindow):    def _emit_refresh(self) -> None:

    """Main application window displaying prayer times and controls."""        if self._refresh_handler:

            self._refresh_handler()

    def __init__(self) -> None:

        super().__init__()    def _emit_language_toggle(self) -> None:

        self.translations: Dict[str, Any] = {}        if self._language_handler:

        self.prayer_name_map: Dict[str, str] = {}            self._language_handler()

        self._is_rtl = False

        self._last_location: tuple[str, str] = ("", "")    def _emit_open_settings(self) -> None:

        self._location_set = False        if self._settings_handler:

        self._hijri_display: str = ""            self._settings_handler()

        self._gregorian_display: str = ""

        self._prayer_info: Dict[str, PrayerInfo] = {}    # -- UI updates -----------------------------------------------------------

        self._active_prayer: Optional[str] = None    def apply_translations(

        self,

        self.setObjectName("PrayerWindow")        translations: Dict[str, Any],

        self.setWindowTitle("Prayer Times")        prayer_name_map: Dict[str, str],

        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)        is_rtl: bool,

        self.resize(500, 620)    ) -> None:

        self.translations = translations

        central = QtWidgets.QWidget()        self.prayer_name_map = prayer_name_map

        self.setCentralWidget(central)

        self.setWindowTitle(translations.get("app_title", "Prayer Times"))

        outer_layout = QtWidgets.QVBoxLayout(central)        self.refresh_button.setText(translations.get("refresh", "Refresh"))

        outer_layout.setContentsMargins(24, 24, 24, 24)        self.language_button.setText(translations.get("language_toggle", "Language"))

        outer_layout.setSpacing(20)        self.settings_button.setText(translations.get("settings_button", "Settings"))



        self.location_label = QtWidgets.QLabel()        if self._location_set:

        self.location_label.setObjectName("locationLabel")            self.update_location(*self._last_location)

        font = QtGui.QFont()        else:

        font.setPointSize(18)            self.location_label.setText(translations.get("location_label", "Location"))

        font.setBold(True)

        self.location_label.setFont(font)        if self._gregorian_display:

        outer_layout.addWidget(self.location_label)            self.update_gregorian_date(self._gregorian_display)

        else:

        self.date_label = QtWidgets.QLabel()            self.date_label.setText(translations.get("today_label", "Today"))

        self.date_label.setObjectName("dateLabel")

        self.date_label.setWordWrap(True)        if self._hijri_display:

        outer_layout.addWidget(self.date_label)            self.update_hijri_date(self._hijri_display)

        else:

        self.hijri_label = QtWidgets.QLabel()            self.hijri_label.setText(translations.get("hijri_label", "Hijri Date"))

        self.hijri_label.setObjectName("hijriLabel")

        self.hijri_label.setWordWrap(True)        self.next_prayer_label.setText(translations.get("next_prayer", "Next Prayer"))

        outer_layout.addWidget(self.hijri_label)

        for name, card in self.prayer_cards.items():

        self.next_prayer_label = QtWidgets.QLabel()            card["name"].setText(self.prayer_name_map.get(name, name))

        self.next_prayer_label.setObjectName("nextPrayerLabel")

        next_font = QtGui.QFont()        self._set_layout_direction(is_rtl)

        next_font.setPointSize(12)        self._highlight_prayer(self._active_prayer)

        next_font.setBold(True)        self._update_prayer_countdowns(None)

        self.next_prayer_label.setFont(next_font)

        self.next_prayer_label.setWordWrap(True)    def update_location(self, city: str, country: str) -> None:

        outer_layout.addWidget(self.next_prayer_label)        self._last_location = (city, country)

        self._location_set = bool(city or country)

        self.prayer_container = QtWidgets.QWidget()        if city and country:

        self.prayer_container.setObjectName("prayerContainer")            text = f"{city}, {country}"

        self.prayer_layout = QtWidgets.QGridLayout(self.prayer_container)        else:

        self.prayer_layout.setContentsMargins(0, 0, 0, 0)            text = city or country or ""

        self.prayer_layout.setHorizontalSpacing(16)        label_text = self.translations.get("location_label", "Location")

        self.prayer_layout.setVerticalSpacing(16)        self.location_label.setText(f"{label_text}: {text}" if text else label_text)

        self.prayer_layout.setColumnStretch(0, 1)

        self.prayer_layout.setColumnStretch(1, 1)    def update_hijri_date(self, hijri_date: str) -> None:

        self.prayer_container.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)        self._hijri_display = hijri_date

        outer_layout.addWidget(self.prayer_container)        label = self.translations.get("hijri_label", "Hijri Date")

        self.hijri_label.setText(f"{label}: {hijri_date}")

        button_row = QtWidgets.QHBoxLayout()

        button_row.setSpacing(12)    def update_gregorian_date(self, gregorian_date: str) -> None:

        self._gregorian_display = gregorian_date

        self.refresh_button = QtWidgets.QPushButton("Refresh")        label = self.translations.get("today_label", "Today")

        self.refresh_button.setObjectName("PrimaryButton")        self.date_label.setText(f"{label}: {gregorian_date}" if gregorian_date else label)

        button_row.addWidget(self.refresh_button)

    def update_prayers(self, prayers: Iterable[PrayerInfo]) -> None:

        self.settings_button = QtWidgets.QPushButton("Settings")        prayers_list = sorted(list(prayers), key=lambda info: info.time)

        self.settings_button.setObjectName("SecondaryButton")        self._prayer_info = {info.name: info for info in prayers_list}

        button_row.addWidget(self.settings_button)

        if prayers_list:

        self.language_button = QtWidgets.QPushButton("العربية")            order = [info.name for info in prayers_list]

        self.language_button.setObjectName("GhostButton")            self._rebuild_prayer_layout(order)

        button_row.addWidget(self.language_button)            for info in prayers_list:

                card = self._ensure_prayer_card(info.name)

        button_row.addStretch()                localized_name = self.prayer_name_map.get(info.name, info.name)

        outer_layout.addLayout(button_row)                card["name"].setText(localized_name)

                card["time"].setText(info.time.strftime("%H:%M"))

        self.status_label = QtWidgets.QLabel()        else:

        self.status_label.setObjectName("statusLabel")            for card in self.prayer_cards.values():

        self.status_label.setWordWrap(True)                card["time"].setText("--:--")

        outer_layout.addWidget(self.status_label)                card["countdown"].clear()



        outer_layout.addStretch()        self._highlight_prayer(self._active_prayer)

        self._update_prayer_countdowns(None)

        self.prayer_cards: Dict[str, Dict[str, Any]] = {}

        self._display_order: List[str] = []    def update_next_prayer(

        self._build_default_cards()        self,

        prayer_name: Optional[str],

        self.refresh_button.clicked.connect(self._emit_refresh)  # type: ignore        countdown_text: Optional[str],

        self.language_button.clicked.connect(self._emit_language_toggle)  # type: ignore        reference_time: Optional[datetime] = None,

        self.settings_button.clicked.connect(self._emit_open_settings)  # type: ignore    ) -> None:

        label = self.translations.get("next_prayer", "Next Prayer")

        self._refresh_handler: Optional[Callable[[], None]] = None        if prayer_name and countdown_text:

        self._language_handler: Optional[Callable[[], None]] = None            localized_name = self.prayer_name_map.get(prayer_name, prayer_name)

        self._settings_handler: Optional[Callable[[], None]] = None            until_text = self.translations.get("until", "in")

            self.next_prayer_label.setText(f"{label}: {localized_name} {until_text} {countdown_text}")

        self._apply_styles()        else:

            self.next_prayer_label.setText(label)

    # -- Event handler wiring -------------------------------------------------

    def on_refresh(self, handler: Callable[[], None]) -> None:        self._active_prayer = prayer_name

        self._refresh_handler = handler        self._highlight_prayer(prayer_name)

        self._update_prayer_countdowns(reference_time)

    def on_language_toggle(self, handler: Callable[[], None]) -> None:

        self._language_handler = handler    def set_status(self, text: str) -> None:

        self.status_label.setText(text)

    def on_settings_open(self, handler: Callable[[], None]) -> None:

        self._settings_handler = handler    def _set_layout_direction(self, rtl: bool) -> None:

        if rtl == self._is_rtl:

    def _emit_refresh(self) -> None:            return

        if self._refresh_handler:        direction = QtCore.Qt.RightToLeft if rtl else QtCore.Qt.LeftToRight

            self._refresh_handler()        self.setLayoutDirection(direction)

        self.prayer_container.setLayoutDirection(direction)

    def _emit_language_toggle(self) -> None:        self._is_rtl = rtl

        if self._language_handler:

            self._language_handler()    def _build_default_cards(self) -> None:

        for name in ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]:

    def _emit_open_settings(self) -> None:            self._ensure_prayer_card(name)

        if self._settings_handler:        self._rebuild_prayer_layout(["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"])

            self._settings_handler()

    def _ensure_prayer_card(self, prayer_name: str) -> Dict[str, Any]:

    # -- UI updates -----------------------------------------------------------        card = self.prayer_cards.get(prayer_name)

    def apply_translations(        if card is not None:

        self,            return card

        translations: Dict[str, Any],

        prayer_name_map: Dict[str, str],        frame = QtWidgets.QFrame()

        is_rtl: bool,        frame.setObjectName("prayerCard")

    ) -> None:        frame.setProperty("state", "default")

        self.translations = translations        frame.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)

        self.prayer_name_map = prayer_name_map

        layout = QtWidgets.QVBoxLayout(frame)

        self.setWindowTitle(translations.get("app_title", "Prayer Times"))        layout.setContentsMargins(18, 18, 18, 18)

        self.refresh_button.setText(translations.get("refresh", "Refresh"))        layout.setSpacing(6)

        self.language_button.setText(translations.get("language_toggle", "Language"))

        self.settings_button.setText(translations.get("settings_button", "Settings"))        name_label = QtWidgets.QLabel(prayer_name)

        name_label.setObjectName("prayerName")

        if self._location_set:        name_label.setProperty("active", False)

            self.update_location(*self._last_location)

        else:        time_label = QtWidgets.QLabel("--:--")

            self.location_label.setText(translations.get("location_label", "Location"))        time_label.setObjectName("prayerTime")



        if self._gregorian_display:        countdown_label = QtWidgets.QLabel("")

            self.update_gregorian_date(self._gregorian_display)        countdown_label.setObjectName("prayerCountdown")

        else:        countdown_label.setWordWrap(True)

            self.date_label.setText(translations.get("today_label", "Today"))

        layout.addWidget(name_label)

        if self._hijri_display:        layout.addWidget(time_label)

            self.update_hijri_date(self._hijri_display)        layout.addWidget(countdown_label)

        else:        layout.addStretch()

            self.hijri_label.setText(translations.get("hijri_label", "Hijri Date"))

        card = {

        self.next_prayer_label.setText(translations.get("next_prayer", "Next Prayer"))            "frame": frame,

            "name": name_label,

        for name, card in self.prayer_cards.items():            "time": time_label,

            card["name"].setText(self.prayer_name_map.get(name, name))            "countdown": countdown_label,

        }

        self._set_layout_direction(is_rtl)        self.prayer_cards[prayer_name] = card

        self._highlight_prayer(self._active_prayer)        return card

        self._update_prayer_countdowns(None)

    def _rebuild_prayer_layout(self, order: list[str]) -> None:

    def update_location(self, city: str, country: str) -> None:        self._display_order = order

        self._last_location = (city, country)        for index in reversed(range(self.prayer_layout.count())):

        self._location_set = bool(city or country)            item = self.prayer_layout.takeAt(index)

        if city and country:            widget = item.widget()

            text = f"{city}, {country}"            if widget is not None:

        else:                widget.setParent(self.prayer_container)

            text = city or country or ""

        label_text = self.translations.get("location_label", "Location")        for card in self.prayer_cards.values():

        self.location_label.setText(f"{label_text}: {text}" if text else label_text)            card["frame"].hide()



    def update_hijri_date(self, hijri_date: str) -> None:        for idx, name in enumerate(order):

        self._hijri_display = hijri_date            card = self._ensure_prayer_card(name)

        label = self.translations.get("hijri_label", "Hijri Date")            card["frame"].show()

        self.hijri_label.setText(f"{label}: {hijri_date}")            row = idx // 2

            col = idx % 2

    def update_gregorian_date(self, gregorian_date: str) -> None:            self.prayer_layout.addWidget(card["frame"], row, col)

        self._gregorian_display = gregorian_date

        label = self.translations.get("today_label", "Today")    def _highlight_prayer(self, prayer_name: Optional[str]) -> None:

        self.date_label.setText(f"{label}: {gregorian_date}" if gregorian_date else label)        for name, card in self.prayer_cards.items():

            is_active = prayer_name == name

    def update_prayers(self, prayers: Iterable[PrayerInfo]) -> None:            frame = card["frame"]

        prayers_list = sorted(list(prayers), key=lambda info: info.time)            frame.setProperty("state", "active" if is_active else "default")

        self._prayer_info = {info.name: info for info in prayers_list}            frame.style().unpolish(frame)

            frame.style().polish(frame)

        if prayers_list:

            order = [info.name for info in prayers_list]            name_label = card["name"]

            self._rebuild_prayer_layout(order)            name_label.setProperty("active", is_active)

            for info in prayers_list:            name_label.style().unpolish(name_label)

                card = self._ensure_prayer_card(info.name)            name_label.style().polish(name_label)

                localized_name = self.prayer_name_map.get(info.name, info.name)

                card["name"].setText(localized_name)    def _update_prayer_countdowns(self, reference_time: Optional[datetime]) -> None:

                card["time"].setText(info.time.strftime("%H:%M"))        if not self._prayer_info:

        else:            return

            for card in self.prayer_cards.values():

                card["time"].setText("--:--")        if reference_time is None:

                card["countdown"].clear()            sample = next(iter(self._prayer_info.values()), None)

            if sample is None:

        self._highlight_prayer(self._active_prayer)                return

        self._update_prayer_countdowns(None)            tzinfo = sample.time.tzinfo

            reference_time = datetime.now(tz=tzinfo) if tzinfo else datetime.now()

    def update_next_prayer(

        self,        for name, card in self.prayer_cards.items():

        prayer_name: Optional[str],            info = self._prayer_info.get(name)

        countdown_text: Optional[str],            countdown_label: QtWidgets.QLabel = card["countdown"]

        reference_time: Optional[datetime] = None,            if not info:

    ) -> None:                countdown_label.clear()

        label = self.translations.get("next_prayer", "Next Prayer")                continue

        if prayer_name and countdown_text:

            localized_name = self.prayer_name_map.get(prayer_name, prayer_name)            delta = info.time - reference_time

            until_text = self.translations.get("until", "in")            seconds = int(delta.total_seconds())

            self.next_prayer_label.setText(f"{label}: {localized_name} {until_text} {countdown_text}")            if seconds <= -60:

        else:                countdown_label.setText(self.translations.get("prayer_passed", "Completed"))

            self.next_prayer_label.setText(label)            elif -60 < seconds < 60:

                countdown_label.setText(self.translations.get("prayer_now", "Now"))

        self._active_prayer = prayer_name            else:

        self._highlight_prayer(prayer_name)                hours, remainder = divmod(seconds, 3600)

        self._update_prayer_countdowns(reference_time)                minutes = remainder // 60

                hours = abs(hours)

    def set_status(self, text: str) -> None:                minutes = abs(minutes)

        self.status_label.setText(text)                if hours > 0:

                    chunk = f"{hours}h {minutes}m"

    def _set_layout_direction(self, rtl: bool) -> None:                else:

        if rtl == self._is_rtl:                    chunk = f"{minutes}m"

            return                prefix = self.translations.get("until", "in")

        direction = QtCore.Qt.RightToLeft if rtl else QtCore.Qt.LeftToRight                countdown_label.setText(f"{prefix} {chunk}")

        self.setLayoutDirection(direction)

        self.prayer_container.setLayoutDirection(direction)    def _apply_styles(self) -> None:

        self._is_rtl = rtl        self.setStyleSheet(

            """

    def _build_default_cards(self) -> None:            QWidget {

        for name in ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]:                font-family: 'Ubuntu', 'Segoe UI', sans-serif;

            self._ensure_prayer_card(name)            }

        self._rebuild_prayer_layout(["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"])

            #PrayerWindow {

    def _ensure_prayer_card(self, prayer_name: str) -> Dict[str, Any]:                background-color: #f5f6fa;

        card = self.prayer_cards.get(prayer_name)            }

        if card is not None:

            return card            QLabel#locationLabel {

                color: #0f172a;

        frame = QtWidgets.QFrame()            }

        frame.setObjectName("prayerCard")

        frame.setProperty("state", "default")            QLabel#dateLabel, QLabel#hijriLabel, QLabel#statusLabel {

        frame.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)                color: #475569;

                font-size: 13px;

        layout = QtWidgets.QVBoxLayout(frame)            }

        layout.setContentsMargins(18, 18, 18, 18)

        layout.setSpacing(6)            QLabel#nextPrayerLabel {

                color: #1e293b;

        name_label = QtWidgets.QLabel(prayer_name)                font-size: 14px;

        name_label.setObjectName("prayerName")            }

        name_label.setProperty("active", False)

            QFrame#prayerCard {

        time_label = QtWidgets.QLabel("--:--")                background-color: #ffffff;

        time_label.setObjectName("prayerTime")                border: 1px solid #d9e1ef;

                border-radius: 16px;

        countdown_label = QtWidgets.QLabel("")            }

        countdown_label.setObjectName("prayerCountdown")

        countdown_label.setWordWrap(True)            QFrame#prayerCard[state="active"] {

                border-color: #1d74f2;

        layout.addWidget(name_label)                background-color: #e8f1ff;

        layout.addWidget(time_label)            }

        layout.addWidget(countdown_label)

        layout.addStretch()            QLabel#prayerName {

                font-size: 16px;

        card = {                font-weight: 600;

            "frame": frame,                color: #1f2937;

            "name": name_label,            }

            "time": time_label,

            "countdown": countdown_label,            QLabel#prayerName[active="true"] {

        }                color: #1d4ed8;

        self.prayer_cards[prayer_name] = card            }

        return card

            QLabel#prayerTime {

    def _rebuild_prayer_layout(self, order: List[str]) -> None:                font-size: 26px;

        self._display_order = order                font-weight: 600;

        for index in reversed(range(self.prayer_layout.count())):                color: #0f172a;

            item = self.prayer_layout.takeAt(index)            }

            widget = item.widget()

            if widget is not None:            QLabel#prayerCountdown {

                widget.setParent(self.prayer_container)                font-size: 12px;

                color: #64748b;

        for card in self.prayer_cards.values():            }

            card["frame"].hide()

            QGroupBox {

        for idx, name in enumerate(order):                border: 1px solid #d9e1ef;

            card = self._ensure_prayer_card(name)                border-radius: 12px;

            card["frame"].show()                margin-top: 16px;

            row = idx // 2                padding: 16px;

            col = idx % 2                font-weight: 600;

            self.prayer_layout.addWidget(card["frame"], row, col)                color: #0f172a;

            }

    def _highlight_prayer(self, prayer_name: Optional[str]) -> None:

        for name, card in self.prayer_cards.items():            QGroupBox::title {

            is_active = prayer_name == name                subcontrol-origin: margin;

            frame = card["frame"]                left: 12px;

            frame.setProperty("state", "active" if is_active else "default")                padding: 0 6px;

            frame.style().unpolish(frame)                background-color: #f5f6fa;

            frame.style().polish(frame)                color: #0f172a;

                font-size: 14px;

            name_label = card["name"]                font-weight: 700;

            name_label.setProperty("active", is_active)            }

            name_label.style().unpolish(name_label)

            name_label.style().polish(name_label)            QLabel#settingsHint {

                color: #475569;

    def _update_prayer_countdowns(self, reference_time: Optional[datetime]) -> None:                font-size: 12px;

        if not self._prayer_info:            }

            return

            QComboBox, QLineEdit {

        if reference_time is None:                padding: 8px 10px;

            sample = next(iter(self._prayer_info.values()), None)                border-radius: 8px;

            if sample is None:                border: 1px solid #cbd5e1;

                return                background-color: #ffffff;

            tzinfo = sample.time.tzinfo                color: #0f172a;

            reference_time = datetime.now(tz=tzinfo) if tzinfo else datetime.now()            }



        for name, card in self.prayer_cards.items():            QComboBox:focus, QLineEdit:focus {

            info = self._prayer_info.get(name)                border-color: #1d74f2;

            countdown_label: QtWidgets.QLabel = card["countdown"]            }

            if not info:

                countdown_label.clear()            QCheckBox {

                continue                font-weight: 500;

                color: #1e293b;

            delta = info.time - reference_time            }

            seconds = int(delta.total_seconds())

            if seconds <= -60:            QPushButton#PrimaryButton {

                countdown_label.setText(self.translations.get("prayer_passed", "Completed"))                padding: 10px 20px;

            elif -60 < seconds < 60:                border-radius: 8px;

                countdown_label.setText(self.translations.get("prayer_now", "Now"))                background-color: #1d74f2;

            else:                color: #ffffff;

                hours, remainder = divmod(seconds, 3600)                font-weight: 600;

                minutes = remainder // 60            }

                hours = abs(hours)

                minutes = abs(minutes)            QPushButton#PrimaryButton:hover {

                if hours > 0:                background-color: #155bcb;

                    chunk = f"{hours}h {minutes}m"            }

                else:

                    chunk = f"{minutes}m"            QPushButton#SecondaryButton {

                prefix = self.translations.get("until", "in")                padding: 10px 20px;

                countdown_label.setText(f"{prefix} {chunk}")                border-radius: 8px;

                border: 1px solid #cbd5e1;

    def _apply_styles(self) -> None:                background-color: #ffffff;

        self.setStyleSheet(                color: #1e293b;

            """                font-weight: 600;

            QWidget {            }

                font-family: 'Ubuntu', 'Segoe UI', sans-serif;

            }            QPushButton#SecondaryButton:hover {

                border-color: #94a3b8;

            #PrayerWindow {            }

                background-color: #f5f6fa;

            }            QPushButton#GhostButton {

                padding: 10px 18px;

            QLabel#locationLabel {                border-radius: 8px;

                color: #0f172a;                border: none;

            }                background-color: transparent;

                color: #1e293b;

            QLabel#dateLabel, QLabel#hijriLabel, QLabel#statusLabel {                font-weight: 600;

                color: #475569;            }

                font-size: 13px;

            }            QPushButton#GhostButton:hover {

                background-color: #e2e8f0;

            QLabel#nextPrayerLabel {            }

                color: #1e293b;            """

                font-size: 14px;        )

            }



            QPushButton#PrimaryButton {class SettingsDialog(QtWidgets.QDialog):

                padding: 10px 20px;    """Dialog exposing configurable application preferences."""

                border-radius: 8px;

                background-color: #1d4ed8;    def __init__(

                color: #ffffff;        self,

                font-weight: 600;        parent: Optional[QtWidgets.QWidget],

            }        translations: Dict[str, Any],

        language_options: List[tuple[str, str]],

            QPushButton#PrimaryButton:hover {        initial: Dict[str, Any],

                background-color: #155bcb;        prayer_labels: Dict[str, str],

            }        locations: Iterable[Dict[str, Any]],

    ) -> None:

            QPushButton#SecondaryButton {        super().__init__(parent)

                padding: 10px 20px;        self.translations = translations

                border-radius: 8px;        self.setWindowTitle(translations.get("settings_title", "Settings"))

                border: 1px solid #cbd5e1;        self.setModal(True)

                background-color: #ffffff;        self.resize(420, 420)

                color: #1e293b;

                font-weight: 600;        self._locations = list(locations)

            }        self._placeholder_country = translations.get("select_country_placeholder", "Select country")

        self._placeholder_city = translations.get("select_city_placeholder", "Select city")

            QPushButton#SecondaryButton:hover {        initial_location = initial.get("location", {}) if isinstance(initial, dict) else {}

                border-color: #94a3b8;

            }        layout = QtWidgets.QVBoxLayout(self)

        layout.setContentsMargins(20, 20, 20, 20)

            QPushButton#GhostButton {        layout.setSpacing(16)

                padding: 10px 18px;

                border-radius: 8px;        general_group = QtWidgets.QGroupBox(translations.get("settings_general", "General"))

                border: none;        general_layout = QtWidgets.QVBoxLayout()

                background-color: transparent;

                color: #1e293b;        language_row = QtWidgets.QHBoxLayout()

                font-weight: 600;        language_label = QtWidgets.QLabel(translations.get("settings_language_label", "Language"))

            }        language_row.addWidget(language_label)

        language_row.addStretch()

            QPushButton#GhostButton:hover {        self.language_combo = QtWidgets.QComboBox()

                background-color: #e2e8f0;        for code, label in language_options:

            }            self.language_combo.addItem(label, code)

        current_language = str(initial.get("language", ""))

            QFrame#prayerCard {        index = max(0, self.language_combo.findData(current_language))

                background-color: #ffffff;        self.language_combo.setCurrentIndex(index)

                border-radius: 16px;        language_row.addWidget(self.language_combo)

                border: 1px solid #e2e8f0;        general_layout.addLayout(language_row)

                padding: 18px;

            }        self.auto_location_checkbox = QtWidgets.QCheckBox(

            translations.get("settings_auto_location", "Detect location automatically")

            QFrame#prayerCard[state="active"] {        )

                border-color: #1d4ed8;        self.auto_location_checkbox.setChecked(bool(initial.get("auto_location", True)))

                box-shadow: 0px 8px 20px rgba(37, 99, 235, 0.15);        general_layout.addWidget(self.auto_location_checkbox)

            }

        location_hint = QtWidgets.QLabel(translations.get("settings_location_hint", "Choose a city for manual mode."))

            QLabel#prayerName {        location_hint.setObjectName("settingsHint")

                font-size: 16px;        location_hint.setWordWrap(True)

                font-weight: 600;        general_layout.addWidget(location_hint)

                color: #1e293b;

            }        location_form = QtWidgets.QFormLayout()

        location_form.setLabelAlignment(QtCore.Qt.AlignLeft)

            QLabel#prayerName[active="true"] {

                color: #1d4ed8;        self.country_combo = QtWidgets.QComboBox()

            }        self.country_combo.setObjectName("settingsCountryCombo")

        self.country_combo.setEditable(False)

            QLabel#prayerTime {        self.country_combo.addItem(self._placeholder_country, None)

                font-size: 32px;        for country in self._locations:

                color: #0f172a;            self.country_combo.addItem(country.get("name", ""), country)

                font-weight: 600;

            }        self.city_combo = QtWidgets.QComboBox()

        self.city_combo.setObjectName("settingsCityCombo")

            QLabel#prayerCountdown {        self.city_combo.setEditable(False)

                color: #475569;        self.city_combo.addItem(self._placeholder_city, None)

                font-size: 12px;

            }        location_form.addRow(translations.get("country_prompt", "Country"), self.country_combo)

            """        location_form.addRow(translations.get("city_prompt", "City"), self.city_combo)

        )        general_layout.addLayout(location_form)



        self.launch_on_startup_checkbox = QtWidgets.QCheckBox(

class SettingsDialog(QtWidgets.QDialog):            translations.get("settings_launch_on_startup", "Launch on startup")

    """Dialog exposing configurable application preferences."""        )

        self.launch_on_startup_checkbox.setChecked(bool(initial.get("launch_on_startup", False)))

    def __init__(        general_layout.addWidget(self.launch_on_startup_checkbox)

        self,

        parent: Optional[QtWidgets.QWidget],        general_group.setLayout(general_layout)

        translations: Dict[str, Any],        layout.addWidget(general_group)

        language_options: List[tuple[str, str]],

        initial: Dict[str, Any],        audio_group = QtWidgets.QGroupBox(translations.get("settings_audio", "Adhan"))

        prayer_labels: Dict[str, str],        audio_layout = QtWidgets.QVBoxLayout()

        locations: Iterable[Dict[str, Any]],        hint = QtWidgets.QLabel(translations.get("settings_short_adhan_hint", "Play shorter Adhan for:"))

    ) -> None:        hint.setObjectName("settingsHint")

        super().__init__(parent)        hint.setWordWrap(True)

        self.translations = translations        audio_layout.addWidget(hint)

        self.setWindowTitle(translations.get("settings_title", "Settings"))

        self.setModal(True)        self.adhan_checkboxes: Dict[str, QtWidgets.QCheckBox] = {}

        self.resize(420, 440)        short_for = set(initial.get("use_short_for", []))

        for key in ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]:

        self._locations = list(locations)            label = prayer_labels.get(key, key)

        self._placeholder_country = translations.get("select_country_placeholder", "Select country")            checkbox = QtWidgets.QCheckBox(label)

        self._placeholder_city = translations.get("select_city_placeholder", "Select city")            checkbox.setChecked(key in short_for)

        initial_location = initial.get("location", {}) if isinstance(initial, dict) else {}            self.adhan_checkboxes[key] = checkbox

            audio_layout.addWidget(checkbox)

        layout = QtWidgets.QVBoxLayout(self)

        layout.setContentsMargins(20, 20, 20, 20)        audio_group.setLayout(audio_layout)

        layout.setSpacing(16)        layout.addWidget(audio_group)



        general_group = QtWidgets.QGroupBox(translations.get("settings_general", "General"))        buttons = QtWidgets.QDialogButtonBox()

        general_layout = QtWidgets.QVBoxLayout()        save_label = translations.get("save", "Save")

        cancel_label = translations.get("cancel", "Cancel")

        language_row = QtWidgets.QHBoxLayout()        self.save_button = buttons.addButton(save_label, QtWidgets.QDialogButtonBox.AcceptRole)

        language_label = QtWidgets.QLabel(translations.get("settings_language_label", "Language"))        self.cancel_button = buttons.addButton(cancel_label, QtWidgets.QDialogButtonBox.RejectRole)

        language_row.addWidget(language_label)        buttons.accepted.connect(self.accept)  # type: ignore

        language_row.addStretch()        buttons.rejected.connect(self.reject)  # type: ignore

        self.language_combo = QtWidgets.QComboBox()        layout.addWidget(buttons)

        for code, label in language_options:

            self.language_combo.addItem(label, code)        self.country_combo.currentIndexChanged.connect(self._on_country_changed)  # type: ignore

        current_language = str(initial.get("language", ""))        self.auto_location_checkbox.toggled.connect(self._toggle_manual_fields)  # type: ignore

        index = max(0, self.language_combo.findData(current_language))

        self.language_combo.setCurrentIndex(index)        self._apply_initial_selection(initial_location)

        language_row.addWidget(self.language_combo)        self._toggle_manual_fields(self.auto_location_checkbox.isChecked())

        general_layout.addLayout(language_row)

    def values(self) -> Dict[str, Any]:

        self.auto_location_checkbox = QtWidgets.QCheckBox(        return {

            translations.get("settings_auto_location", "Detect location automatically")            "language": self.language_combo.currentData(),

        )            "auto_location": self.auto_location_checkbox.isChecked(),

        self.auto_location_checkbox.setChecked(bool(initial.get("auto_location", True)))            "launch_on_startup": self.launch_on_startup_checkbox.isChecked(),

        general_layout.addWidget(self.auto_location_checkbox)            "use_short_for": [key for key, box in self.adhan_checkboxes.items() if box.isChecked()],

            "location": self._selected_location_payload(),

        location_form = QtWidgets.QFormLayout()        }

        location_form.setLabelAlignment(QtCore.Qt.AlignLeft)

    def _on_country_changed(self, index: int) -> None:

        self.country_combo = QtWidgets.QComboBox()        self._populate_cities(index)

        self.country_combo.setObjectName("settingsCountryCombo")

        self.country_combo.setEditable(False)    def _apply_initial_selection(self, initial: Dict[str, Any]) -> None:

        self.country_combo.addItem(self._placeholder_country, None)        desired_code = initial.get("country_code") or initial.get("country")

        for country in self._locations:        desired_city = initial.get("city")

            self.country_combo.addItem(country.get("name", ""), country)

        target_index = 0

        self.city_combo = QtWidgets.QComboBox()        if desired_code:

        self.city_combo.setObjectName("settingsCityCombo")            for idx in range(1, self.country_combo.count()):

        self.city_combo.setEditable(False)                country = self.country_combo.itemData(idx)

        self.city_combo.addItem(self._placeholder_city, None)                if not country:

                    continue

        location_form.addRow(translations.get("country_prompt", "Country"), self.country_combo)                if desired_code in (country.get("code"), country.get("name")):

        location_form.addRow(translations.get("city_prompt", "City"), self.city_combo)                    target_index = idx

        general_layout.addLayout(location_form)                    break

        self.country_combo.setCurrentIndex(target_index)

        self.launch_on_startup_checkbox = QtWidgets.QCheckBox(

            translations.get("settings_launch_on_startup", "Launch on startup")        self._populate_cities(target_index, desired_city)

        )

        self.launch_on_startup_checkbox.setChecked(bool(initial.get("launch_on_startup", False)))    def _populate_cities(self, index: int, desired_city: Optional[str] = None) -> None:

        general_layout.addWidget(self.launch_on_startup_checkbox)        country = self.country_combo.itemData(index)

        self.city_combo.blockSignals(True)

        general_group.setLayout(general_layout)        self.city_combo.clear()

        layout.addWidget(general_group)        self.city_combo.addItem(self._placeholder_city, None)



        audio_group = QtWidgets.QGroupBox(translations.get("settings_audio", "Adhan"))        if country and isinstance(country, dict):

        audio_layout = QtWidgets.QVBoxLayout()            for city in country.get("cities", []):

        hint = QtWidgets.QLabel(translations.get("settings_short_adhan_hint", "Play shorter Adhan for:"))                self.city_combo.addItem(city.get("name", ""), city)

        hint.setObjectName("settingsHint")            if desired_city:

        hint.setWordWrap(True)                for idx in range(1, self.city_combo.count()):

        audio_layout.addWidget(hint)                    city_data = self.city_combo.itemData(idx)

                    if city_data and city_data.get("name") == desired_city:

        self.adhan_checkboxes: Dict[str, QtWidgets.QCheckBox] = {}                        self.city_combo.setCurrentIndex(idx)

        short_for = set(initial.get("use_short_for", []))                        break

        for key in ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]:        else:

            label = prayer_labels.get(key, key)            self.city_combo.setCurrentIndex(0)

            checkbox = QtWidgets.QCheckBox(label)

            checkbox.setChecked(key in short_for)        self.city_combo.blockSignals(False)

            self.adhan_checkboxes[key] = checkbox

            audio_layout.addWidget(checkbox)    def _toggle_manual_fields(self, auto_detect: bool) -> None:

        self.country_combo.setEnabled(not auto_detect)

        audio_group.setLayout(audio_layout)        self.city_combo.setEnabled(not auto_detect)

        layout.addWidget(audio_group)

    def _selected_location_payload(self) -> Dict[str, Optional[str]]:

        buttons = QtWidgets.QDialogButtonBox()        country_data = self.country_combo.currentData()

        save_label = translations.get("save", "Save")        city_data = self.city_combo.currentData()

        cancel_label = translations.get("cancel", "Cancel")        return {

        self.save_button = buttons.addButton(save_label, QtWidgets.QDialogButtonBox.AcceptRole)            "country": country_data.get("name") if isinstance(country_data, dict) else None,

        self.cancel_button = buttons.addButton(cancel_label, QtWidgets.QDialogButtonBox.RejectRole)            "country_code": country_data.get("code") if isinstance(country_data, dict) else None,

        buttons.accepted.connect(self.accept)  # type: ignore            "city": city_data.get("name") if isinstance(city_data, dict) else None,

        buttons.rejected.connect(self.reject)  # type: ignore            "latitude": city_data.get("latitude") if isinstance(city_data, dict) else None,

        layout.addWidget(buttons)            "longitude": city_data.get("longitude") if isinstance(city_data, dict) else None,

        }

        self.country_combo.currentIndexChanged.connect(self._on_country_changed)  # type: ignore

        self.auto_location_checkbox.toggled.connect(self._toggle_manual_fields)  # type: ignore

class LocationDialog(QtWidgets.QDialog):

        self._apply_initial_selection(initial_location)    """Dialog allowing the user to configure location preferences."""

        self._toggle_manual_fields(self.auto_location_checkbox.isChecked())

    def __init__(

    def values(self) -> Dict[str, Any]:        self,

        return {        parent: Optional[QtWidgets.QWidget],

            "language": self.language_combo.currentData(),        translations: Dict[str, Any],

            "auto_location": self.auto_location_checkbox.isChecked(),        initial: Dict[str, Optional[str]],

            "launch_on_startup": self.launch_on_startup_checkbox.isChecked(),        locations: Iterable[Dict[str, Any]],

            "use_short_for": [key for key, box in self.adhan_checkboxes.items() if box.isChecked()],    ) -> None:

            "location": self._selected_location_payload(),        super().__init__(parent)

        }        self.translations = translations

        self._locations = list(locations)

    def _on_country_changed(self, index: int) -> None:        self.setWindowTitle(translations.get("manual_location", "Set Location"))

        self._populate_cities(index)

        layout = QtWidgets.QVBoxLayout(self)

    def _apply_initial_selection(self, initial: Dict[str, Any]) -> None:        layout.setContentsMargins(16, 16, 16, 16)

        desired_code = initial.get("country_code") or initial.get("country")        layout.setSpacing(12)

        desired_city = initial.get("city")

        self.auto_checkbox = QtWidgets.QCheckBox(translations.get("auto_location", "Detect location automatically"))

        target_index = 0        self.auto_checkbox.setChecked(bool(initial.get("auto_location", False)))

        if desired_code:        layout.addWidget(self.auto_checkbox)

            for idx in range(1, self.country_combo.count()):

                country = self.country_combo.itemData(idx)        form = QtWidgets.QFormLayout()

                if not country:        form.setLabelAlignment(QtCore.Qt.AlignRight)

                    continue

                if desired_code in (country.get("code"), country.get("name")):        self.country_combo = QtWidgets.QComboBox()

                    target_index = idx        self.country_combo.setObjectName("countryCombo")

                    break        self.country_combo.setEditable(False)

        self.country_combo.setCurrentIndex(target_index)        placeholder_country = translations.get("select_country_placeholder", "Select country")

        self._populate_cities(target_index, desired_city)        self.country_combo.addItem(placeholder_country, None)

        for country in self._locations:

    def _populate_cities(self, index: int, desired_city: Optional[str] = None) -> None:            self.country_combo.addItem(country.get("name", ""), country)

        country = self.country_combo.itemData(index)

        self.city_combo.blockSignals(True)        self.city_combo = QtWidgets.QComboBox()

        self.city_combo.clear()        self.city_combo.setObjectName("cityCombo")

        self.city_combo.addItem(self._placeholder_city, None)        self.city_combo.setEditable(False)

        placeholder_city = translations.get("select_city_placeholder", "Select city")

        if country and isinstance(country, dict):        self.city_combo.addItem(placeholder_city, None)

            for city in country.get("cities", []):

                self.city_combo.addItem(city.get("name", ""), city)        form.addRow(translations.get("country_prompt", "Country"), self.country_combo)

            if desired_city:        form.addRow(translations.get("city_prompt", "City"), self.city_combo)

                for idx in range(1, self.city_combo.count()):        layout.addLayout(form)

                    city_data = self.city_combo.itemData(idx)

                    if city_data and city_data.get("name") == desired_city:        buttons = QtWidgets.QDialogButtonBox()

                        self.city_combo.setCurrentIndex(idx)        buttons.addButton(translations.get("cancel", "Cancel"), QtWidgets.QDialogButtonBox.RejectRole)

                        break        buttons.addButton(translations.get("save", "Save"), QtWidgets.QDialogButtonBox.AcceptRole)

        else:        buttons.rejected.connect(self.reject)  # type: ignore

            self.city_combo.setCurrentIndex(0)        buttons.accepted.connect(self.accept)  # type: ignore

        layout.addWidget(buttons)

        self.city_combo.blockSignals(False)

        self.country_combo.currentIndexChanged.connect(self._populate_cities)  # type: ignore

    def _toggle_manual_fields(self, auto_detect: bool) -> None:        self.auto_checkbox.toggled.connect(self._toggle_manual_fields)  # type: ignore

        self.country_combo.setEnabled(not auto_detect)

        self.city_combo.setEnabled(not auto_detect)        self._apply_initial_selection(initial)

        self._toggle_manual_fields(self.auto_checkbox.isChecked())

    def _selected_location_payload(self) -> Dict[str, Optional[str]]:

        country_data = self.country_combo.currentData()    def _apply_initial_selection(self, initial: Dict[str, Optional[str]]) -> None:

        city_data = self.city_combo.currentData()        desired_code = initial.get("country_code") or initial.get("country")

        return {        desired_city = initial.get("city")

            "country": country_data.get("name") if isinstance(country_data, dict) else None,        if desired_code:

            "country_code": country_data.get("code") if isinstance(country_data, dict) else None,            index = 0

            "city": city_data.get("name") if isinstance(city_data, dict) else None,            for idx in range(1, self.country_combo.count()):

            "latitude": city_data.get("latitude") if isinstance(city_data, dict) else None,                country = self.country_combo.itemData(idx)

            "longitude": city_data.get("longitude") if isinstance(city_data, dict) else None,                if not country:

        }                    continue

                if desired_code in (country.get("code"), country.get("name")):
                    index = idx
                    break
            self.country_combo.setCurrentIndex(index)
        else:
            self.country_combo.setCurrentIndex(0)

        if desired_city:
            self._populate_cities(self.country_combo.currentIndex(), desired_city)
        else:
            self._populate_cities(self.country_combo.currentIndex())

    def _populate_cities(self, index: int, desired_city: Optional[str] = None) -> None:
        country = self.country_combo.itemData(index)
        placeholder_city = self.translations.get("select_city_placeholder", "Select city")
        self.city_combo.blockSignals(True)
        self.city_combo.clear()
        self.city_combo.addItem(placeholder_city, None)
        if country and isinstance(country, dict):
            cities = country.get("cities", [])
            for city in cities:
                self.city_combo.addItem(city.get("name", ""), city)
            if desired_city:
                for idx in range(1, self.city_combo.count()):
                    city_data = self.city_combo.itemData(idx)
                    if city_data and city_data.get("name") == desired_city:
                        self.city_combo.setCurrentIndex(idx)
                        break
        else:
            self.city_combo.setCurrentIndex(0)
        self.city_combo.blockSignals(False)

    def _toggle_manual_fields(self, auto_detect: bool) -> None:
        widgets = [self.country_combo, self.city_combo]
        for widget in widgets:
            widget.setEnabled(not auto_detect)

    def values(self) -> Dict[str, Optional[str]]:
        country_data = self.country_combo.currentData()
        city_data = self.city_combo.currentData()
        return {
            "auto_location": self.auto_checkbox.isChecked(),
            "country": country_data.get("name") if isinstance(country_data, dict) else None,
            "country_code": country_data.get("code") if isinstance(country_data, dict) else None,
            "city": city_data.get("name") if isinstance(city_data, dict) else None,
            "latitude": city_data.get("latitude") if isinstance(city_data, dict) else None,
            "longitude": city_data.get("longitude") if isinstance(city_data, dict) else None,
        }
