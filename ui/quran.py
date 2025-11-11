"""Qur'an reading page and bookmark management."""
from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    from PyQt5 import QtCore, QtGui, QtWidgets  # type: ignore
except Exception:  # pragma: no cover - fallback path
    try:
        from PySide2 import QtCore, QtGui, QtWidgets  # type: ignore
    except Exception:
        from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore


@dataclass(frozen=True)
class SurahInfo:
    number: int
    name: str
    arabic_name: str
    ayah_count: int


_SURAH_METADATA: List[tuple[int, str, str, int]] = [
    (1, "Al-Fatiha", "الفاتحة", 7),
    (2, "Al-Baqarah", "البقرة", 286),
    (3, "Aal-Imran", "آل عمران", 200),
    (4, "An-Nisa", "النساء", 176),
    (5, "Al-Ma'idah", "المائدة", 120),
    (6, "Al-An'am", "الأنعام", 165),
    (7, "Al-A'raf", "الأعراف", 206),
    (8, "Al-Anfal", "الأنفال", 75),
    (9, "At-Tawbah", "التوبة", 129),
    (10, "Yunus", "يونس", 109),
    (11, "Hud", "هود", 123),
    (12, "Yusuf", "يوسف", 111),
    (13, "Ar-Ra'd", "الرعد", 43),
    (14, "Ibrahim", "إبراهيم", 52),
    (15, "Al-Hijr", "الحجر", 99),
    (16, "An-Nahl", "النحل", 128),
    (17, "Al-Isra", "الإسراء", 111),
    (18, "Al-Kahf", "الكهف", 110),
    (19, "Maryam", "مريم", 98),
    (20, "Ta-Ha", "طه", 135),
    (21, "Al-Anbiya", "الأنبياء", 112),
    (22, "Al-Hajj", "الحج", 78),
    (23, "Al-Mu'minun", "المؤمنون", 118),
    (24, "An-Nur", "النور", 64),
    (25, "Al-Furqan", "الفرقان", 77),
    (26, "Ash-Shu'ara", "الشعراء", 227),
    (27, "An-Naml", "النمل", 93),
    (28, "Al-Qasas", "القصص", 88),
    (29, "Al-Ankabut", "العنكبوت", 69),
    (30, "Ar-Rum", "الروم", 60),
    (31, "Luqman", "لقمان", 34),
    (32, "As-Sajdah", "السجدة", 30),
    (33, "Al-Ahzab", "الأحزاب", 73),
    (34, "Saba", "سبأ", 54),
    (35, "Fatir", "فاطر", 45),
    (36, "Ya-Sin", "يس", 83),
    (37, "As-Saffat", "الصافات", 182),
    (38, "Sad", "ص", 88),
    (39, "Az-Zumar", "الزمر", 75),
    (40, "Ghafir", "غافر", 85),
    (41, "Fussilat", "فصلت", 54),
    (42, "Ash-Shuraa", "الشورى", 53),
    (43, "Az-Zukhruf", "الزخرف", 89),
    (44, "Ad-Dukhan", "الدخان", 59),
    (45, "Al-Jathiyah", "الجاثية", 37),
    (46, "Al-Ahqaf", "الأحقاف", 35),
    (47, "Muhammad", "محمد", 38),
    (48, "Al-Fath", "الفتح", 29),
    (49, "Al-Hujurat", "الحجرات", 18),
    (50, "Qaf", "ق", 45),
    (51, "Adh-Dhariyat", "الذاريات", 60),
    (52, "At-Tur", "الطور", 49),
    (53, "An-Najm", "النجم", 62),
    (54, "Al-Qamar", "القمر", 55),
    (55, "Ar-Rahman", "الرحمن", 78),
    (56, "Al-Waqi'ah", "الواقعة", 96),
    (57, "Al-Hadid", "الحديد", 29),
    (58, "Al-Mujadila", "المجادلة", 22),
    (59, "Al-Hashr", "الحشر", 24),
    (60, "Al-Mumtahanah", "الممتحنة", 13),
    (61, "As-Saff", "الصف", 14),
    (62, "Al-Jumu'ah", "الجمعة", 11),
    (63, "Al-Munafiqun", "المنافقون", 11),
    (64, "At-Taghabun", "التغابن", 18),
    (65, "At-Talaq", "الطلاق", 12),
    (66, "At-Tahrim", "التحريم", 12),
    (67, "Al-Mulk", "الملك", 30),
    (68, "Al-Qalam", "القلم", 52),
    (69, "Al-Haqqah", "الحاقة", 52),
    (70, "Al-Ma'arij", "المعارج", 44),
    (71, "Nuh", "نوح", 28),
    (72, "Al-Jinn", "الجن", 28),
    (73, "Al-Muzzammil", "المزمل", 20),
    (74, "Al-Muddathir", "المدثر", 56),
    (75, "Al-Qiyamah", "القيامة", 40),
    (76, "Al-Insan", "الإنسان", 31),
    (77, "Al-Mursalat", "المرسلات", 50),
    (78, "An-Naba", "النبأ", 40),
    (79, "An-Nazi'at", "النازعات", 46),
    (80, "Abasa", "عبس", 42),
    (81, "At-Takwir", "التكوير", 29),
    (82, "Al-Infitar", "الانفطار", 19),
    (83, "Al-Mutaffifin", "المطففين", 36),
    (84, "Al-Inshiqaq", "الانشقاق", 25),
    (85, "Al-Buruj", "البروج", 22),
    (86, "At-Tariq", "الطارق", 17),
    (87, "Al-A'la", "الأعلى", 19),
    (88, "Al-Ghashiyah", "الغاشية", 26),
    (89, "Al-Fajr", "الفجر", 30),
    (90, "Al-Balad", "البلد", 20),
    (91, "Ash-Shams", "الشمس", 15),
    (92, "Al-Layl", "الليل", 21),
    (93, "Ad-Duha", "الضحى", 11),
    (94, "Ash-Sharh", "الشرح", 8),
    (95, "At-Tin", "التين", 8),
    (96, "Al-Alaq", "العلق", 19),
    (97, "Al-Qadr", "القدر", 5),
    (98, "Al-Bayyinah", "البينة", 8),
    (99, "Az-Zalzalah", "الزلزلة", 8),
    (100, "Al-Adiyat", "العاديات", 11),
    (101, "Al-Qari'ah", "القارعة", 11),
    (102, "At-Takathur", "التكاثر", 8),
    (103, "Al-Asr", "العصر", 3),
    (104, "Al-Humazah", "الهمزة", 9),
    (105, "Al-Fil", "الفيل", 5),
    (106, "Quraysh", "قريش", 4),
    (107, "Al-Ma'un", "الماعون", 7),
    (108, "Al-Kawthar", "الكوثر", 3),
    (109, "Al-Kafirun", "الكافرون", 6),
    (110, "An-Nasr", "النصر", 3),
    (111, "Al-Masad", "المسد", 5),
    (112, "Al-Ikhlas", "الإخلاص", 4),
    (113, "Al-Falaq", "الفلق", 5),
    (114, "An-Nas", "الناس", 6),
]

SURAH_DATA: List[SurahInfo] = [
    SurahInfo(number=number, name=name, arabic_name=arabic, ayah_count=count)
    for number, name, arabic, count in _SURAH_METADATA
]


class QuranPage(QtWidgets.QWidget):
    """Display all surahs, allow bookmarking, and render Arabic text."""

    bookmark_changed = QtCore.pyqtSignal(object)
    surah_selected = QtCore.pyqtSignal(int)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)

        self._strings: Dict[str, Any] = {}
        self._bookmark: Optional[Dict[str, Any]] = None
        self._current_surah: Optional[int] = None
        self._reading_placeholder = "Select a surah to begin reading."
        self._loading_text = "Loading surah..."
        self._error_template = "Unable to load this surah."

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        self.header_label = QtWidgets.QLabel("Qur'an Surahs")
        header_font = QtGui.QFont(self.header_label.font())
        header_font.setPointSize(18)
        header_font.setBold(True)
        self.header_label.setFont(header_font)
        self.header_label.setObjectName("quranHeader")
        layout.addWidget(self.header_label)

        self.view_stack = QtWidgets.QStackedWidget()
        layout.addWidget(self.view_stack, stretch=1)

        content_card = QtWidgets.QFrame()
        content_card.setObjectName("quranCard")
        card_layout = QtWidgets.QVBoxLayout(content_card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(16)

        self.surah_list = QtWidgets.QListWidget()
        self.surah_list.setObjectName("quranList")
        self.surah_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.surah_list.setUniformItemSizes(False)
        self.surah_list.setWordWrap(True)
        self._populate_surah_list()
        self.surah_list.currentItemChanged.connect(self._on_selection_changed)  # type: ignore
        card_layout.addWidget(self.surah_list)

        controls_row = QtWidgets.QHBoxLayout()
        controls_row.setSpacing(12)

        self.ayah_label = QtWidgets.QLabel("Ayah")
        self.ayah_label.setObjectName("quranAyahLabel")
        controls_row.addWidget(self.ayah_label)

        self.ayah_spinner = QtWidgets.QSpinBox()
        self.ayah_spinner.setObjectName("quranAyahSpinner")
        self.ayah_spinner.setRange(1, self._max_ayah_count())
        controls_row.addWidget(self.ayah_spinner)

        controls_row.addStretch(1)

        self.save_button = QtWidgets.QPushButton("Set Bookmark")
        self.save_button.setObjectName("quranSaveButton")
        self.save_button.clicked.connect(self._emit_bookmark)  # type: ignore
        controls_row.addWidget(self.save_button)

        self.clear_button = QtWidgets.QPushButton("Clear Bookmark")
        self.clear_button.setObjectName("quranClearButton")
        self.clear_button.clicked.connect(self._clear_bookmark)  # type: ignore
        controls_row.addWidget(self.clear_button)

        card_layout.addLayout(controls_row)

        self.bookmark_status = QtWidgets.QLabel("No bookmark saved.")
        self.bookmark_status.setObjectName("quranStatusLabel")
        card_layout.addWidget(self.bookmark_status)

        content_card.setLayout(card_layout)
        self.view_stack.addWidget(content_card)

        reader_container = QtWidgets.QWidget()
        reader_container.setObjectName("quranReader")
        reader_layout = QtWidgets.QVBoxLayout(reader_container)
        reader_layout.setContentsMargins(20, 20, 20, 20)
        reader_layout.setSpacing(12)

        header_row = QtWidgets.QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(12)

        self.back_button = QtWidgets.QPushButton("Back")
        self.back_button.setObjectName("quranBackButton")
        self.back_button.setCursor(QtCore.Qt.PointingHandCursor)
        self.back_button.clicked.connect(self._show_list_view)  # type: ignore
        header_row.addWidget(self.back_button, 0)
        header_row.addStretch(1)

        reader_layout.addLayout(header_row)

        self.reading_title = QtWidgets.QLabel(self._reading_placeholder)
        reading_title_font = QtGui.QFont(self.reading_title.font())
        reading_title_font.setPointSize(18)
        reading_title_font.setBold(True)
        self.reading_title.setFont(reading_title_font)
        self.reading_title.setObjectName("quranReadingTitle")
        reader_layout.addWidget(self.reading_title)

        self.reading_text = QtWidgets.QTextBrowser()
        self.reading_text.setObjectName("quranText")
        self.reading_text.setReadOnly(True)
        self.reading_text.setOpenExternalLinks(False)
        self.reading_text.setAcceptRichText(True)
        self.reading_text.setWordWrapMode(QtGui.QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.reading_text.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse | QtCore.Qt.TextSelectableByKeyboard
        )
        self.reading_text.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.reading_text.setAlignment(QtCore.Qt.AlignRight)
        self.reading_text.setHtml(self._placeholder_html(self._reading_placeholder))
        reader_layout.addWidget(self.reading_text, stretch=1)

        self.view_stack.addWidget(reader_container)
        self.view_stack.setCurrentWidget(content_card)

        self._reader_container = reader_container
        self._list_container = content_card
        self.refresh_reader_styles()

    # ------------------------------------------------------------------
    def apply_translations(self, translations: Dict[str, Any]) -> None:
        self._strings = translations
        self.header_label.setText(translations.get("quran_header", "Qur'an Surahs"))
        self.ayah_label.setText(translations.get("quran_ayah_label", "Ayah"))
        self.save_button.setText(translations.get("quran_save", "Set Bookmark"))
        self.clear_button.setText(translations.get("quran_clear", "Clear Bookmark"))
        self.back_button.setText(translations.get("quran_back", "Back"))
        self._reading_placeholder = translations.get("quran_reading_placeholder", self._reading_placeholder)
        self._loading_text = translations.get("quran_loading", self._loading_text)
        self._error_template = translations.get("quran_error", self._error_template)

        if not self._current_surah:
            self._set_reading_placeholder()
        self._update_bookmark_status(self._bookmark)

    def set_bookmark(self, bookmark: Optional[Dict[str, Any]]) -> None:
        self._bookmark = bookmark.copy() if isinstance(bookmark, dict) else None
        if self._bookmark:
            number = int(self._bookmark.get("surah", 0))
            ayah = max(1, int(self._bookmark.get("ayah", 1)))
            self._select_surah(number)
            self.ayah_spinner.setValue(ayah)
        else:
            self.surah_list.blockSignals(True)
            self.surah_list.clearSelection()
            self.surah_list.blockSignals(False)
            self.ayah_spinner.setValue(1)
        self._update_bookmark_status(self._bookmark)

    def ensure_default_selection(self) -> None:
        if self.surah_list.currentRow() == -1 and self.surah_list.count() > 0:
            self.surah_list.setCurrentRow(0)
        self._show_list_view()

    # ------------------------------------------------------------------
    def show_surah_loading(self, surah_number: int) -> None:
        surah = self._find_surah(surah_number)
        if not surah:
            return
        self._current_surah = surah.number
        self._show_reader_view()
        self.reading_title.setText(self._format_surah_title(surah))
        self.reading_text.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.reading_text.setAlignment(QtCore.Qt.AlignLeft)
        self.reading_text.setHtml(self._placeholder_html(self._loading_text))

    def update_surah_text(self, surah_number: int, text: Optional[str], error: Optional[str] = None) -> None:
        surah = self._find_surah(surah_number)
        if not surah:
            return
        self._current_surah = surah.number
        self._show_reader_view()
        self.reading_title.setText(self._format_surah_title(surah))
        if error:
            message = error or self._error_template
            self.reading_text.setLayoutDirection(QtCore.Qt.LeftToRight)
            self.reading_text.setAlignment(QtCore.Qt.AlignLeft)
            self.reading_text.setHtml(self._placeholder_html(message))
        else:
            rendered = text or ""
            self.reading_text.setLayoutDirection(QtCore.Qt.RightToLeft)
            self.reading_text.setAlignment(QtCore.Qt.AlignRight)
            self.reading_text.setHtml(rendered)
        self.reading_text.verticalScrollBar().setValue(0)

    # ------------------------------------------------------------------
    def _populate_surah_list(self) -> None:
        self.surah_list.clear()
        for surah in SURAH_DATA:
            item = QtWidgets.QListWidgetItem(
                f"{surah.number:03d} · {surah.name}\n{surah.arabic_name} ({surah.ayah_count})"
            )
            item.setData(QtCore.Qt.UserRole, surah)
            item.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            item.setSizeHint(QtCore.QSize(0, 56))
            self.surah_list.addItem(item)

    def _select_surah(self, number: int) -> None:
        for idx in range(self.surah_list.count()):
            item = self.surah_list.item(idx)
            surah: SurahInfo = item.data(QtCore.Qt.UserRole)
            if surah.number == number:
                if self.surah_list.currentRow() == idx:
                    self._on_selection_changed(item, item)
                else:
                    self.surah_list.setCurrentRow(idx)
                return

    def _emit_bookmark(self) -> None:
        item = self.surah_list.currentItem()
        if item is None:
            return
        surah: SurahInfo = item.data(QtCore.Qt.UserRole)
        ayah = self.ayah_spinner.value()
        bookmark = {
            "surah": surah.number,
            "surah_name": surah.name,
            "surah_name_ar": surah.arabic_name,
            "ayah": ayah,
        }
        self._bookmark = bookmark
        self._update_bookmark_status(bookmark)
        self.bookmark_changed.emit(bookmark)

    def _clear_bookmark(self) -> None:
        self._bookmark = None
        self.surah_list.blockSignals(True)
        self.surah_list.clearSelection()
        self.surah_list.blockSignals(False)
        self.ayah_spinner.setValue(1)
        self._update_bookmark_status(None)
        self.bookmark_changed.emit(None)
        self._show_list_view()

    def _on_selection_changed(
        self,
        current: Optional[QtWidgets.QListWidgetItem],
        previous: Optional[QtWidgets.QListWidgetItem],
    ) -> None:
        if current is None:
            self._current_surah = None
            self._set_reading_placeholder()
            return
        surah: SurahInfo = current.data(QtCore.Qt.UserRole)
        self._current_surah = surah.number
        self.ayah_spinner.blockSignals(True)
        self.ayah_spinner.setRange(1, max(1, surah.ayah_count))
        if self._bookmark and int(self._bookmark.get("surah", 0)) == surah.number:
            self.ayah_spinner.setValue(int(self._bookmark.get("ayah", 1)))
        else:
            self.ayah_spinner.setValue(1)
        self.ayah_spinner.blockSignals(False)
        self.show_surah_loading(surah.number)
        self.surah_selected.emit(surah.number)

    def _update_bookmark_status(self, bookmark: Optional[Dict[str, Any]]) -> None:
        if bookmark:
            surah_number = int(bookmark.get("surah", 0))
            ayah_number = int(bookmark.get("ayah", 1))
            name_en = bookmark.get("surah_name") or self._surah_name_en(surah_number)
            name_ar = bookmark.get("surah_name_ar") or self._surah_name_ar(surah_number)
            template = self._strings.get(
                "quran_status",
                "Reading {surah_en} / {surah_ar} · Ayah {ayah}",
            )
            self.bookmark_status.setText(
                template.format(
                    surah_en=name_en or surah_number,
                    surah_ar=name_ar or surah_number,
                    ayah=ayah_number,
                )
            )
        else:
            self.bookmark_status.setText(self._strings.get("quran_empty", "No bookmark saved."))

    def _set_reading_placeholder(self) -> None:
        self.reading_title.setText(self._reading_placeholder)
        self.reading_text.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.reading_text.setAlignment(QtCore.Qt.AlignRight)
        self.reading_text.setHtml(self._placeholder_html(self._reading_placeholder))

    @staticmethod
    def _max_ayah_count() -> int:
        return max(surah.ayah_count for surah in SURAH_DATA)

    @staticmethod
    def _surah_name_en(number: int) -> Optional[str]:
        for surah in SURAH_DATA:
            if surah.number == number:
                return surah.name
        return None

    @staticmethod
    def _surah_name_ar(number: int) -> Optional[str]:
        for surah in SURAH_DATA:
            if surah.number == number:
                return surah.arabic_name
        return None

    @staticmethod
    def _format_surah_title(surah: SurahInfo) -> str:
        return f"{surah.number:03d} · {surah.name} / {surah.arabic_name}"

    @staticmethod
    def _find_surah(number: int) -> Optional[SurahInfo]:
        for surah in SURAH_DATA:
            if surah.number == number:
                return surah
        return None

    def _show_list_view(self) -> None:
        if self.view_stack.currentWidget() is not self._list_container:
            self.view_stack.setCurrentWidget(self._list_container)
            self.surah_list.setFocus()

    def _show_reader_view(self) -> None:
        if self.view_stack.currentWidget() is not self._reader_container:
            self.view_stack.setCurrentWidget(self._reader_container)
        self.reading_text.setFocus()

    def _placeholder_html(self, message: str) -> str:
        safe = html.escape(message)
        return f"<div class='placeholder' dir='rtl'><p>{safe}</p></div>"

    def refresh_reader_styles(self) -> None:
        database = QtGui.QFontDatabase()
        preferred_fonts = [
            "KFGQPC Uthman Taha Naskh",
            "Mushaf Madinah",
            "Mushaf Madani",
            "KFGQPC Hafs",
            "Al Majeed Quranic Font",
            "Scheherazade New",
            "Amiri Quran",
        ]
        chosen_family: Optional[str] = None
        available = set(database.families())
        for family in preferred_fonts:
            if family in available:
                chosen_family = family
                break

        font = QtGui.QFont(self.reading_text.font())
        if chosen_family:
            font = QtGui.QFont(chosen_family)
        base_point = font.pointSize() if font.pointSize() > 0 else 28
        target_point = max(base_point, 32)
        font.setPointSize(target_point)
        font.setStyleStrategy(QtGui.QFont.PreferAntialias)
        font.setHintingPreference(QtGui.QFont.PreferNoHinting)
        self.reading_text.setFont(font)

        palette = self.reading_text.palette()
        base_color = palette.color(QtGui.QPalette.Text)
        background_color = palette.color(QtGui.QPalette.Base)
        is_dark_chrome = background_color.lightness() < 160
        if is_dark_chrome:
            text_color = "#f8fafc"
            accent = "#38d0a5"
            parchment = "#121c33"
            parchment_edge = "#22324f"
            placeholder_color = "#c7d2fe"
            background_fill = (
                "background: qlineargradient(x1:0, y1:0, x2:1, y2:1,"
                " stop:0 #0d1627, stop:1 #152342);"
            )
        else:
            text_color = base_color.name()
            accent = "#15803d"
            parchment = "#f9f1d6"
            parchment_edge = "#e0cfa2"
            placeholder_color = "#64748b"
            background_fill = (
                "background: qradialgradient(cx:0.5, cy:0.5, radius:1, fx:0.5, fy:0.4,"
                " stop:0 #fffdf4, stop:1 #f9f1d6);"
            )

        family_candidates = [font.family()] + preferred_fonts + ["Scheherazade New", "Amiri Quran", "Traditional Arabic", "Arial"]
        # Preserve order while removing duplicates
        ordered_families: List[str] = []
        for family in family_candidates:
            if family and family not in ordered_families:
                ordered_families.append(family)
        css_font_stack = ", ".join(f"'{family}'" for family in ordered_families)

        font_size = font.pointSize()
        number_size = max(font_size - 4, 22)

        stylesheet = (
            "body {"
            " direction: rtl;"
            " margin: 0;"
            " padding: 0 18px;"
            " background: transparent;"
            f" color: {text_color};"
            f" font-family: {css_font_stack};"
            f" font-size: {font_size}px;"
            " line-height: 2.5;"
            " text-align: justify;"
            " letter-spacing: 0.25px;"
            " word-spacing: 1.6px;"
            "}"
            "p {"
            " margin: 0 0 20px 0;"
            "}"
            ".placeholder {"
            " text-align: center;"
            " opacity: 0.9;"
            " padding: 32px 0;"
            f" color: {placeholder_color};"
            "}"
            "p.ayah {"
            " display: inline;"
            " margin: 0;"
            " padding: 0;"
            " text-align: inherit;"
            " text-indent: 0;"
            "}"
            "p.ayah::after {"
            " content: '\\2003';"
            "}"
            "p.ayah + p.ayah {"
            " margin-inline-start: 16px;"
            "}"
            "p.ayah.basmala {"
            " display: block;"
            " text-align: center;"
            " padding: 24px 0 12px;"
            " margin: 24px 0;"
            " font-weight: 600;"
            " letter-spacing: 1.4px;"
            " word-spacing: 4px;"
            "}"
            "p.ayah.basmala::after {"
            " content: none;"
            "}"
            "span.ayah-number {"
            " display: inline-flex;"
            " align-items: center;"
            " justify-content: center;"
            " min-width: 48px;"
            " min-height: 48px;"
            " padding: 6px;"
            " margin-inline-start: 14px;"
            " margin-inline-end: 6px;"
            " font-weight: 700;"
            f" font-size: {number_size}px;"
            f" color: {accent};"
            " letter-spacing: 1.1px;"
            f" background: radial-gradient(circle at 50% 45%, #fff 0%, {accent}1A 65%, {accent}33 100%);"
            f" box-shadow: 0 0 0 2px {accent}88, 0 6px 12px -6px {accent}55;"
            " clip-path: polygon(50% 0%, 65% 12%, 85% 10%, 100% 32%, 100% 68%, 85% 88%, 50% 100%, 35% 88%, 15% 90%, 0% 68%, 0% 32%, 15% 10%, 35% 12%);"
            " border: none;"
            "}"
        )

        self.reading_text.document().setDefaultStyleSheet(stylesheet)
        self.reading_text.setStyleSheet(
            "QTextBrowser#quranText {"
            f" {background_fill}"
            f" border: 2px solid {parchment_edge};"
            " border-radius: 18px;"
            " padding: 24px 18px;"
            "}"
            "QTextBrowser#quranText::viewport {"
            " border: none;"
            "}"
        )


__all__ = ["QuranPage", "SURAH_DATA", "SurahInfo"]
