"""Entry point for the Islamic prayer times desktop application."""
from __future__ import annotations

import json
import logging
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, time as time_module
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import pytz
import html
import re
import requests
from tzlocal import get_localzone_name

try:  # Prefer PyQt5, fall back to Qt for Python if available
    from PyQt5 import QtCore, QtGui, QtWidgets  # type: ignore
except Exception:  # pragma: no cover - fallback only used when PyQt5 missing
    try:
        from PySide2 import QtCore, QtGui, QtWidgets  # type: ignore
    except Exception:
        from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore

try:  # Compatibility alias for Qt signal and slot decorators
    Signal = QtCore.pyqtSignal  # type: ignore[attr-defined]
    Slot = QtCore.pyqtSlot  # type: ignore[attr-defined]
except AttributeError:  # pragma: no cover - PySide compatibility
    Signal = QtCore.Signal  # type: ignore[attr-defined]
    Slot = QtCore.Slot  # type: ignore[attr-defined]

try:  # pragma: no cover - platform specific import
    import winreg
except ImportError:  # pragma: no cover - non-Windows fallback
    winreg = None  # type: ignore

from adhan_player import AdhanPlayer
from prayer_times import (
    LocationInfo,
    PrayerDay,
    PrayerTimesService,
    build_location_from_config,
    detect_location_from_ip,
)
from scheduler import PrayerScheduler
from location_catalog import LocationCatalog
from ui import PrayerTimesWindow, SettingsDialog, WelcomeDialog
from ui.quran import SURAH_DATA
from weather import WeatherInfo, WeatherService, DailyForecast

APP_ROOT = Path(__file__).parent
CONFIG_PATH = APP_ROOT / "config.json"
TRANSLATIONS_PATH = APP_ROOT / "translations.json"
LOCATIONS_PATH = APP_ROOT / "assets" / "locations.json"
STARTUP_REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_REGISTRY_VALUE = "Prayer App"

LANGUAGE_FALLBACK_NAMES = {
    "en": "English",
    "ar": "العربية",
}

AR_WEEKDAYS = [
    "الاثنين",
    "الثلاثاء",
    "الأربعاء",
    "الخميس",
    "الجمعة",
    "السبت",
    "الأحد",
]

AR_MONTHS = [
    "يناير",
    "فبراير",
    "مارس",
    "أبريل",
    "مايو",
    "يونيو",
    "يوليو",
    "أغسطس",
    "سبتمبر",
    "أكتوبر",
    "نوفمبر",
    "ديسمبر",
]

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
LOGGER = logging.getLogger(__name__)

ARABIC_INDIC_DIGITS = ("٠", "١", "٢", "٣", "٤", "٥", "٦", "٧", "٨", "٩")


class _AsyncDispatcher(QtCore.QObject):
    """Provide main-thread delivery for background task callbacks."""

    success = Signal(object)
    error = Signal(object)

    def __init__(
        self,
        owner: "PrayerApp",
        on_success: Callable[[Any], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        super().__init__()
        self._owner = owner
        self._on_success = on_success
        self._on_error = on_error
        self.success.connect(self._handle_success)  # type: ignore[attr-defined]
        self.error.connect(self._handle_error)  # type: ignore[attr-defined]

    @Slot(object)
    def _handle_success(self, result: Any) -> None:
        LOGGER.debug("Dispatcher invoking success handler %s", getattr(self._on_success, "__name__", self._on_success))
        try:
            self._on_success(result)
        finally:
            self._owner._async_dispatchers.discard(self)
            self.deleteLater()

    @Slot(object)
    def _handle_error(self, exc: Exception) -> None:
        LOGGER.debug("Dispatcher invoking error handler %s", getattr(self._on_error, "__name__", self._on_error))
        try:
            self._on_error(exc)
        finally:
            self._owner._async_dispatchers.discard(self)
            self.deleteLater()


class PrayerApp(QtWidgets.QApplication):
    """Coordinates the UI, scheduling, and playback components."""

    def __init__(self, argv: list[str]) -> None:
        super().__init__(argv)
        self.setApplicationName("Prayer Times")
        self.setQuitOnLastWindowClosed(False)

        self._register_application_font()
        self.setFont(QtGui.QFont("Ubuntu", 10))

        self._executor = ThreadPoolExecutor(max_workers=2)
        self._config = self._load_json(CONFIG_PATH, default={})
        self._translations = self._load_json(TRANSLATIONS_PATH, default={})
        self.location_catalog = LocationCatalog(LOCATIONS_PATH)
        self._async_dispatchers: Set[_AsyncDispatcher] = set()

        LOGGER.debug("Loaded config keys: %s", list(self._config.keys()))
        LOGGER.debug("Languages available: %s", list(self._translations.keys()))

        if not bool(self._config.get("onboarding_complete")):
            self._run_onboarding_flow()

        self.current_language = str(self._config.get("language", "en"))
        self.current_prayer_day: Optional[PrayerDay] = None
        self.current_location: Optional[LocationInfo] = build_location_from_config(self._config)
        self.current_weather: Optional[WeatherInfo] = None
        self.current_forecast: List[DailyForecast] = []
        self.weekly_schedule: List[Tuple[date, Dict[str, str]]] = []
        self.launch_on_startup = bool(self._config.get("launch_on_startup", False))
        self.theme_preference = str(self._config.get("theme", "system")).lower()
        if self.theme_preference not in {"light", "dark", "system"}:
            self.theme_preference = "system"
        self.active_theme = ""
        self._surah_cache: Dict[int, str] = {}
        self._pending_surah_number: Optional[int] = None
        self.current_inspiration: Tuple[str, Optional[str]] = ("", None)
        LOGGER.debug(
            "Initial state -> language=%s auto_location=%s manual_location=%s",
            self.current_language,
            self._config.get("auto_location", True),
            self.current_location,
        )

        adhan_cfg = self._config.get("adhan", {}) if isinstance(self._config, dict) else {}
        full_path = APP_ROOT / str(adhan_cfg.get("full_prayer", "assets/adhan_full.mp3"))
        short_path = APP_ROOT / str(adhan_cfg.get("short_prayer", "assets/adhan_short.mp3"))
        self.use_short_for = set(adhan_cfg.get("use_short_for", []))
        self.adhan_player = AdhanPlayer(str(full_path), str(short_path), parent=self)
        self.adhan_player.playback_finished.connect(self._on_adhan_playback_finished)  # type: ignore
        self._active_adhan_dialog: Optional[QtWidgets.QMessageBox] = None
        self._active_prayer_code: Optional[str] = None
        self._message_box_factory: Optional[Callable[[QtWidgets.QWidget], QtWidgets.QMessageBox]] = None
        self._allow_window_close = False
        self._tray_hint_shown = False

        calc_cfg = self._config.get("calculation", {}) if isinstance(self._config, dict) else {}
        method = int(calc_cfg.get("method", 3))
        school = int(calc_cfg.get("school", 0))
        self.prayer_service = PrayerTimesService(method=method, school=school)
        self.weather_service = WeatherService()
        self.quran_bookmark = self._normalize_quran_bookmark(self._config.get("quran_bookmark"))

        self.scheduler: Optional[PrayerScheduler] = None
        self.tray_icon: Optional[QtWidgets.QSystemTrayIcon] = None
        self.tray_menu: Optional[QtWidgets.QMenu] = None
        self.tray_show_action: Optional[QtWidgets.QAction] = None
        self.tray_hide_action: Optional[QtWidgets.QAction] = None
        self.tray_refresh_action: Optional[QtWidgets.QAction] = None
        self.tray_startup_action: Optional[QtWidgets.QAction] = None
        self.tray_quit_action: Optional[QtWidgets.QAction] = None

        self.window = PrayerTimesWindow()
        self._apply_theme_preference(self.theme_preference)
        self.window.on_refresh(self.refresh_prayer_times)
        self.window.on_language_toggle(self.toggle_language)
        self.window.on_settings_open(self.open_settings_dialog)
        self.window.on_quran_bookmark(self._handle_quran_bookmark)
        self.window.on_quran_surah_request(self._handle_quran_surah_request)
        self.window.set_quran_bookmark(self.quran_bookmark)
        self.window.on_close_attempt(self._handle_window_close)
        self.window.show()

        self._setup_tray_icon()

        self.countdown_timer = QtCore.QTimer(self)
        self.countdown_timer.timeout.connect(self.update_countdown_label)  # type: ignore
        self.countdown_timer.start(30_000)

        self.aboutToQuit.connect(self._cleanup)  # type: ignore

        self._apply_language(self.current_language)
        self._apply_startup_setting(self.launch_on_startup)
        QtCore.QTimer.singleShot(100, self.refresh_prayer_times)

    # ------------------------------------------------------------------
    def refresh_prayer_times(self) -> None:
        strings = self._strings_for_language()
        self.window.set_status(strings.get("updating", "Updating prayer times..."))
        LOGGER.debug("Refreshing prayer times (auto_location=%s)", self._config.get("auto_location", True))

        def task() -> Tuple[PrayerDay, Optional[WeatherInfo], List[DailyForecast], List[PrayerDay]]:
            LOGGER.debug("Refresh task started on worker thread")
            location = self._resolve_location()
            LOGGER.debug(
                "Resolved location for refresh: city=%s country=%s lat=%s lon=%s tz=%s",
                location.city,
                location.country,
                location.latitude,
                location.longitude,
                location.timezone,
            )
            prayer_day = self.prayer_service.fetch_prayer_times(location)

            weather_info: Optional[WeatherInfo] = None
            forecast: List[DailyForecast] = []
            weather_location = prayer_day.location
            if weather_location.latitude is not None and weather_location.longitude is not None:
                try:
                    weather_info, forecast = self.weather_service.fetch_weather(
                        weather_location.latitude,
                        weather_location.longitude,
                    )
                except Exception:  # pragma: no cover - network failure handled gracefully
                    LOGGER.warning(
                        "Weather fetch failed for location %s, %s",
                        weather_location.city,
                        weather_location.country,
                        exc_info=True,
                    )
            else:
                LOGGER.debug(
                    "Skipping weather fetch due to missing coordinates for location %s, %s",
                    weather_location.city,
                    weather_location.country,
                )

            upcoming_days: List[PrayerDay] = []
            for offset in range(1, 7):
                target_date = prayer_day.gregorian_date + timedelta(days=offset)
                try:
                    next_day = self.prayer_service.fetch_prayer_times(prayer_day.location, target_date=target_date)
                except Exception:
                    LOGGER.warning("Failed to fetch timetable for %s", target_date, exc_info=True)
                    break
                upcoming_days.append(next_day)

            return prayer_day, weather_info, forecast, upcoming_days

        self._run_async(task, self._handle_refresh_success, self._handle_refresh_error)

    def _resolve_location(self) -> LocationInfo:
        auto_location = bool(self._config.get("auto_location", True))
        if auto_location:
            LOGGER.debug("Attempting automatic location detection via IP lookup")
            try:
                location = detect_location_from_ip()
                LOGGER.debug(
                    "Automatic location detection success: city=%s country=%s lat=%s lon=%s tz=%s",
                    location.city,
                    location.country,
                    location.latitude,
                    location.longitude,
                    location.timezone,
                )
            except Exception:  # pragma: no cover - network failure
                LOGGER.warning("Automatic location detection failed; falling back to saved location", exc_info=True)
                if self.current_location:
                    LOGGER.debug("Using previously stored location: %s", self.current_location)
                    return self.current_location
                fallback = build_location_from_config(self._config)
                if fallback:
                    LOGGER.debug("Loaded fallback location from config: %s", fallback)
                    self.current_location = fallback
                    return fallback
                raise RuntimeError("Automatic location not configured")

            self._update_config_location(location)
            return location

        if self.current_location:
            LOGGER.debug("Using cached manual location: %s", self.current_location)
            if not self.current_location.city or not self.current_location.country:
                raise RuntimeError("Manual location not configured")
            return self.current_location
        raise RuntimeError("Manual location not configured")

    def _handle_refresh_success(
        self,
        result: Tuple[PrayerDay, Optional[WeatherInfo], List[DailyForecast], List[PrayerDay]],
    ) -> None:
        prayer_day, weather_info, forecast, upcoming_days = result
        self.current_prayer_day = prayer_day
        self.current_location = prayer_day.location
        self.current_weather = weather_info
        self.current_forecast = forecast or []
        self.weekly_schedule = self._build_weekly_schedule_rows(prayer_day, upcoming_days)

        strings = self._strings_for_language()
        LOGGER.info(
            "Prayer times refreshed for %s, %s",
            prayer_day.location.city,
            prayer_day.location.country,
        )
        LOGGER.debug("Prayer schedule contains %d entries", len(prayer_day.prayers))
        self._render_current_prayer_day()
        self.window.set_status(strings.get("updated", "Prayer times updated."))
        self.window.update_weekly_schedule(self.weekly_schedule)
        self._deliver_inspiration(self.current_language)

        tzinfo = prayer_day.prayers[0].time.tzinfo
        timezone_name = getattr(tzinfo, "zone", None) or str(tzinfo)
        self._ensure_scheduler(timezone_name)
        assert self.scheduler is not None
        self.scheduler.schedule_prayers(prayer_day.prayers, self._on_prayer_trigger)

        refresh_time = self._next_refresh_time(prayer_day.prayers[0].time)
        self.scheduler.schedule_refresh(refresh_time, lambda: QtCore.QTimer.singleShot(0, self.refresh_prayer_times))

    def _handle_refresh_error(self, error: Exception) -> None:
        LOGGER.error("Failed to refresh prayer times", exc_info=error)
        strings = self._strings_for_language()
        if isinstance(error, RuntimeError):
            message = strings.get("error_location", "Unable to detect location. Please set it manually.")
        else:
            message = strings.get("error_fetch", "Unable to fetch prayer times. Please try again.")
        self.window.set_status(message)
        QtWidgets.QMessageBox.warning(
            self.window,
            strings.get("error_title", "Error"),
            message,
        )

    def _next_refresh_time(self, reference: datetime) -> datetime:
        tzinfo = reference.tzinfo or pytz.UTC
        next_day = reference.date() + timedelta(days=1)
        refresh_naive = datetime.combine(next_day, time_module(hour=0, minute=5))
        if hasattr(tzinfo, "localize"):
            return tzinfo.localize(refresh_naive)
        return refresh_naive.replace(tzinfo=tzinfo)

    def _on_prayer_trigger(self, prayer_name: str) -> None:
        LOGGER.info("Triggering Adhan for %s", prayer_name)
        QtCore.QTimer.singleShot(0, lambda name=prayer_name: self._handle_prayer_trigger(name))

    def _handle_prayer_trigger(self, prayer_name: str) -> None:
        strings = self._strings_for_language()
        prayer_map = strings.get("prayers") if isinstance(strings, dict) else {}
        if not isinstance(prayer_map, dict):
            prayer_map = {}

        localized_name = str(prayer_map.get(prayer_name, prayer_name))
        self._active_prayer_code = prayer_name

        use_short = prayer_name in self.use_short_for
        audio_started = False
        try:
            audio_started = self.adhan_player.play(use_short=use_short)
        except Exception:
            LOGGER.exception("Failed to play Adhan audio")

        self._show_adhan_notification(localized_name, strings, audio_started=audio_started)

    def _show_adhan_notification(
        self,
        localized_prayer_name: str,
        strings: Dict[str, Any],
        *,
        audio_started: bool,
    ) -> None:
        title_template = strings.get("adhan_notification_title", "Time for {prayer}")
        body_template = strings.get("adhan_notification_body", "It's time for {prayer}.")
        try:
            title = str(title_template).format(prayer=localized_prayer_name)
        except Exception:
            title = f"Time for {localized_prayer_name}"
        try:
            body = str(body_template).format(prayer=localized_prayer_name)
        except Exception:
            body = f"It's time for {localized_prayer_name}."

        self.window.set_status(body)

        if self.tray_icon:
            try:
                self.tray_icon.showMessage(title, body, QtWidgets.QSystemTrayIcon.Information, 15_000)
            except Exception:  # pragma: no cover - platform dependent
                LOGGER.debug("Unable to show system tray notification", exc_info=True)

        if self._active_adhan_dialog:
            dialog = self._active_adhan_dialog
            self._active_adhan_dialog = None
            if dialog and dialog.isVisible():
                dialog.close()

        factory = getattr(self, "_message_box_factory", None)
        if callable(factory):
            box = factory(self.window)
        else:
            box = QtWidgets.QMessageBox(self.window)
        box.setWindowTitle(title)
        box.setText(body)
        box.setIcon(QtWidgets.QMessageBox.Information)
        box.setStandardButtons(QtWidgets.QMessageBox.NoButton)
        box.setWindowModality(QtCore.Qt.NonModal)
        box.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        snooze_label = strings.get("adhan_notification_snooze", "Snooze")
        dismiss_label = strings.get("adhan_notification_dismiss", "Dismiss")
        snooze_button = box.addButton(str(snooze_label), QtWidgets.QMessageBox.ActionRole)
        box.addButton(str(dismiss_label), QtWidgets.QMessageBox.RejectRole)

        def handle_click(button: QtWidgets.QAbstractButton) -> None:
            if button is snooze_button:
                self.adhan_player.stop()
            box.close()

        box.buttonClicked.connect(handle_click)  # type: ignore
        box.destroyed.connect(self._on_adhan_dialog_destroyed)  # type: ignore
        box.show()
        box.raise_()
        box.activateWindow()

        self._active_adhan_dialog = box

        if not audio_started:
            LOGGER.warning("Adhan audio did not start; notification shown without sound")

    def _on_adhan_playback_finished(self) -> None:
        LOGGER.debug("Adhan playback finished")
        self._active_prayer_code = None
        dialog = self._active_adhan_dialog
        if dialog:
            self._active_adhan_dialog = None
            if dialog.isVisible():
                dialog.close()

    def _on_adhan_dialog_destroyed(self, *_: object) -> None:
        self._active_adhan_dialog = None

    # -- System tray and startup ---------------------------------------------
    def _setup_tray_icon(self) -> None:
        if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
            LOGGER.warning("System tray not available on this system")
            return

        icon_path = APP_ROOT / "assets" / "app_icon.ico"
        icon = QtGui.QIcon(str(icon_path)) if icon_path.exists() else self.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon)

        tray = QtWidgets.QSystemTrayIcon(icon, self)
        tray.activated.connect(self._on_tray_activated)  # type: ignore

        menu = QtWidgets.QMenu()
        self.tray_show_action = menu.addAction("Show Window")
        self.tray_show_action.triggered.connect(self._show_main_window)  # type: ignore

        self.tray_hide_action = menu.addAction("Hide Window")
        self.tray_hide_action.triggered.connect(self._hide_main_window)  # type: ignore

        menu.addSeparator()
        self.tray_refresh_action = menu.addAction("Refresh Prayer Times")
        self.tray_refresh_action.triggered.connect(self.refresh_prayer_times)  # type: ignore

        self.tray_startup_action = menu.addAction("Enable Launch on Startup")
        self.tray_startup_action.setCheckable(True)
        self.tray_startup_action.triggered.connect(self.toggle_startup_launch)  # type: ignore

        menu.addSeparator()
        self.tray_quit_action = menu.addAction("Quit")
        self.tray_quit_action.triggered.connect(self._quit_from_tray)  # type: ignore

        tray.setContextMenu(menu)
        tray.setToolTip("Prayer Times")
        tray.show()

        self.tray_icon = tray
        self.tray_menu = menu

    def _on_tray_activated(self, reason: QtWidgets.QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QtWidgets.QSystemTrayIcon.Trigger, QtWidgets.QSystemTrayIcon.DoubleClick):
            self._show_main_window()

    def _show_main_window(self) -> None:
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def _hide_main_window(self) -> None:
        self.window.hide()

    def _handle_window_close(self) -> bool:
        if not self.tray_icon or not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
            return True
        if self._allow_window_close:
            return True

        self.window.hide()
        if not self._tray_hint_shown:
            strings = self._strings_for_language()
            title = strings.get("tray_minimize_title", "Prayer Times is still running")
            message = strings.get(
                "tray_minimize_message",
                "Prayer Times will keep running in the system tray. Use the tray icon to reopen or quit.",
            )
            try:
                self.tray_icon.showMessage(title, message, QtWidgets.QSystemTrayIcon.Information, 5000)
            except Exception:
                LOGGER.debug("System tray minimize hint failed", exc_info=True)
            self._tray_hint_shown = True
        return False

    def _quit_from_tray(self) -> None:
        self._allow_window_close = True
        self.quit()

    def toggle_startup_launch(self) -> None:
        desired = not self.launch_on_startup
        success = self._set_launch_on_startup(desired)
        strings = self._strings_for_language()
        if not success:
            QtWidgets.QMessageBox.warning(
                self.window,
                strings.get("error_title", "Error"),
                strings.get("startup_unsupported", "Startup toggle is not supported on this system."),
            )
            if self.tray_startup_action:
                self.tray_startup_action.setChecked(self.launch_on_startup)
            return

        self.launch_on_startup = desired
        self._config["launch_on_startup"] = desired
        self._save_json(CONFIG_PATH, self._config)
        status_key = "startup_enabled" if desired else "startup_disabled"
        fallback = "Launch on startup enabled." if desired else "Launch on startup disabled."
        self.window.set_status(strings.get(status_key, fallback))
        self._update_tray_texts(strings)

    def _update_tray_texts(self, strings: Dict[str, Any]) -> None:
        if not self.tray_icon:
            return

        tooltip = strings.get("tray_tooltip", "Prayer Times")
        self.tray_icon.setToolTip(tooltip)

        if self.tray_show_action:
            self.tray_show_action.setText(strings.get("tray_show", "Show Window"))
        if self.tray_hide_action:
            self.tray_hide_action.setText(strings.get("tray_hide", "Hide Window"))
        if self.tray_refresh_action:
            self.tray_refresh_action.setText(strings.get("tray_refresh", "Refresh Prayer Times"))
        if self.tray_quit_action:
            self.tray_quit_action.setText(strings.get("tray_quit", "Quit"))
        if self.tray_startup_action:
            label = (
                strings.get("tray_toggle_startup_off", "Disable Launch on Startup")
                if self.launch_on_startup
                else strings.get("tray_toggle_startup_on", "Enable Launch on Startup")
            )
            self.tray_startup_action.setText(label)
            self.tray_startup_action.setChecked(self.launch_on_startup)

    def _apply_startup_setting(self, enable: bool) -> None:
        if enable:
            success = self._set_launch_on_startup(True)
            if not success:
                LOGGER.warning("Unable to configure launch on startup")
                self.launch_on_startup = False
                self._config["launch_on_startup"] = False
                self._save_json(CONFIG_PATH, self._config)
        else:
            self._set_launch_on_startup(False)

    def _set_launch_on_startup(self, enable: bool) -> bool:
        if winreg is None or not sys.platform.startswith("win"):
            return not enable

        command = self._startup_command()
        try:
            access = winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REGISTRY_PATH, 0, access) as key:
                if enable:
                    winreg.SetValueEx(key, STARTUP_REGISTRY_VALUE, 0, winreg.REG_SZ, command)
                else:
                    try:
                        winreg.QueryValueEx(key, STARTUP_REGISTRY_VALUE)
                    except FileNotFoundError:
                        LOGGER.debug("Startup registry value already absent; nothing to remove")
                        return True

                    try:
                        winreg.DeleteValue(key, STARTUP_REGISTRY_VALUE)
                    except OSError:
                        LOGGER.exception("Unexpected error removing startup registry value")
                        return False
        except FileNotFoundError:
            if not enable:
                return True
            try:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, STARTUP_REGISTRY_PATH) as key:
                    winreg.SetValueEx(key, STARTUP_REGISTRY_VALUE, 0, winreg.REG_SZ, command)
            except OSError:
                LOGGER.exception("Failed to create startup registry key")
                return False
        except PermissionError:
            LOGGER.warning("Insufficient permissions to modify startup registry value")
            return False
        except OSError:
            LOGGER.exception("Failed to update startup registry value")
            return False

        return True

    def _startup_command(self) -> str:
        executable = sys.executable
        if executable.lower().endswith("python.exe"):
            pythonw = executable[:-9] + "pythonw.exe"
            if Path(pythonw).exists():
                executable = pythonw
        return f'"{executable}" "{APP_ROOT / "main.py"}"'

    def toggle_language(self) -> None:
        languages = list(self._translations.keys()) or ["en"]
        if len(languages) < 2:
            return
        current_index = languages.index(self.current_language) if self.current_language in languages else 0
        next_language = languages[(current_index + 1) % len(languages)]
        self.current_language = next_language
        self._config["language"] = next_language
        self._save_json(CONFIG_PATH, self._config)
        self._apply_language(next_language)
        if self.current_prayer_day:
            self._render_current_prayer_day()

    def update_countdown_label(self) -> None:
        if not self.current_prayer_day:
            self.window.update_next_prayer(None, None, None)
            return

        now = datetime.now(self.current_prayer_day.prayers[0].time.tzinfo)
        next_prayer = self.current_prayer_day.next_prayer(now)
        if not next_prayer:
            self.window.update_next_prayer(None, None, now)
            return

        delta = next_prayer.time - now
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes = remainder // 60
        if hours > 0:
            countdown = f"{hours}h {minutes}m"
        else:
            countdown = f"{minutes}m"
        self.window.update_next_prayer(next_prayer.name, countdown, now)

    # ------------------------------------------------------------------
    def _apply_language(self, language_code: str) -> None:
        strings = self._strings_for_language(language_code)
        prayer_map = strings.get("prayers", {}) if isinstance(strings, dict) else {}
        is_rtl = language_code.startswith("ar")
        self.window.apply_translations(strings, prayer_map, is_rtl)
        self._deliver_inspiration(language_code)
        self.window.update_weekly_schedule(self.weekly_schedule)
        self._update_tray_texts(strings)
        if self.current_prayer_day:
            self._render_current_prayer_day()

    def _strings_for_language(self, language_code: Optional[str] = None) -> Dict[str, Any]:
        language_code = language_code or self.current_language
        LOGGER.debug("Fetching translations for language %s", language_code)
        return self._translations.get(language_code, self._translations.get("en", {}))

    def _select_inspiration(self, language_code: str) -> Tuple[str, Optional[str]]:
        strings = self._strings_for_language(language_code)
        entries = strings.get("home_inspirations")
        if not isinstance(entries, list) or not entries:
            fallback = self._translations.get("en", {}).get("home_inspirations")
            entries = fallback if isinstance(fallback, list) else []

        if not entries:
            return "", None

        index = date.today().toordinal() % len(entries)
        entry = entries[index] if index < len(entries) else entries[0]
        if isinstance(entry, dict):
            text = str(entry.get("text", "")).strip()
            reference_raw = entry.get("reference")
            reference = str(reference_raw).strip() if reference_raw else None
            return text, reference

        text = str(entry).strip()
        return text, None

    def _deliver_inspiration(self, language_code: str) -> None:
        text, reference = self._select_inspiration(language_code)
        self.current_inspiration = (text, reference)
        if hasattr(self, "window"):
            self.window.update_inspiration(text, reference)

    def _ensure_scheduler(self, timezone: str) -> None:
        if self.scheduler and self.scheduler.timezone == timezone:
            LOGGER.debug("Scheduler already configured for timezone %s", timezone)
            return
        if self.scheduler:
            LOGGER.debug("Shutting down existing scheduler for timezone %s", self.scheduler.timezone)
            self.scheduler.shutdown()
        self.scheduler = PrayerScheduler(timezone)
        self.scheduler.start()
        LOGGER.debug("Started scheduler for timezone %s", timezone)

    def _update_config_location(self, location: LocationInfo, country_code: Optional[str] = None) -> None:
        if not isinstance(self._config.get("location"), dict):
            self._config["location"] = {}
        self._config["location"].update(
            {
                "city": location.city,
                "country": location.country,
                "latitude": location.latitude,
                "longitude": location.longitude,
                "timezone": location.timezone,
            }
        )
        if country_code:
            self._config["location"]["country_code"] = country_code
        LOGGER.debug("Persisting location config: %s", self._config.get("location"))
        self._save_json(CONFIG_PATH, self._config)

    def _normalize_quran_bookmark(self, bookmark: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not isinstance(bookmark, dict):
            return None
        try:
            surah_number = int(bookmark.get("surah", 0))
        except (TypeError, ValueError):
            return None
        if surah_number < 1 or surah_number > len(SURAH_DATA):
            return None

        try:
            ayah_number = int(bookmark.get("ayah", 1))
        except (TypeError, ValueError):
            ayah_number = 1
        ayah_number = max(1, ayah_number)

        surah_info = next((info for info in SURAH_DATA if info.number == surah_number), None)
        if surah_info is None:
            return None

        surah_name = bookmark.get("surah_name")
        if not isinstance(surah_name, str) or not surah_name.strip():
            surah_name = surah_info.name

        surah_name_ar = bookmark.get("surah_name_ar")
        if not isinstance(surah_name_ar, str) or not surah_name_ar.strip():
            surah_name_ar = surah_info.arabic_name

        return {
            "surah": surah_number,
            "ayah": ayah_number,
            "surah_name": surah_name,
            "surah_name_ar": surah_name_ar,
        }

    def _handle_quran_bookmark(self, bookmark: Optional[Dict[str, Any]]) -> None:
        normalized = self._normalize_quran_bookmark(bookmark)
        strings = self._strings_for_language()

        if normalized:
            self.quran_bookmark = normalized
            self._config["quran_bookmark"] = normalized
            self._save_json(CONFIG_PATH, self._config)

            template = strings.get("quran_bookmark_saved", "Bookmark saved for {surah} · Ayah {ayah}.")
            if not isinstance(template, str):
                template = "Bookmark saved for {surah} · Ayah {ayah}."
            message = template.format(surah=normalized.get("surah_name"), ayah=normalized.get("ayah"))
            self.window.set_status(message)
        else:
            self.quran_bookmark = None
            if "quran_bookmark" in self._config:
                self._config.pop("quran_bookmark", None)
                self._save_json(CONFIG_PATH, self._config)

            cleared = strings.get("quran_bookmark_cleared", "Bookmark cleared.")
            if not isinstance(cleared, str):
                cleared = "Bookmark cleared."
            self.window.set_status(cleared)

        self.window.set_quran_bookmark(self.quran_bookmark)

    def _handle_quran_surah_request(self, surah_number: int) -> None:
        if surah_number < 1 or surah_number > len(SURAH_DATA):
            return

        self._pending_surah_number = surah_number

        cached = self._surah_cache.get(surah_number)
        if cached is not None:
            self.window.display_quran_text(surah_number, cached, None)
            return

        self.window.show_quran_loading(surah_number)

        def task() -> str:
            return self._download_surah_text(surah_number)

        def on_success(text: str) -> None:
            if self._pending_surah_number != surah_number:
                return
            self._surah_cache[surah_number] = text
            self.window.display_quran_text(surah_number, text, None)

        def on_error(exc: Exception) -> None:
            if self._pending_surah_number != surah_number:
                return
            strings = self._strings_for_language()
            message = strings.get("quran_error_detail", str(exc))
            if not isinstance(message, str):
                message = str(exc)
            self.window.display_quran_text(surah_number, None, message)

        self._run_async(task, on_success, on_error)

    def _download_surah_text(self, surah_number: int) -> str:
        endpoint = f"https://api.alquran.cloud/v1/surah/{surah_number}?edition=quran-uthmani"
        try:
            response = requests.get(endpoint, timeout=15)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise RuntimeError("Network request failed") from exc

        if not isinstance(payload, dict) or payload.get("status") != "OK":
            raise RuntimeError("Unexpected response from Qur'an service")

        data = payload.get("data", {})
        ayahs = data.get("ayahs", []) if isinstance(data, dict) else []
        if not ayahs:
            raise RuntimeError("Surah text unavailable")

        return self._build_surah_html(surah_number, ayahs)

    def _build_surah_html(self, surah_number: int, ayahs: List[Dict[str, Any]]) -> str:
        blocks: List[str] = []
        for index, ayah in enumerate(ayahs):
            if not isinstance(ayah, dict):
                continue
            text = ayah.get("text")
            if not isinstance(text, str):
                continue

            clean_text = re.sub(r"\u06dd[\u0660-\u0669]+", "", text).strip()
            if not clean_text:
                continue

            try:
                number_in_surah = int(ayah.get("numberInSurah", index + 1))
            except (TypeError, ValueError):
                number_in_surah = index + 1

            digits = "".join(ARABIC_INDIC_DIGITS[int(d)] for d in str(abs(number_in_surah)))
            classes = "ayah basmala" if index == 0 and surah_number != 9 else "ayah"
            safe_text = html.escape(clean_text)
            number_html = f"<span class='ayah-number'>{digits}</span>"
            blocks.append(f"<p dir='rtl' class='{classes}'>{safe_text}{number_html}</p>")

        if not blocks:
            raise RuntimeError("Surah text unavailable")

        return "<div class='surah-body' dir='rtl'>" + "".join(blocks) + "</div>"

    def _build_weekly_schedule_rows(
        self,
        today: PrayerDay,
        upcoming: List[PrayerDay],
    ) -> List[Tuple[date, Dict[str, str]]]:
        rows: List[Tuple[date, Dict[str, str]]] = []
        days = [today] + list(upcoming)
        base_date = today.gregorian_date
        for index, entry in enumerate(days[:7]):
            display_date = base_date + timedelta(days=index)
            timings = {info.name: info.time.strftime("%H:%M") for info in entry.prayers}
            rows.append((display_date, timings))
        return rows

    def _render_current_prayer_day(self) -> None:
        if not self.current_prayer_day:
            return

        prayer_day = self.current_prayer_day
        LOGGER.info(
            "Rendering prayer day for %s with %d entries",
            prayer_day.location.city or prayer_day.location.country,
            len(prayer_day.prayers),
        )
        self.window.update_location(prayer_day.location.city, prayer_day.location.country)
        self.window.update_hijri_date(prayer_day.hijri_date)
        gregorian_text = self._format_gregorian_date(prayer_day.gregorian_date)
        self.window.update_gregorian_date(gregorian_text)
        self.window.update_prayers(prayer_day.prayers)
        self.update_countdown_label()
        self.window.update_weather(
            self._weather_location_label(prayer_day.location), self.current_weather, self.current_forecast
        )
        self.window.repaint()

    def _format_gregorian_date(self, day: date) -> str:
        if self.current_language.startswith("ar"):
            weekday = AR_WEEKDAYS[day.weekday()]
            month = AR_MONTHS[day.month - 1]
            return f"{weekday}، {day.day} {month} {day.year}"
        return day.strftime("%A, %B %d, %Y")

    def _weather_location_label(self, location: Optional[LocationInfo]) -> str:
        if not location:
            strings = self._strings_for_language()
            return strings.get("weather_tab_title", "Weather")

        parts = [part for part in [location.city, location.country] if part]
        if parts:
            return ", ".join(parts)

        if location.timezone:
            return str(location.timezone)

        strings = self._strings_for_language()
        return strings.get("weather_tab_title", "Weather")

    def _find_city_record(
        self,
        country_code: Optional[str],
        city_name: Optional[str],
        country_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not city_name:
            LOGGER.debug("City lookup skipped because city_name is missing")
            return None
        record = self.location_catalog.city_record(country_code, country_name, city_name)
        if record:
            LOGGER.debug("Matched city %s (country=%s)", city_name, country_code or country_name)
        else:
            LOGGER.debug("City %s (country_code=%s) not found in catalog", city_name, country_code)
        return record

    def _system_timezone(self) -> str:
        try:
            tz_name = get_localzone_name()
            pytz.timezone(tz_name)
            LOGGER.debug("Resolved system timezone: %s", tz_name)
            return tz_name
        except Exception:
            LOGGER.warning("Falling back to UTC for system timezone resolution")
            return "UTC"

    def _apply_theme_preference(self, preference: Optional[str]) -> None:
        resolved = self._resolve_theme_choice(preference)
        if self.active_theme == resolved:
            return
        LOGGER.debug("Applying theme preference '%s' resolved to '%s'", preference, resolved)
        self.active_theme = resolved
        self.window.apply_theme(resolved)

    def _resolve_theme_choice(self, preference: Optional[str]) -> str:
        pref = str(preference or "system").lower()
        if pref not in {"light", "dark", "system"}:
            pref = "system"
        if pref == "system":
            return self._detect_system_theme()
        return pref

    def _detect_system_theme(self) -> str:
        if sys.platform.startswith("win") and winreg:
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                ) as key:
                    value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                    return "light" if int(value) else "dark"
            except Exception:
                LOGGER.debug("Windows theme detection failed; falling back to palette", exc_info=True)

        if sys.platform == "darwin":
            try:
                result = subprocess.run(
                    ["defaults", "read", "-g", "AppleInterfaceStyle"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode == 0:
                    return "dark"
            except Exception:
                LOGGER.debug("macOS theme detection failed; falling back to palette", exc_info=True)

        palette = self.palette()
        window_color = palette.color(QtGui.QPalette.Window)
        return "dark" if window_color.lightness() < 128 else "light"

    def _register_application_font(self) -> None:
        font_db = QtGui.QFontDatabase()
        if "Ubuntu" in font_db.families():
            return
        font_path = APP_ROOT / "assets" / "Ubuntu-Regular.ttf"
        if font_path.exists():
            result = font_db.addApplicationFont(str(font_path))
            if result == -1:
                LOGGER.warning("Failed to load bundled Ubuntu font asset")
        else:
            LOGGER.info("Ubuntu font not found in assets; falling back to system default")

    def _run_onboarding_flow(self) -> None:
        language_options = self._language_options()
        theme_preview = self._resolve_theme_choice(self._config.get("theme"))
        dialog = WelcomeDialog(None, self._translations, language_options, self.location_catalog, theme=theme_preview)
        result = dialog.exec()
        if result != QtWidgets.QDialog.Accepted:
            raise SystemExit(0)

        payload = dialog.values()
        language = str(payload.get("language") or "en")
        auto_location = bool(payload.get("auto_location", True))
        location_payload = payload.get("location") or {}

        self._config["language"] = language
        self._config["auto_location"] = auto_location

        if auto_location:
            self._config.pop("location", None)
        else:
            city = str(location_payload.get("city") or "").strip()
            country = str(location_payload.get("country") or "").strip()
            if city and country:
                latitude = self._parse_optional_float(location_payload.get("latitude"))
                longitude = self._parse_optional_float(location_payload.get("longitude"))
                timezone = self._system_timezone()
                self._config.setdefault("location", {})
                self._config["location"].update(
                    {
                        "city": city,
                        "country": country,
                        "latitude": latitude,
                        "longitude": longitude,
                        "timezone": timezone,
                    }
                )
                country_code = location_payload.get("country_code")
                if country_code:
                    self._config["location"]["country_code"] = country_code
            else:
                self._config.pop("location", None)

        self._config["onboarding_complete"] = True
        self._save_json(CONFIG_PATH, self._config)

    def _language_options(self) -> List[Tuple[str, str]]:
        options: List[Tuple[str, str]] = []
        for code in self._translations.keys():
            translations = self._translations.get(code, {})
            label = translations.get("language_display") or LANGUAGE_FALLBACK_NAMES.get(code, code)
            options.append((code, str(label)))
        if not options:
            options.append(("en", LANGUAGE_FALLBACK_NAMES.get("en", "English")))
        return options

    def open_settings_dialog(self) -> None:
        strings = self._strings_for_language()
        language_options = self._language_options()
        prayer_labels = {
            name: strings.get("prayers", {}).get(name, name)
            for name in ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]
        }
        if not isinstance(self._config.get("adhan"), dict):
            self._config["adhan"] = {}

        initial_location_cfg: Dict[str, Any] = {}
        if isinstance(self._config.get("location"), dict):
            initial_location_cfg = dict(self._config["location"])

        countries = self.location_catalog.countries()
        dialog = SettingsDialog(
            self.window,
            strings,
            language_options,
            {
                "language": self.current_language,
                "auto_location": self._config.get("auto_location", True),
                "launch_on_startup": self.launch_on_startup,
                "use_short_for": list(self.use_short_for),
                "theme": self.theme_preference,
                "location": initial_location_cfg,
            },
            prayer_labels,
            countries,
            self.location_catalog,
            theme=self.active_theme or "light",
        )

        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return

        values = dialog.values()
        desired_language = values.get("language", self.current_language)
        desired_auto = bool(values.get("auto_location", True))
        desired_startup = bool(values.get("launch_on_startup", False))
        desired_short = set(values.get("use_short_for", []))
        desired_theme_pref = str(values.get("theme", self.theme_preference or "system")).lower()
        if desired_theme_pref not in {"light", "dark", "system"}:
            desired_theme_pref = "system"
        desired_location_cfg = values.get("location") or {}

        manual_location_info: Optional[LocationInfo] = None
        desired_country_code: Optional[str] = None
        current_auto = bool(self._config.get("auto_location", True))

        if not desired_auto:
            city_name = str(desired_location_cfg.get("city") or "").strip()
            country_name = str(desired_location_cfg.get("country") or "").strip()
            desired_country_code = str(desired_location_cfg.get("country_code") or "").strip() or None

            if not city_name or not country_name:
                QtWidgets.QMessageBox.warning(
                    self.window,
                    strings.get("error_title", "Error"),
                    strings.get("error_city_country", "Please provide both city and country."),
                )
                return

            city_record = self._find_city_record(
                desired_country_code,
                city_name,
                desired_location_cfg.get("country"),
            )
            if not city_record:
                QtWidgets.QMessageBox.warning(
                    self.window,
                    strings.get("error_title", "Error"),
                    strings.get("error_city_country", "Please provide both city and country."),
                )
                return

            latitude = self._parse_optional_float(city_record.get("latitude"))
            longitude = self._parse_optional_float(city_record.get("longitude"))
            timezone = self._system_timezone()
            manual_location_info = LocationInfo(
                city=city_name,
                country=country_name,
                latitude=latitude,
                longitude=longitude,
                timezone=timezone,
            )

        existing_manual_cfg = initial_location_cfg if isinstance(initial_location_cfg, dict) else {}
        location_changed = False
        if not desired_auto and manual_location_info:
            location_changed = (
                str(existing_manual_cfg.get("city")) != manual_location_info.city
                or str(existing_manual_cfg.get("country")) != manual_location_info.country
                or self._parse_optional_float(existing_manual_cfg.get("latitude")) != manual_location_info.latitude
                or self._parse_optional_float(existing_manual_cfg.get("longitude")) != manual_location_info.longitude
            )
        elif desired_auto != current_auto:
            location_changed = True

        startup_changed = desired_startup != self.launch_on_startup
        language_changed = desired_language != self.current_language and desired_language is not None
        auto_changed = desired_auto != current_auto
        audio_changed = desired_short != self.use_short_for

        theme_changed = desired_theme_pref != self.theme_preference

        if not any([startup_changed, language_changed, auto_changed, audio_changed, location_changed, theme_changed]):
            self.window.set_status(strings.get("settings_saved", "Settings updated."))
            return

        self.window.set_status(strings.get("settings_applying", "Applying settings..."))

        def task() -> Dict[str, bool]:
            startup_result = True
            if startup_changed:
                startup_result = self._set_launch_on_startup(desired_startup)
            return {"startup_result": startup_result}

        def on_success(result: Dict[str, bool]) -> None:
            strings_local = self._strings_for_language()
            status_message = strings_local.get("settings_saved", "Settings updated.")

            if startup_changed:
                if result.get("startup_result", False):
                    self.launch_on_startup = desired_startup
                    self._config["launch_on_startup"] = desired_startup
                else:
                    status_message = strings_local.get(
                        "startup_unsupported",
                        "Startup toggle is not supported on this system.",
                    )
                    QtWidgets.QMessageBox.warning(
                        self.window,
                        strings_local.get("error_title", "Error"),
                        status_message,
                    )

            if language_changed:
                self.current_language = desired_language
                self._config["language"] = desired_language
                self._apply_language(desired_language)
                self._render_current_prayer_day()

            if theme_changed:
                self.theme_preference = desired_theme_pref
                self._config["theme"] = desired_theme_pref
                self._apply_theme_preference(self.theme_preference)

            if auto_changed or location_changed:
                self._config["auto_location"] = desired_auto
                if not desired_auto and manual_location_info:
                    self.current_location = manual_location_info
                    self._update_config_location(manual_location_info, desired_country_code)

            if audio_changed:
                self.use_short_for = desired_short
                self._config.setdefault("adhan", {})
                self._config["adhan"]["use_short_for"] = list(desired_short)

            self._save_json(CONFIG_PATH, self._config)

            if auto_changed or (not desired_auto and location_changed):
                self.refresh_prayer_times()
            elif language_changed and self.current_prayer_day:
                self._render_current_prayer_day()
            else:
                self.update_countdown_label()

            self.window.set_status(status_message)

        def on_error(exc: Exception) -> None:
            LOGGER.exception("Failed to apply settings", exc_info=exc)
            strings_local = self._strings_for_language()
            message = strings_local.get("settings_error", "Unable to apply settings. Please try again.")
            self.window.set_status(message)
            QtWidgets.QMessageBox.warning(
                self.window,
                strings_local.get("error_title", "Error"),
                message,
            )

        self._run_async(task, on_success, on_error)

    @staticmethod
    def _parse_optional_float(value: Optional[object]) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        stripped = str(value).strip()
        if not stripped:
            return None
        return float(stripped)

    def _run_async(self, func, on_success, on_error) -> None:
        LOGGER.debug("Submitting background task %s", getattr(func, "__name__", func))
        dispatcher = _AsyncDispatcher(self, on_success, on_error)
        self._async_dispatchers.add(dispatcher)
        future = self._executor.submit(func)

        def _done(future_result) -> None:
            try:
                result = future_result.result()
                LOGGER.debug("Background task %s completed successfully", getattr(func, "__name__", func))
            except Exception as exc:  # pragma: no cover - UI glue
                LOGGER.exception("Background task %s raised an exception", getattr(func, "__name__", func), exc_info=exc)
                dispatcher.error.emit(exc)
            else:
                dispatcher.success.emit(result)

        future.add_done_callback(_done)

    @staticmethod
    def _load_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    @staticmethod
    def _save_json(path: Path, payload: Dict[str, Any]) -> None:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def _cleanup(self) -> None:
        if self.scheduler:
            self.scheduler.shutdown()
        self._executor.shutdown(wait=False)
        self.adhan_player.stop()
        if self.tray_icon:
            self.tray_icon.hide()
        self._allow_window_close = True


def main() -> int:
    app = PrayerApp(sys.argv)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
