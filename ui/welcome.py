"""First-run welcome dialog for initial language and location selection."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from location_catalog import LocationCatalog

try:  # Prefer PyQt5
    from PyQt5 import QtCore, QtGui, QtWidgets  # type: ignore
except Exception:  # pragma: no cover - fallback path
    try:
        from PySide2 import QtCore, QtGui, QtWidgets  # type: ignore
    except Exception:
        from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore


class WelcomeDialog(QtWidgets.QDialog):
    """Guides the user through the first-run experience."""

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget],
        translations: Dict[str, Any],
        language_options: Sequence[Tuple[str, str]],
        catalog: LocationCatalog,
        *,
        theme: str = "light",
    ) -> None:
        super().__init__(parent)
        self.setModal(True)
        self.setObjectName("WelcomeDialog")
        self.setWindowTitle(translations.get("welcome_title", "Welcome"))
        self.resize(520, 480)

        self._catalog = catalog
        self._translations = translations
        self._theme = theme if theme in {"light", "dark"} else "light"
        self._placeholder_country = translations.get("select_country_placeholder", "Select country")
        self._placeholder_city = translations.get("select_city_placeholder", "Select city")
        self._cities_cache: Dict[str, List[Dict[str, Any]]] = {}

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)

        header = QtWidgets.QLabel(translations.get("welcome_heading", "Assalamu alaikum"))
        header_font = QtGui.QFont(header.font())
        header_font.setPointSize(22)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setObjectName("welcomeHeader")
        layout.addWidget(header)

        subtitle_text = translations.get(
            "welcome_subtitle",
            "Let's get you set up with your preferred language and location.",
        )
        subtitle = QtWidgets.QLabel(subtitle_text)
        subtitle.setObjectName("welcomeSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # Language selection card
        language_card = QtWidgets.QGroupBox(translations.get("welcome_language_title", "Language"))
        language_layout = QtWidgets.QVBoxLayout()
        language_layout.setSpacing(12)

        hint = QtWidgets.QLabel(
            translations.get(
                "welcome_language_hint",
                "Choose the language you would like to use inside the app.",
            )
        )
        hint.setWordWrap(True)
        hint.setObjectName("welcomeHint")
        language_layout.addWidget(hint)

        self.language_combo = QtWidgets.QComboBox()
        self.language_combo.setObjectName("welcomeLanguageCombo")
        for code, label in language_options:
            self.language_combo.addItem(label, code)
        language_layout.addWidget(self.language_combo)
        language_card.setLayout(language_layout)
        layout.addWidget(language_card)

        # Location configuration card
        location_card = QtWidgets.QGroupBox(translations.get("welcome_location_title", "Location"))
        location_layout = QtWidgets.QVBoxLayout()
        location_layout.setSpacing(12)

        location_hint = QtWidgets.QLabel(
            translations.get(
                "welcome_location_hint",
                "We can detect your location automatically or you can set a specific city.",
            )
        )
        location_hint.setObjectName("welcomeHint")
        location_hint.setWordWrap(True)
        location_layout.addWidget(location_hint)

        self.auto_radio = QtWidgets.QRadioButton(
            translations.get("welcome_location_auto", "Detect my location automatically")
        )
        self.manual_radio = QtWidgets.QRadioButton(
            translations.get("welcome_location_manual", "Let me choose a location")
        )
        self.auto_radio.setChecked(True)
        location_layout.addWidget(self.auto_radio)
        location_layout.addWidget(self.manual_radio)

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignLeft)

        self.country_combo = QtWidgets.QComboBox()
        self.country_combo.setObjectName("welcomeCountryCombo")
        self.country_combo.addItem(self._placeholder_country, None)
        for country in self._catalog.countries():
            if not isinstance(country, dict):
                continue
            name = str(country.get("name") or "").strip()
            code = country.get("code")
            if not name:
                continue
            self.country_combo.addItem(name, {"name": name, "code": code})

        self.city_combo = QtWidgets.QComboBox()
        self.city_combo.setObjectName("welcomeCityCombo")
        self.city_combo.addItem(self._placeholder_city, None)

        form.addRow(translations.get("country_prompt", "Country"), self.country_combo)
        form.addRow(translations.get("city_prompt", "City"), self.city_combo)
        location_layout.addLayout(form)

        location_card.setLayout(location_layout)
        layout.addWidget(location_card)

        layout.addStretch(1)

        self.error_label = QtWidgets.QLabel("")
        self.error_label.setObjectName("welcomeError")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        self.button_box = QtWidgets.QDialogButtonBox()
        continue_label = translations.get("welcome_continue", "Get started")
        cancel_label = translations.get("cancel", "Cancel")
        self.continue_button = self.button_box.addButton(continue_label, QtWidgets.QDialogButtonBox.AcceptRole)
        self.cancel_button = self.button_box.addButton(cancel_label, QtWidgets.QDialogButtonBox.RejectRole)
        self.continue_button.setObjectName("welcomePrimaryButton")
        self.cancel_button.setObjectName("welcomeSecondaryButton")
        layout.addWidget(self.button_box)

        self.button_box.accepted.connect(self.accept)  # type: ignore
        self.button_box.rejected.connect(self.reject)  # type: ignore
        self.manual_radio.toggled.connect(self._toggle_manual_fields)  # type: ignore
        self.country_combo.currentIndexChanged.connect(self._on_country_changed)  # type: ignore

        self._toggle_manual_fields(False)
        self._apply_theme(self._theme)

    # ------------------------------------------------------------------
    def values(self) -> Dict[str, Any]:
        return {
            "language": self.language_combo.currentData(),
            "auto_location": self.auto_radio.isChecked(),
            "location": self._selected_location_payload(),
        }

    # ------------------------------------------------------------------
    def accept(self) -> None:  # type: ignore[override]
        self.error_label.hide()
        if not self.language_combo.currentData():
            self._show_error("Please choose a language to continue.")
            return

        if self.manual_radio.isChecked():
            location = self._selected_location_payload()
            if not location.get("country") or not location.get("city"):
                self._show_error("Select both a country and city to continue.")
                return
        super().accept()

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()

    def _toggle_manual_fields(self, manual_enabled: bool) -> None:
        self.country_combo.setEnabled(manual_enabled)
        self.city_combo.setEnabled(manual_enabled)

    def _on_country_changed(self, index: int) -> None:
        if not self.manual_radio.isChecked():
            return
        self._populate_cities(index)

    def _populate_cities(self, index: int) -> None:
        country = self.country_combo.itemData(index)
        self.city_combo.blockSignals(True)
        self.city_combo.clear()
        self.city_combo.addItem(self._placeholder_city, None)

        if isinstance(country, dict):
            code = country.get("code")
            name = country.get("name")
            cache_key = (code or name or "").upper()
            cities = self._cities_cache.get(cache_key)
            if cities is None:
                cities = self._load_cities_for_country(code, name)
                self._cities_cache[cache_key] = cities
            for city in cities:
                self.city_combo.addItem(city.get("name", ""), city)
        self.city_combo.blockSignals(False)

    def _load_cities_for_country(
        self,
        country_code: Optional[str],
        country_name: Optional[str],
    ) -> List[Dict[str, Any]]:
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            raw_cities = self._catalog.cities(country_code, country_name)
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

        cities: List[Dict[str, Any]] = []
        for city in raw_cities:
            if isinstance(city, dict):
                name = str(city.get("name") or city.get("city") or "").strip()
                if not name:
                    continue
                cities.append(
                    {
                        "name": name,
                        "latitude": city.get("latitude"),
                        "longitude": city.get("longitude"),
                        "country_code": country_code,
                    }
                )
            else:
                name = str(city).strip()
                if name:
                    cities.append({"name": name, "country_code": country_code})
        return cities

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

    def _apply_theme(self, theme: str) -> None:
        if theme == "dark":
            self.setStyleSheet(
                """
                QDialog#WelcomeDialog {
                    background-color: #0b1628;
                    color: #f1f5ff;
                }

                QLabel#welcomeHeader {
                    color: #d7fee4;
                }

                QLabel#welcomeSubtitle {
                    color: #b7c3df;
                }

                QLabel#welcomeHint {
                    color: #b7c3df;
                }

                QLabel#welcomeError {
                    color: #fca5a5;
                }

                QGroupBox {
                    border: 1px solid #1f3452;
                    border-radius: 16px;
                    padding: 18px;
                }

                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 0 8px;
                    color: #38d0a5;
                }

                QRadioButton {
                    spacing: 10px;
                }

                QComboBox#welcomeLanguageCombo,
                QComboBox#welcomeCountryCombo,
                QComboBox#welcomeCityCombo {
                    background-color: #1b2d4a;
                    border: 1px solid #1f3452;
                    border-radius: 10px;
                    padding: 8px 12px;
                    color: #f1f5ff;
                }

                QPushButton#welcomePrimaryButton {
                    background-color: #15803d;
                    color: #f8fafc;
                    border-radius: 10px;
                    padding: 12px 26px;
                    font-weight: 600;
                }

                QPushButton#welcomePrimaryButton:hover {
                    background-color: #166534;
                }

                QPushButton#welcomeSecondaryButton {
                    background-color: transparent;
                    border: 1px solid #1f3452;
                    border-radius: 10px;
                    padding: 10px 24px;
                    color: #f1f5ff;
                }

                QPushButton#welcomeSecondaryButton:hover {
                    border-color: #38d0a5;
                }
                """
            )
        else:
            self.setStyleSheet(
                """
                QDialog#WelcomeDialog {
                    background-color: #ffffff;
                    color: #0f172a;
                }

                QLabel#welcomeHeader {
                    color: #14532d;
                }

                QLabel#welcomeSubtitle {
                    color: #475569;
                }

                QLabel#welcomeHint {
                    color: #475569;
                }

                QLabel#welcomeError {
                    color: #b91c1c;
                }

                QGroupBox {
                    border: 1px solid #bbf7d0;
                    border-radius: 16px;
                    padding: 18px;
                }

                QGroupBox::title {
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 0 8px;
                    color: #15803d;
                }

                QRadioButton {
                    spacing: 10px;
                }

                QComboBox#welcomeLanguageCombo,
                QComboBox#welcomeCountryCombo,
                QComboBox#welcomeCityCombo {
                    background-color: #f1f5f9;
                    border: 1px solid #bbf7d0;
                    border-radius: 10px;
                    padding: 8px 12px;
                    color: #0f172a;
                }

                QPushButton#welcomePrimaryButton {
                    background-color: #15803d;
                    color: #ffffff;
                    border-radius: 10px;
                    padding: 12px 26px;
                    font-weight: 600;
                }

                QPushButton#welcomePrimaryButton:hover {
                    background-color: #166534;
                }

                QPushButton#welcomeSecondaryButton {
                    background-color: transparent;
                    border: 1px solid #bbf7d0;
                    border-radius: 10px;
                    padding: 10px 24px;
                    color: #14532d;
                }

                QPushButton#welcomeSecondaryButton:hover {
                    border-color: #4ade80;
                }
                """
            )


__all__ = ["WelcomeDialog"]
