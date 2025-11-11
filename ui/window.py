"""Main window for the prayer times application."""
from __future__ import annotations

import textwrap
from datetime import datetime, date
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

ACCENT_COLOR_HEX = "#15803d"

try:  # Prefer PyQt5, fall back to Qt for Python
    from PyQt5 import QtCore, QtGui, QtWidgets  # type: ignore
except Exception:  # pragma: no cover - fallback path
    try:
        from PySide2 import QtCore, QtGui, QtWidgets  # type: ignore
    except Exception:
        from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore

from prayer_times import PrayerInfo
from weather import DailyForecast, WeatherInfo
from ui.home import HomePage
from ui.weather import WeatherTab
from ui.quran import QuranPage


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
        self._last_countdown_display: Optional[str] = None
        self._weekly_schedule: List[Tuple[date, Dict[str, str]]] = []

        self.setObjectName("PrayerWindow")
        self.setWindowTitle("Prayer Times")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.resize(1280, 720)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        root_layout = QtWidgets.QHBoxLayout(central)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(24)

        # navigation (placed on the left as a vertical rail)
        self._nav_group = QtWidgets.QButtonGroup(self)
        self._nav_group.setExclusive(True)
        self._nav_buttons: Dict[int, QtWidgets.QToolButton] = {}
        self._nav_items: Dict[int, tuple[str, str, str]] = {}
        self._accent_color = QtGui.QColor(ACCENT_COLOR_HEX)
        self._theme: str = "light"

        # main content container
        self.content_container = QtWidgets.QWidget()
        self.content_container.setObjectName("ContentContainer")
        content_layout = QtWidgets.QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)

        # pages stack
        self.page_stack = QtWidgets.QStackedWidget()
        content_layout.addWidget(self.page_stack, stretch=1)

        self.home_page = self._build_home_page()
        self.prayer_page = self._build_prayer_page()
        self.weather_tab = WeatherTab()
        self.quran_page = QuranPage()

        self.page_stack.addWidget(self.home_page)
        self.page_stack.addWidget(self.prayer_page)
        self.page_stack.addWidget(self.weather_tab)
        self.page_stack.addWidget(self.quran_page)
        self._set_active_page(0)

        self.status_label = QtWidgets.QLabel()
        self.status_label.setObjectName("statusLabel")
        self.status_label.setWordWrap(True)
        content_layout.addWidget(self.status_label)

        # prayer cards
        self.prayer_cards: Dict[str, Dict[str, Any]] = {}
        self._display_order: List[str] = []
        self._build_default_cards()

        # assemble layouts
        self.nav_bar = self._build_nav_bar()
        root_layout.addWidget(self.nav_bar, alignment=QtCore.Qt.AlignTop)
        root_layout.addWidget(self.content_container, stretch=1)

        # wiring
        self.refresh_button.clicked.connect(self._emit_refresh)  # type: ignore
        self.language_button.clicked.connect(self._emit_language_toggle)  # type: ignore
        self.settings_button.clicked.connect(self._emit_open_settings)  # type: ignore

        self._refresh_handler: Optional[Callable[[], None]] = None
        self._language_handler: Optional[Callable[[], None]] = None
        self._settings_handler: Optional[Callable[[], None]] = None

        self._bookmark_handler: Optional[Callable[[Optional[Dict[str, Any]]], None]] = None
        self._surah_handler: Optional[Callable[[int], None]] = None
        self._close_handler: Optional[Callable[[], bool]] = None

        self.quran_page.bookmark_changed.connect(self._emit_quran_bookmark)  # type: ignore
        self.quran_page.surah_selected.connect(self._emit_quran_surah_request)  # type: ignore

        self.apply_theme("light")

    # -- Builders -----------------------------------------------------------
    def _build_nav_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QFrame()
        bar.setObjectName("NavBar")
        bar.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
        bar.setFixedWidth(160)

        layout = QtWidgets.QVBoxLayout(bar)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)

        buttons = [
            (0, "nav_home", "Home", "home"),
            (1, "nav_prayers", "Prayers", "prayers"),
            (2, "nav_weather", "Weather", "weather"),
            (3, "nav_quran", "Qur'an", "quran"),
        ]

        for index, translation_key, fallback, kind in buttons:
            button = QtWidgets.QToolButton()
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
            button.setIconSize(QtCore.QSize(40, 40))
            button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
            button.setMinimumHeight(110)
            button.setObjectName("NavButton")
            button.setCursor(QtCore.Qt.PointingHandCursor)
            button.pressed.connect(lambda idx=index: self._set_active_page(idx))  # type: ignore

            self._nav_group.addButton(button, index)
            self._nav_buttons[index] = button
            self._nav_items[index] = (translation_key, fallback, kind)

            label = self.translations.get(translation_key, fallback)
            button.setText(label)

            icon = self._glyph_icon_for_nav(kind)
            if not icon.isNull():
                button.setIcon(icon)

            layout.addWidget(button)

        layout.addStretch(1)

        action_widget = QtWidgets.QWidget()
        action_widget.setObjectName("NavActions")
        action_layout = QtWidgets.QVBoxLayout(action_widget)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(12)

        self.refresh_button = QtWidgets.QPushButton()
        self.refresh_button.setObjectName("PrimaryButton")
        self.refresh_button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.refresh_button.setMinimumHeight(44)
        self.refresh_button.setCursor(QtCore.Qt.PointingHandCursor)
        refresh_icon = self._create_glyph_icon("\u21bb", QtGui.QColor("#ffffff"), 28)
        self.refresh_button.setIcon(refresh_icon)
        self.refresh_button.setIconSize(QtCore.QSize(28, 28))
        self.refresh_button.setText("")
        action_layout.addWidget(self.refresh_button)

        self.settings_button = QtWidgets.QPushButton()
        self.settings_button.setObjectName("SecondaryButton")
        self.settings_button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.settings_button.setMinimumHeight(44)
        self.settings_button.setCursor(QtCore.Qt.PointingHandCursor)
        settings_icon = self._create_glyph_icon("\u2699", self._accent_color, 26)
        self.settings_button.setIcon(settings_icon)
        self.settings_button.setIconSize(QtCore.QSize(26, 26))
        self.settings_button.setText("")
        action_layout.addWidget(self.settings_button)

        self.language_button = QtWidgets.QPushButton(
            self.translations.get("language_toggle", "Language")
        )
        self.language_button.setObjectName("GhostButton")
        self.language_button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.language_button.setMinimumHeight(44)
        self.language_button.setCursor(QtCore.Qt.PointingHandCursor)
        action_layout.addWidget(self.language_button)

        layout.addWidget(action_widget)
        self._update_action_icons()
        return bar

    # ------------------------------------------------------------------
    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # type: ignore[override]
        if self._close_handler is not None:
            try:
                should_close = self._close_handler()
            except Exception:
                should_close = True
            if not should_close:
                event.ignore()
                return
        super().closeEvent(event)

    def on_close_attempt(self, handler: Callable[[], bool]) -> None:
        self._close_handler = handler

    def _glyph_icon_for_nav(self, kind: str, color: Optional[QtGui.QColor] = None) -> QtGui.QIcon:
        glyphs = {"home": "\u2302", "prayers": "\u262a", "weather": "\u2601", "quran": "\U0001F4D6"}
        glyph = glyphs.get(kind, "")
        if not glyph:
            return QtGui.QIcon()

        size = QtCore.QSize(48, 48)
        pixmap = QtGui.QPixmap(size)
        pixmap.fill(QtCore.Qt.transparent)

        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtGui.QPen(color or self._accent_color))
        font = QtGui.QFont("Segoe UI Symbol", 28)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), QtCore.Qt.AlignCenter, glyph)
        painter.end()

        icon = QtGui.QIcon()
        icon.addPixmap(pixmap, QtGui.QIcon.Normal, QtGui.QIcon.Off)
        # make checked state white glyph on accent background by painting glyph white
        pixmap_on = QtGui.QPixmap(size)
        pixmap_on.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap_on)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(pixmap_on.rect(), self._accent_color)
        painter.setPen(QtGui.QPen(QtGui.QColor("#ffffff")))
        painter.setFont(font)
        painter.drawText(pixmap_on.rect(), QtCore.Qt.AlignCenter, glyph)
        painter.end()
        icon.addPixmap(pixmap_on, QtGui.QIcon.Normal, QtGui.QIcon.On)
        return icon

    def _create_glyph_icon(self, glyph: str, color: QtGui.QColor, size: int = 28) -> QtGui.QIcon:
        icon_size = max(size, 24)
        dimension = icon_size + 12
        pixmap = QtGui.QPixmap(dimension, dimension)
        pixmap.fill(QtCore.Qt.transparent)

        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtGui.QPen(color))
        font = QtGui.QFont("Segoe UI Symbol", icon_size)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), QtCore.Qt.AlignCenter, glyph)
        painter.end()

        icon = QtGui.QIcon()
        icon.addPixmap(pixmap)
        return icon

    def _build_home_page(self) -> HomePage:
        page = HomePage()
        page.setObjectName("HomePage")
        return page

    def _build_prayer_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        page.setObjectName("PrayerPage")

        outer_layout = QtWidgets.QVBoxLayout(page)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(16)

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

        hijri_card = QtWidgets.QFrame()
        hijri_card.setObjectName("hijriCard")
        hijri_layout = QtWidgets.QVBoxLayout(hijri_card)
        hijri_layout.setContentsMargins(18, 18, 18, 18)
        hijri_layout.setSpacing(6)

        self.hijri_title_label = QtWidgets.QLabel("Hijri Date")
        self.hijri_title_label.setObjectName("hijriTitle")
        title_font = self.hijri_title_label.font()
        title_font.setPointSize(12)
        title_font.setBold(True)
        self.hijri_title_label.setFont(title_font)

        self.hijri_label = QtWidgets.QLabel("--")
        self.hijri_label.setObjectName("hijriLabel")
        hijri_font = self.hijri_label.font()
        hijri_font.setPointSize(16)
        hijri_font.setBold(True)
        self.hijri_label.setFont(hijri_font)
        self.hijri_label.setWordWrap(True)

        hijri_layout.addWidget(self.hijri_title_label)
        hijri_layout.addWidget(self.hijri_label)
        outer_layout.addWidget(hijri_card)

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

        outer_layout.addStretch(1)
        return page

    def _set_active_page(self, index: int) -> None:
        self.page_stack.setCurrentIndex(index)
        QtWidgets.QApplication.processEvents(QtCore.QEventLoop.ExcludeUserInputEvents)
        button = self._nav_buttons.get(index)
        if button and not button.isChecked():
            button.setChecked(True)
        if self.page_stack.widget(index) is self.quran_page:
            self.quran_page.ensure_default_selection()

    # -- Event handler wiring -------------------------------------------------
    def on_refresh(self, handler: Callable[[], None]) -> None:
        self._refresh_handler = handler

    def on_language_toggle(self, handler: Callable[[], None]) -> None:
        self._language_handler = handler

    def on_settings_open(self, handler: Callable[[], None]) -> None:
        self._settings_handler = handler

    def on_quran_bookmark(self, handler: Callable[[Optional[Dict[str, Any]]], None]) -> None:
        self._bookmark_handler = handler

    def on_quran_surah_request(self, handler: Callable[[int], None]) -> None:
        self._surah_handler = handler

    def _emit_refresh(self) -> None:
        if self._refresh_handler:
            self._refresh_handler()

    def _emit_language_toggle(self) -> None:
        if self._language_handler:
            self._language_handler()

    def _emit_open_settings(self) -> None:
        if self._settings_handler:
            self._settings_handler()

    def _emit_quran_bookmark(self, bookmark: Optional[Dict[str, Any]]) -> None:
        if self._bookmark_handler:
            self._bookmark_handler(bookmark)

    def set_quran_bookmark(self, bookmark: Optional[Dict[str, Any]]) -> None:
        self.quran_page.set_bookmark(bookmark)

    def _emit_quran_surah_request(self, surah_number: int) -> None:
        if self._surah_handler:
            self._surah_handler(surah_number)

    def show_quran_loading(self, surah_number: int) -> None:
        self.quran_page.show_surah_loading(surah_number)

    def display_quran_text(self, surah_number: int, text: Optional[str], error: Optional[str] = None) -> None:
        self.quran_page.update_surah_text(surah_number, text, error)

    def update_inspiration(self, text: Optional[str], reference: Optional[str]) -> None:
        self.home_page.update_inspiration(text, reference)

    def update_weekly_schedule(self, schedule: Sequence[Tuple[date, Dict[str, str]]]) -> None:
        self._weekly_schedule = list(schedule)
        self.home_page.update_weekly_schedule(self._weekly_schedule, self.prayer_name_map)

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

        refresh_text = translations.get("refresh", "Refresh")
        self.refresh_button.setToolTip(refresh_text)
        self.refresh_button.setAccessibleName(refresh_text)
        self.refresh_button.setStatusTip(refresh_text)
        self.refresh_button.setText("")

        settings_text = translations.get("settings_button", "Settings")
        self.settings_button.setToolTip(settings_text)
        self.settings_button.setAccessibleName(settings_text)
        self.settings_button.setStatusTip(settings_text)
        self.settings_button.setText("")

        language_text = translations.get("language_toggle", "Language")
        self.language_button.setText(language_text)
        self.language_button.setToolTip(language_text)
        self.language_button.setAccessibleName(language_text)
        self.home_page.apply_translations(translations)
        self.weather_tab.apply_translations(translations)
        self.quran_page.apply_translations(translations)

        fallback_overrides = {
            1: translations.get("prayer_tab_title", "Prayers"),
            2: translations.get("weather_tab_title", "Weather"),
            3: translations.get("quran_tab_title", "Qur'an"),
        }
        for index, (translation_key, fallback, _) in self._nav_items.items():
            button = self._nav_buttons.get(index)
            if not button:
                continue
            default_text = fallback_overrides.get(index, fallback)
            button.setText(translations.get(translation_key, default_text))

        if self._location_set:
            self.update_location(*self._last_location)
        else:
            self.location_label.setText(translations.get("location_label", "Location"))

        if self._gregorian_display:
            self.update_gregorian_date(self._gregorian_display)
        else:
            self.date_label.setText(translations.get("today_label", "Today"))

        self.hijri_title_label.setText(translations.get("hijri_label", "Hijri Date"))
        if self._hijri_display:
            self.hijri_label.setText(self._hijri_display)
        else:
            self.hijri_label.setText("--")

        next_prayer_label = translations.get("next_prayer", "Next Prayer")
        if self._active_prayer and self._last_countdown_display is not None:
            self.update_next_prayer(self._active_prayer, self._last_countdown_display)
        else:
            self.next_prayer_label.setText(next_prayer_label)

        for name, card in self.prayer_cards.items():
            card["name"].setText(self.prayer_name_map.get(name, name))

        self._set_layout_direction(is_rtl)
        self._highlight_prayer(self._active_prayer)
        self._update_prayer_countdowns(None)
        self._refresh_prayer_progress(None)
        self.home_page.update_weekly_schedule(self._weekly_schedule, self.prayer_name_map)

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
        self.hijri_label.setText(hijri_date)

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
        self._refresh_prayer_progress(None)

    def update_next_prayer(
        self,
        prayer_name: Optional[str],
        countdown_text: Optional[str],
        reference_time: Optional[datetime] = None,
    ) -> None:
        label = self.translations.get("next_prayer", "Next Prayer")
        localized_name = self.prayer_name_map.get(prayer_name, prayer_name) if prayer_name else None
        if prayer_name and countdown_text:
            until_text = self.translations.get("until", "in")
            self.next_prayer_label.setText(f"{label}: {localized_name} {until_text} {countdown_text}")
        else:
            self.next_prayer_label.setText(label)

        self._last_countdown_display = countdown_text
        self._active_prayer = prayer_name
        self._highlight_prayer(prayer_name)
        self._update_prayer_countdowns(reference_time)
        self._refresh_prayer_progress(reference_time)

        prayer_time_text = None
        if prayer_name and prayer_name in self._prayer_info:
            prayer_time_text = self._prayer_info[prayer_name].time.strftime("%H:%M")

        self.home_page.update_next_prayer(localized_name, prayer_time_text, countdown_text)

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def update_weather(
        self,
        location_label: str,
        weather: Optional[WeatherInfo],
        forecast: Sequence[DailyForecast],
    ) -> None:
        self.weather_tab.update_weather(location_label, weather)
        self.weather_tab.update_forecast(forecast)
        self.home_page.update_weather(location_label, weather)

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

    def _compute_prayer_progress(
        self,
        reference_time: Optional[datetime],
    ) -> Tuple[int, int, Optional[str]]:
        if not self._prayer_info:
            return 0, 0, None

        ordered = sorted(self._prayer_info.values(), key=lambda info: info.time)
        tzinfo = ordered[0].time.tzinfo
        if reference_time is None:
            reference_time = datetime.now(tz=tzinfo) if tzinfo else datetime.now()

        completed = [info for info in ordered if info.time <= reference_time]
        total = len(ordered)
        last_label: Optional[str] = None
        if completed:
            last_name = completed[-1].name
            last_label = self.prayer_name_map.get(last_name, last_name)
        return len(completed), total, last_label

    def _refresh_prayer_progress(self, reference_time: Optional[datetime]) -> None:
        completed, total, last_label = self._compute_prayer_progress(reference_time)
        status_text = ""
        if last_label and completed:
            status_text = f"{self.translations.get('prayer_passed', 'Completed')}: {last_label}"
        self.home_page.update_progress(completed, total, status_text or None)

    def apply_theme(self, theme: str) -> None:
        """Apply the selected theme stylesheet and refresh glyph colors."""
        if theme not in {"light", "dark"}:
            theme = "light"
        self._theme = theme
        self.setStyleSheet(self._stylesheet_for_theme(theme))
        self._update_action_icons()
        self.quran_page.refresh_reader_styles()

    def _update_action_icons(self) -> None:
        """Refresh action button glyphs so they stay legible per theme."""
        if not hasattr(self, "refresh_button"):
            return

        nav_color = self._accent_color if self._theme == "light" else QtGui.QColor("#38d0a5")
        for index, button in self._nav_buttons.items():
            _, _, kind = self._nav_items.get(index, ("", "", ""))
            if not kind:
                continue
            button.setIcon(self._glyph_icon_for_nav(kind, nav_color))

        refresh_color = QtGui.QColor("#ffffff") if self._theme == "light" else QtGui.QColor("#f1f5ff")
        self.refresh_button.setIcon(self._create_glyph_icon("\u21bb", refresh_color, 28))

        settings_color = self._accent_color if self._theme == "light" else QtGui.QColor("#38d0a5")
        self.settings_button.setIcon(self._create_glyph_icon("\u2699", settings_color, 26))

    def _stylesheet_for_theme(self, theme: str) -> str:
        if theme == "dark":
            return textwrap.dedent(
                """
                QWidget {
                    font-family: 'Ubuntu', 'Segoe UI', sans-serif;
                    color: #f1f5ff;
                }

                #PrayerWindow {
                    background-color: #0b1628;
                    background-image: radial-gradient(circle at 15% 20%, rgba(56, 208, 165, 0.08), transparent 55%),
                                      radial-gradient(circle at 85% 10%, rgba(37, 99, 235, 0.12), transparent 65%);
                }

                #NavBar {
                    background-color: #111d33;
                    border-radius: 24px;
                    border: 1px solid #1f2f46;
                    padding: 16px 12px;
                    box-shadow: 0 18px 32px rgba(9, 16, 32, 0.55);
                }

                QWidget#NavActions {
                    border-top: 1px solid #1f2f46;
                    margin-top: 12px;
                    padding-top: 16px;
                }

                QToolButton#NavButton {
                    color: #f1f5ff;
                    font-weight: 600;
                    padding: 12px 6px;
                    margin: 4px 0;
                    border-radius: 16px;
                    background-color: transparent;
                }

                QToolButton#NavButton:hover {
                    background-color: #1b2d4a;
                }

                QToolButton#NavButton:checked {
                    background-color: #15803d;
                    color: #ffffff;
                    border: none;
                }

                QLabel#locationLabel {
                    color: #f8fafc;
                }

                QLabel#dateLabel, QLabel#hijriLabel, QLabel#statusLabel, QLabel#observedAtLabel {
                    color: #b7c3df;
                    font-size: 13px;
                }

                QLabel#nextPrayerLabel {
                    color: #d7fee4;
                    font-size: 14px;
                }

                QFrame#homeCard {
                    background-color: #13243d;
                    border-radius: 20px;
                    border: 1px solid #1f3452;
                    box-shadow: 0 20px 40px rgba(9, 16, 32, 0.45);
                }

                QLabel#homeInspirationText {
                    color: #f8fafc;
                    font-size: 16px;
                    line-height: 1.7;
                }

                QPushButton#homeActionButton,
                QToolButton#homeActionButton {
                    padding: 8px 18px;
                    border-radius: 10px;
                    border: 1px solid #1f3452;
                    background-color: #13243d;
                    color: #d7fee4;
                    font-weight: 600;
                }

                QPushButton#homeActionButton:hover,
                QToolButton#homeActionButton:hover {
                    border-color: #38d0a5;
                    background-color: #1b2d4a;
                }

                QToolButton#homeActionButton:checked {
                    background-color: #15803d;
                    border-color: #15803d;
                    color: #ffffff;
                }

                QFrame#weeklyBody {
                    border-top: 1px solid #1f3452;
                    padding-top: 12px;
                }

                QTableWidget#weeklyTable {
                    background-color: #0f1d32;
                    border: 1px solid #1f3452;
                    border-radius: 12px;
                    color: #f1f5ff;
                    gridline-color: rgba(56, 208, 165, 0.35);
                }

                QTableWidget#weeklyTable::item {
                    padding: 6px;
                }

                QTableWidget#weeklyTable QHeaderView::section {
                    background-color: #13243d;
                    color: #d7fee4;
                    border: none;
                    padding: 6px;
                }

                QLabel#homeCardTitle {
                    color: #38d0a5;
                    font-size: 15px;
                    font-weight: 600;
                }

                QLabel#homeCardPrimary {
                    color: #f8fafc;
                    font-size: 28px;
                    font-weight: 700;
                }

                QLabel#homeCardSecondary {
                    color: #d7fee4;
                    font-size: 16px;
                    font-weight: 600;
                }

                QLabel#homeCardCaption {
                    color: #a9b7d6;
                    font-size: 12px;
                }

                QPushButton#PrimaryButton {
                    padding: 10px 20px;
                    border-radius: 8px;
                    background-color: #15803d;
                    color: #f8fafc;
                    font-weight: 600;
                }

                QPushButton#PrimaryButton:hover {
                    background-color: #166534;
                }

                QPushButton#SecondaryButton {
                    padding: 10px 20px;
                    border-radius: 8px;
                    border: 1px solid #1f3452;
                    background-color: #1b2d4a;
                    color: #f1f5ff;
                    font-weight: 600;
                }

                QPushButton#SecondaryButton:hover {
                    border-color: #38d0a5;
                }

                QPushButton#GhostButton {
                    padding: 10px 18px;
                    border-radius: 8px;
                    border: none;
                    background-color: transparent;
                    color: #f1f5ff;
                    font-weight: 600;
                }

                QPushButton#GhostButton:hover {
                    background-color: #1b2d4a;
                }

                QFrame#hijriCard {
                    background-color: #13243d;
                    border-radius: 16px;
                    border: 1px solid #1f3452;
                    padding: 18px;
                }

                QLabel#hijriTitle {
                    color: #22c55e;
                    font-size: 13px;
                    font-weight: 600;
                }

                QLabel#hijriLabel {
                    color: #f8fafc;
                    font-size: 20px;
                    font-weight: 600;
                }

                QFrame#prayerCard {
                    background-color: #13243d;
                    border-radius: 16px;
                    border: 1px solid #1f3452;
                    padding: 18px;
                    box-shadow: 0 18px 28px rgba(9, 16, 32, 0.35);
                }

                QFrame#prayerCard[state="active"] {
                    border-color: #15803d;
                    box-shadow: 0px 8px 18px rgba(56, 208, 165, 0.55);
                }

                QLabel#prayerName {
                    font-size: 16px;
                    font-weight: 600;
                    color: #f1f5ff;
                }

                QLabel#prayerName[active="true"] {
                    color: #d7fee4;
                }

                QLabel#prayerTime {
                    font-size: 32px;
                    color: #f8fafc;
                    font-weight: 600;
                }

                QLabel#prayerCountdown {
                    color: #a9b7d6;
                    font-size: 12px;
                }

                QScrollArea#forecastArea {
                    background-color: transparent;
                    border: none;
                }

                QWidget#forecastContainer {
                    background-color: transparent;
                }

                QFrame#forecastCard {
                    background-color: #13243d;
                    border-radius: 20px;
                    border: 1px solid #1f3452;
                }

                QFrame#forecastCard:hover {
                    border-color: #38d0a5;
                    box-shadow: 0px 8px 18px rgba(56, 208, 165, 0.55);
                }

                QLabel#forecastIcon {
                    background-color: #1b2d4a;
                    border-radius: 24px;
                    padding: 8px;
                }

                QLabel#forecastDay {
                    color: #d7fee4;
                    font-size: 14px;
                    font-weight: 600;
                }

                QLabel#forecastCondition {
                    color: #b7c3df;
                    font-size: 12px;
                }

                QLabel#forecastTemps {
                    color: #f8fafc;
                    font-size: 16px;
                    font-weight: 600;
                }

                QLabel#forecastTitle {
                    color: #f1f5ff;
                    font-size: 15px;
                    font-weight: 600;
                }

                QLabel#forecastPlaceholder {
                    color: #b7c3df;
                    padding: 24px;
                }

                QFrame#quranCard {
                    background-color: #13243d;
                    border-radius: 20px;
                    border: 1px solid #1f3452;
                }

                QWidget#quranReader {
                    background-color: #0f1d32;
                    border-radius: 20px;
                    border: 1px solid #1f3452;
                }

                QListWidget#quranList {
                    background-color: #0f1d32;
                    border: 1px solid #1f3452;
                    border-radius: 12px;
                    padding: 8px;
                    color: #f1f5ff;
                }

                QListWidget#quranList::item:selected {
                    background-color: #15803d;
                    color: #ffffff;
                }

                QListWidget#quranList::item:hover {
                    background-color: #223759;
                }

                QLabel#quranHeader {
                    color: #f8fafc;
                }

                QLabel#quranReadingTitle {
                    color: #f8fafc;
                }

                QLabel#quranStatusLabel {
                    color: #b7c3df;
                }

                QLabel#quranAyahLabel {
                    color: #f1f5ff;
                    font-weight: 600;
                }

                QPushButton#quranBackButton {
                    padding: 8px 16px;
                    border-radius: 10px;
                    border: 1px solid #1f3452;
                    background-color: #13243d;
                    color: #f1f5ff;
                    font-weight: 600;
                }

                QPushButton#quranBackButton:hover {
                    border-color: #38d0a5;
                    background-color: #1b2d4a;
                }

                QSpinBox#quranAyahSpinner {
                    background-color: #1b2d4a;
                    border: 1px solid #1f3452;
                    border-radius: 8px;
                    padding: 4px 8px;
                    color: #f1f5ff;
                }

                QPushButton#quranSaveButton,
                QPushButton#quranClearButton {
                    padding: 10px 20px;
                    border-radius: 8px;
                    font-weight: 600;
                }

                QPushButton#quranSaveButton {
                    background-color: #15803d;
                    color: #f8fafc;
                    border: none;
                }

                QPushButton#quranSaveButton:hover {
                    background-color: #166534;
                }

                QPushButton#quranClearButton {
                    background-color: transparent;
                    color: #f1f5ff;
                    border: 1px solid #1f3452;
                }

                QPushButton#quranClearButton:hover {
                    border-color: #38d0a5;
                }

                QTextBrowser#quranText {
                    background-color: #0f1d32;
                    border: 1px solid #1f3452;
                    border-radius: 12px;
                    padding: 16px;
                    color: #f1f5ff;
                    font-size: 18px;
                    line-height: 1.6;
                    box-shadow: inset 0 0 0 1px rgba(21, 128, 61, 0.18), 0 20px 40px rgba(9, 16, 32, 0.45);
                }
                """
            ).strip()

        return textwrap.dedent(
            """
            QWidget {
                font-family: 'Ubuntu', 'Segoe UI', sans-serif;
            }

            #PrayerWindow {
                background: radial-gradient(circle at 18% 15%, #f0fdf4 0%, #f5f6fa 55%, #f0f9ff 120%);
            }

            #NavBar {
                background-color: #ffffff;
                border-radius: 24px;
                border: 1px solid #bbf7d0;
                padding: 16px 12px;
                box-shadow: 0 20px 35px rgba(15, 52, 26, 0.12);
            }

            QWidget#NavActions {
                border-top: 1px solid #bbf7d0;
                margin-top: 12px;
                padding-top: 16px;
            }

            QToolButton#NavButton {
                color: #14532d;
                font-weight: 600;
                padding: 12px 6px;
                margin: 4px 0;
                border-radius: 16px;
                background-color: transparent;
            }

            QToolButton#NavButton:hover {
                background-color: #dcfce7;
            }

            QToolButton#NavButton:checked {
                background-color: #15803d;
                color: #ffffff;
                border: none;
            }

            QLabel#locationLabel {
                color: #0f172a;
            }

            QLabel#dateLabel, QLabel#hijriLabel, QLabel#statusLabel, QLabel#observedAtLabel {
                color: #475569;
                font-size: 13px;
            }

            QLabel#nextPrayerLabel {
                color: #14532d;
                font-size: 14px;
            }

            QFrame#homeCard {
                background-color: #ffffff;
                border-radius: 20px;
                border: 1px solid #bbf7d0;
                box-shadow: 0 18px 32px rgba(13, 148, 136, 0.08);
            }

            QLabel#homeInspirationText {
                color: #0f172a;
                font-size: 16px;
                line-height: 1.7;
            }

            QPushButton#homeActionButton,
            QToolButton#homeActionButton {
                padding: 8px 18px;
                border-radius: 10px;
                border: 1px solid #bbf7d0;
                background-color: #ffffff;
                color: #14532d;
                font-weight: 600;
            }

            QPushButton#homeActionButton:hover,
            QToolButton#homeActionButton:hover {
                border-color: #4ade80;
                background-color: #f0fdf4;
            }

            QToolButton#homeActionButton:checked {
                background-color: #15803d;
                border-color: #15803d;
                color: #ffffff;
            }

            QFrame#weeklyBody {
                border-top: 1px solid #bbf7d0;
                padding-top: 12px;
            }

            QTableWidget#weeklyTable {
                background-color: #f8fafc;
                border: 1px solid #bbf7d0;
                border-radius: 12px;
                color: #0f172a;
                gridline-color: rgba(21, 128, 61, 0.15);
            }

            QTableWidget#weeklyTable::item {
                padding: 6px;
            }

            QTableWidget#weeklyTable QHeaderView::section {
                background-color: #ecfdf5;
                color: #15803d;
                border: none;
                padding: 6px;
            }

            QLabel#homeCardTitle {
                color: #14532d;
                font-size: 15px;
                font-weight: 600;
            }

            QLabel#homeCardPrimary {
                color: #0f172a;
                font-size: 28px;
                font-weight: 700;
            }

            QLabel#homeCardSecondary {
                color: #14532d;
                font-size: 16px;
                font-weight: 600;
            }

            QLabel#homeCardCaption {
                color: #475569;
                font-size: 12px;
            }

            QPushButton#PrimaryButton {
                padding: 10px 20px;
                border-radius: 8px;
                background-color: #15803d;
                color: #ffffff;
                font-weight: 600;
            }

            QPushButton#PrimaryButton:hover {
                background-color: #166534;
            }

            QPushButton#SecondaryButton {
                padding: 10px 20px;
                border-radius: 8px;
                border: 1px solid #bbf7d0;
                background-color: #ffffff;
                color: #14532d;
                font-weight: 600;
            }

            QPushButton#SecondaryButton:hover {
                border-color: #4ade80;
            }

            QPushButton#GhostButton {
                padding: 10px 18px;
                border-radius: 8px;
                border: none;
                background-color: transparent;
                color: #14532d;
                font-weight: 600;
            }

            QPushButton#GhostButton:hover {
                background-color: #dcfce7;
            }

            QFrame#hijriCard {
                background-color: #ffffff;
                border-radius: 16px;
                border: 1px solid #bbf7d0;
                padding: 18px;
            }

            QLabel#hijriTitle {
                color: #166534;
                font-size: 13px;
                font-weight: 600;
            }

            QLabel#hijriLabel {
                color: #052e16;
                font-size: 20px;
                font-weight: 600;
            }

            QFrame#prayerCard {
                background-color: #ffffff;
                border-radius: 16px;
                border: 1px solid #bbf7d0;
                padding: 18px;
                box-shadow: 0 16px 28px rgba(21, 128, 61, 0.12);
            }

            QFrame#prayerCard[state="active"] {
                border-color: #15803d;
                box-shadow: 0px 8px 20px rgba(21, 128, 61, 0.18);
            }

            QLabel#prayerName {
                font-size: 16px;
                font-weight: 600;
                color: #14532d;
            }

            QLabel#prayerName[active="true"] {
                color: #15803d;
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

            QScrollArea#forecastArea {
                background-color: transparent;
                border: none;
            }

            QWidget#forecastContainer {
                background-color: transparent;
            }

            QFrame#forecastCard {
                background-color: #ffffff;
                border-radius: 20px;
                border: 1px solid #bbf7d0;
            }

            QFrame#forecastCard:hover {
                border-color: #4ade80;
                box-shadow: 0px 8px 18px rgba(21, 128, 61, 0.18);
            }

            QLabel#forecastIcon {
                background-color: #f1f5f9;
                border-radius: 24px;
                padding: 8px;
            }

            QLabel#forecastDay {
                color: #15803d;
                font-size: 14px;
                font-weight: 600;
            }

            QLabel#forecastCondition {
                color: #475569;
                font-size: 12px;
            }

            QLabel#forecastTemps {
                color: #14532d;
                font-size: 16px;
                font-weight: 600;
            }

            QLabel#forecastTitle {
                color: #14532d;
                font-size: 15px;
                font-weight: 600;
            }

            QLabel#forecastPlaceholder {
                color: #6b7280;
                padding: 24px;
            }

            QFrame#quranCard {
                background-color: #ffffff;
                border-radius: 20px;
                border: 1px solid #bbf7d0;
            }

            QWidget#quranReader {
                background-color: #ffffff;
                border-radius: 20px;
                border: 1px solid #bbf7d0;
            }

            QListWidget#quranList {
                background-color: #f8fafc;
                border: 1px solid #bbf7d0;
                border-radius: 12px;
                padding: 8px;
                color: #0f172a;
            }

            QListWidget#quranList::item:selected {
                background-color: #15803d;
                color: #ffffff;
            }

            QListWidget#quranList::item:hover {
                background-color: #bbf7d0;
            }

            QLabel#quranHeader {
                color: #0f172a;
            }

            QLabel#quranReadingTitle {
                color: #0f172a;
            }

            QLabel#quranStatusLabel {
                color: #475569;
            }

            QLabel#quranAyahLabel {
                color: #14532d;
                font-weight: 600;
            }

            QPushButton#quranBackButton {
                padding: 8px 16px;
                border-radius: 10px;
                border: 1px solid #bbf7d0;
                background-color: #f8fafc;
                color: #14532d;
                font-weight: 600;
            }

            QPushButton#quranBackButton:hover {
                border-color: #4ade80;
                background-color: #e8fdf2;
            }

            QSpinBox#quranAyahSpinner {
                background-color: #ffffff;
                border: 1px solid #bbf7d0;
                border-radius: 8px;
                padding: 4px 8px;
                color: #0f172a;
            }

            QPushButton#quranSaveButton,
            QPushButton#quranClearButton {
                padding: 10px 20px;
                border-radius: 8px;
                font-weight: 600;
            }

            QPushButton#quranSaveButton {
                background-color: #15803d;
                color: #ffffff;
                border: none;
            }

            QPushButton#quranSaveButton:hover {
                background-color: #166534;
            }

            QPushButton#quranClearButton {
                background-color: transparent;
                color: #14532d;
                border: 1px solid #bbf7d0;
            }

            QPushButton#quranClearButton:hover {
                border-color: #4ade80;
            }

            QTextBrowser#quranText {
                background-color: #ffffff;
                border: 1px solid #bbf7d0;
                border-radius: 12px;
                padding: 16px;
                color: #0f172a;
                font-size: 18px;
                line-height: 1.6;
                box-shadow: inset 0 0 0 1px rgba(21, 128, 61, 0.08), 0 24px 48px rgba(21, 128, 61, 0.08);
            }
            """
        ).strip()
