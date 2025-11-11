"""Settings dialog for the prayer times application."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence

from location_catalog import LocationCatalog

try:
    from PyQt5 import QtCore, QtWidgets  # type: ignore
except Exception:  # pragma: no cover - fallback path
    try:
        from PySide2 import QtCore, QtWidgets  # type: ignore
    except Exception:
        from PySide6 import QtCore, QtWidgets  # type: ignore


class SettingsDialog(QtWidgets.QDialog):
    """Dialog exposing configurable application preferences."""

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget],
        translations: Dict[str, Any],
        language_options: List[tuple[str, str]],
        initial: Dict[str, Any],
        prayer_labels: Dict[str, str],
        countries: Sequence[Dict[str, Any]],
        catalog: LocationCatalog,
        theme: str = "light",
    ) -> None:
        super().__init__(parent)
        self.translations = translations
        self.setWindowTitle(translations.get("settings_title", "Settings"))
        self.setModal(True)
        self.resize(430, 460)

        self._catalog = catalog
        self._locations = list(countries)
        self._cities_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._theme = theme if theme in {"light", "dark"} else "light"
        self._placeholder_country = translations.get("select_country_placeholder", "Select country")
        self._placeholder_city = translations.get("select_city_placeholder", "Select city")
        initial_location = initial.get("location", {}) if isinstance(initial, dict) else {}

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        general_group = QtWidgets.QGroupBox(translations.get("settings_general", "General"))
        general_layout = QtWidgets.QVBoxLayout()

        language_row = QtWidgets.QHBoxLayout()
        language_label = QtWidgets.QLabel(translations.get("settings_language_label", "Language"))
        language_row.addWidget(language_label)
        language_row.addStretch()
        self.language_combo = QtWidgets.QComboBox()
        self.language_combo.setObjectName("settingsLanguageCombo")
        for code, label in language_options:
            self.language_combo.addItem(label, code)
        current_language = str(initial.get("language", ""))
        index = max(0, self.language_combo.findData(current_language))
        self.language_combo.setCurrentIndex(index)
        language_row.addWidget(self.language_combo)
        general_layout.addLayout(language_row)

        theme_row = QtWidgets.QHBoxLayout()
        theme_label = QtWidgets.QLabel(translations.get("settings_theme_label", "Theme"))
        theme_row.addWidget(theme_label)
        theme_row.addStretch()
        self.theme_combo = QtWidgets.QComboBox()
        self.theme_combo.setObjectName("settingsThemeCombo")
        theme_options = [
            ("system", translations.get("settings_theme_system", "Match system")),
            ("light", translations.get("settings_theme_light", "Light")),
            ("dark", translations.get("settings_theme_dark", "Dark")),
        ]
        for value, label in theme_options:
            self.theme_combo.addItem(label, value)
        current_theme = str(initial.get("theme", "system")).lower()
        if current_theme not in {"light", "dark", "system"}:
            current_theme = "system"
        theme_index = max(0, self.theme_combo.findData(current_theme))
        self.theme_combo.setCurrentIndex(theme_index)
        theme_row.addWidget(self.theme_combo)
        general_layout.addLayout(theme_row)

        self.auto_location_checkbox = QtWidgets.QCheckBox(
            translations.get("settings_auto_location", "Detect location automatically")
        )
        self.auto_location_checkbox.setChecked(bool(initial.get("auto_location", True)))
        general_layout.addWidget(self.auto_location_checkbox)

        location_form = QtWidgets.QFormLayout()
        location_form.setLabelAlignment(QtCore.Qt.AlignLeft)

        self.country_combo = QtWidgets.QComboBox()
        self.country_combo.setObjectName("settingsCountryCombo")
        self.country_combo.setEditable(False)
        self.country_combo.addItem(self._placeholder_country, None)
        for country in self._locations:
            name = country.get("name", "") if isinstance(country, dict) else str(country)
            code = country.get("code") if isinstance(country, dict) else None
            self.country_combo.addItem(name, {"name": name, "code": code})

        self.city_combo = QtWidgets.QComboBox()
        self.city_combo.setObjectName("settingsCityCombo")
        self.city_combo.setEditable(False)
        self.city_combo.addItem(self._placeholder_city, None)

        location_form.addRow(translations.get("country_prompt", "Country"), self.country_combo)
        location_form.addRow(translations.get("city_prompt", "City"), self.city_combo)
        general_layout.addLayout(location_form)

        self.launch_on_startup_checkbox = QtWidgets.QCheckBox(
            translations.get("settings_launch_on_startup", "Launch on startup")
        )
        self.launch_on_startup_checkbox.setChecked(bool(initial.get("launch_on_startup", False)))
        general_layout.addWidget(self.launch_on_startup_checkbox)

        general_group.setLayout(general_layout)
        layout.addWidget(general_group)

        audio_group = QtWidgets.QGroupBox(translations.get("settings_audio", "Adhan"))
        audio_layout = QtWidgets.QVBoxLayout()
        hint = QtWidgets.QLabel(translations.get("settings_short_adhan_hint", "Play shorter Adhan for:"))
        hint.setObjectName("settingsHint")
        hint.setWordWrap(True)
        audio_layout.addWidget(hint)

        self.adhan_checkboxes: Dict[str, QtWidgets.QCheckBox] = {}
        short_for = set(initial.get("use_short_for", []))
        for key in ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"]:
            label = prayer_labels.get(key, key)
            checkbox = QtWidgets.QCheckBox(label)
            checkbox.setChecked(key in short_for)
            self.adhan_checkboxes[key] = checkbox
            audio_layout.addWidget(checkbox)

        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)

        buttons = QtWidgets.QDialogButtonBox()
        save_label = translations.get("save", "Save")
        cancel_label = translations.get("cancel", "Cancel")
        self.save_button = buttons.addButton(save_label, QtWidgets.QDialogButtonBox.AcceptRole)
        self.cancel_button = buttons.addButton(cancel_label, QtWidgets.QDialogButtonBox.RejectRole)
        self.save_button.setObjectName("settingsPrimaryButton")
        self.cancel_button.setObjectName("settingsSecondaryButton")
        buttons.accepted.connect(self.accept)  # type: ignore
        buttons.rejected.connect(self.reject)  # type: ignore
        layout.addWidget(buttons)

        self.country_combo.currentIndexChanged.connect(self._on_country_changed)  # type: ignore
        self.auto_location_checkbox.toggled.connect(self._toggle_manual_fields)  # type: ignore
        self.theme_combo.currentIndexChanged.connect(self._on_theme_preview)  # type: ignore

        self._initial_location = initial_location
        catalog_source = getattr(self._catalog, "countries_source", lambda: "fallback")()
        self._is_remote_source = str(catalog_source).lower() == "remote"

        self._apply_initial_selection(initial_location)
        self._toggle_manual_fields(self.auto_location_checkbox.isChecked())
        self._apply_theme(self._theme)

        QtCore.QTimer.singleShot(0, self._refresh_countries)

    def values(self) -> Dict[str, Any]:
        return {
            "language": self.language_combo.currentData(),
            "auto_location": self.auto_location_checkbox.isChecked(),
            "launch_on_startup": self.launch_on_startup_checkbox.isChecked(),
            "use_short_for": [key for key, box in self.adhan_checkboxes.items() if box.isChecked()],
            "theme": self.theme_combo.currentData(),
            "location": self._selected_location_payload(),
        }

    def _on_country_changed(self, index: int) -> None:
        self._populate_cities(index)

    def _apply_initial_selection(self, initial: Dict[str, Any]) -> None:
        desired_code = initial.get("country_code") or initial.get("country")
        desired_city = initial.get("city")

        target_index = 0
        if desired_code:
            for idx in range(1, self.country_combo.count()):
                country = self.country_combo.itemData(idx)
                if not country:
                    continue
                if desired_code in (country.get("code"), country.get("name")):
                    target_index = idx
                    break
        self.country_combo.setCurrentIndex(target_index)
        self._populate_cities(target_index, desired_city)

    def _populate_cities(
        self,
        index: int,
        desired_city: Optional[str] = None,
        force_refresh: bool = False,
    ) -> None:
        country = self.country_combo.itemData(index)
        self.city_combo.blockSignals(True)
        self.city_combo.clear()
        self.city_combo.addItem(self._placeholder_city, None)

        if isinstance(country, dict):
            country_code = country.get("code")
            country_name = country.get("name")
            cache_key = (country_code or country_name or "").upper()
            if force_refresh:
                self._cities_cache.pop(cache_key, None)
            cities = self._cities_cache.get(cache_key)
            if cities is None:
                cities = self._load_cities_for_country(country_code, country_name, refresh=force_refresh)
                self._cities_cache[cache_key] = cities
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
        self.country_combo.setEnabled(not auto_detect)
        self.city_combo.setEnabled(not auto_detect)

    def _selected_location_payload(self) -> Dict[str, Optional[str]]:
        country_data = self.country_combo.currentData()
        city_data = self.city_combo.currentData()
        return {
            "country": country_data.get("name") if isinstance(country_data, dict) else None,
            "country_code": country_data.get("code") if isinstance(country_data, dict) else None,
            "city": city_data.get("name") if isinstance(city_data, dict) else None,
            "latitude": city_data.get("latitude") if isinstance(city_data, dict) else None,
            "longitude": city_data.get("longitude") if isinstance(city_data, dict) else None,
        }

    def _load_cities_for_country(
        self,
        country_code: Optional[str],
        country_name: Optional[str],
        *,
        refresh: bool = False,
    ) -> List[Dict[str, Any]]:
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            raw_cities = self._catalog.cities(country_code, country_name, refresh=refresh)
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

        cities: List[Dict[str, Any]] = []
        for city in raw_cities:
            if isinstance(city, dict):
                name = (
                    str(
                        city.get("name")
                        or city.get("city")
                        or city.get("city_name")
                        or city.get("englishName")
                        or ""
                    ).strip()
                )
                if not name:
                    continue
                cities.append(
                    {
                        "name": name,
                        "latitude": city.get("latitude"),
                        "longitude": city.get("longitude"),
                    }
                )
            else:
                name = str(city).strip()
                if name:
                    cities.append({"name": name})
        return cities

    def _on_theme_preview(self, index: int) -> None:
        value = self.theme_combo.itemData(index)
        desired = str(value) if value is not None else ""
        preview = desired if desired in {"light", "dark"} else self._theme
        self._apply_theme(preview)

    def _apply_theme(self, theme: str) -> None:
        if theme == "dark":
            self.setStyleSheet(
                """
                QDialog {
                    background-color: #0b1628;
                    color: #f1f5ff;
                }

                QLabel {
                    color: #f1f5ff;
                }

                QLabel#settingsHint {
                    color: #b7c3df;
                }

                QGroupBox {
                    border: 1px solid #1f3452;
                    border-radius: 12px;
                    margin-top: 16px;
                    padding: 12px;
                }

                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    left: 12px;
                    padding: 0 6px;
                    color: #38d0a5;
                }

                QComboBox#settingsCountryCombo,
                QComboBox#settingsCityCombo,
                QComboBox#settingsThemeCombo,
                QComboBox#settingsLanguageCombo {
                    background-color: #1b2d4a;
                    border: 1px solid #1f3452;
                    border-radius: 8px;
                    padding: 6px 10px;
                    color: #f1f5ff;
                }

                QComboBox#settingsCountryCombo QAbstractItemView,
                QComboBox#settingsCityCombo QAbstractItemView,
                QComboBox#settingsThemeCombo QAbstractItemView,
                QComboBox#settingsLanguageCombo QAbstractItemView {
                    background-color: #111d33;
                    color: #f1f5ff;
                    selection-background-color: #15803d;
                    selection-color: #ffffff;
                }

                QCheckBox {
                    spacing: 8px;
                }

                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                }

                QCheckBox::indicator:unchecked {
                    border: 1px solid #1f3452;
                    background-color: #1b2d4a;
                }

                QCheckBox::indicator:checked {
                    border: 1px solid #15803d;
                    background-color: #15803d;
                }

                QPushButton#settingsPrimaryButton {
                    background-color: #15803d;
                    color: #f8fafc;
                    border: none;
                    border-radius: 8px;
                    padding: 10px 20px;
                    font-weight: 600;
                }

                QPushButton#settingsPrimaryButton:hover {
                    background-color: #166534;
                }

                QPushButton#settingsSecondaryButton {
                    background-color: transparent;
                    color: #f1f5ff;
                    border: 1px solid #1f3452;
                    border-radius: 8px;
                    padding: 10px 20px;
                    font-weight: 600;
                }

                QPushButton#settingsSecondaryButton:hover {
                    border-color: #38d0a5;
                }
                """
            )
        else:
            self.setStyleSheet("")

    def _refresh_countries(self) -> None:
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            countries = self._catalog.countries(refresh=True)
            source = getattr(self._catalog, "countries_source", lambda: "fallback")()
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

        if not countries:
            return

        is_remote = str(source).lower() == "remote"
        if self._locations and countries == self._locations and self._is_remote_source == is_remote:
            return

        current_data = self.country_combo.currentData()
        current_code = None
        current_name = None
        if isinstance(current_data, dict):
            current_code = current_data.get("code")
            current_name = current_data.get("name")

        current_city = self.city_combo.currentData()
        current_city_name = current_city.get("name") if isinstance(current_city, dict) else None

        self._locations = list(countries)
        self._is_remote_source = is_remote
        self._cities_cache.clear()

        self.country_combo.blockSignals(True)
        self.country_combo.clear()
        self.country_combo.addItem(self._placeholder_country, None)
        for country in self._locations:
            name = country.get("name", "") if isinstance(country, dict) else str(country)
            code = country.get("code") if isinstance(country, dict) else None
            self.country_combo.addItem(name, {"name": name, "code": code})

        target_index = 0
        if current_code or current_name:
            for idx in range(1, self.country_combo.count()):
                data = self.country_combo.itemData(idx)
                if not isinstance(data, dict):
                    continue
                if current_code and data.get("code") == current_code:
                    target_index = idx
                    break
                if current_name and data.get("name") == current_name:
                    target_index = idx
        self.country_combo.setCurrentIndex(target_index)
        self.country_combo.blockSignals(False)

        if not self.auto_location_checkbox.isChecked():
            self._populate_cities(target_index, current_city_name, force_refresh=True)
