"""Settings dialog for the prayer times application."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

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
        locations: Iterable[Dict[str, Any]],
    ) -> None:
        super().__init__(parent)
        self.translations = translations
        self.setWindowTitle(translations.get("settings_title", "Settings"))
        self.setModal(True)
        self.resize(430, 460)

        self._locations = list(locations)
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
            self.country_combo.addItem(country.get("name", ""), country)

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
        buttons.accepted.connect(self.accept)  # type: ignore
        buttons.rejected.connect(self.reject)  # type: ignore
        layout.addWidget(buttons)

        self.country_combo.currentIndexChanged.connect(self._on_country_changed)  # type: ignore
        self.auto_location_checkbox.toggled.connect(self._toggle_manual_fields)  # type: ignore

        self._apply_initial_selection(initial_location)
        self._toggle_manual_fields(self.auto_location_checkbox.isChecked())

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

    def _populate_cities(self, index: int, desired_city: Optional[str] = None) -> None:
        country = self.country_combo.itemData(index)
        self.city_combo.blockSignals(True)
        self.city_combo.clear()
        self.city_combo.addItem(self._placeholder_city, None)

        if country and isinstance(country, dict):
            for city in country.get("cities", []):
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
