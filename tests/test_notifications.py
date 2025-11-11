import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PyQt5 import QtCore, QtWidgets
except Exception:  # pragma: no cover - fallback path
    try:
        from PySide2 import QtCore, QtWidgets
    except Exception:  # pragma: no cover - fallback path
        from PySide6 import QtCore, QtWidgets

import pytest

from main import PrayerApp


@pytest.fixture(scope="module")
def qt_app():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    yield app


class _DummyWindow(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.status_messages: list[str] = []

    def set_status(self, text: str) -> None:
        self.status_messages.append(text)


class _DummyPlayer:
    def __init__(self) -> None:
        self.stop_called = False

    def stop(self) -> None:
        self.stop_called = True


class _NotificationHarness(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.window = _DummyWindow()
        self.tray_icon = None
        self._active_adhan_dialog = None
        self.adhan_player = _DummyPlayer()
        self._message_box_factory = lambda parent: _StubMessageBox(parent)

    def _on_adhan_dialog_destroyed(self, *_: object) -> None:
        self._active_adhan_dialog = None


class _StubMessageBox(QtCore.QObject):
    buttonClicked = QtCore.pyqtSignal(QtWidgets.QAbstractButton)
    destroyed = QtCore.pyqtSignal()

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self._buttons: list[QtWidgets.QAbstractButton] = []
        self._text: str = ""
        self._title: str = ""
        self._visible = False

    def setWindowTitle(self, text: str) -> None:
        self._title = text

    def setText(self, text: str) -> None:
        self._text = text

    def setIcon(self, *_: object) -> None:
        return None

    def setStandardButtons(self, *_: object) -> None:
        return None

    def setWindowModality(self, *_: object) -> None:
        return None

    def setAttribute(self, *_: object) -> None:
        return None

    def addButton(self, text: str, *_: object) -> QtWidgets.QAbstractButton:
        button = QtWidgets.QPushButton(text, parent=self.parent())
        self._buttons.append(button)
        return button

    def buttons(self) -> list[QtWidgets.QAbstractButton]:
        return list(self._buttons)

    def show(self) -> None:
        self._visible = True

    def raise_(self) -> None:
        return None

    def activateWindow(self) -> None:
        return None

    def isVisible(self) -> bool:
        return self._visible

    def close(self) -> None:
        self._visible = False
        self.destroyed.emit()


def test_snooze_button_stops_audio(qt_app: QtWidgets.QApplication) -> None:
    harness = _NotificationHarness()
    strings = {
        "adhan_notification_title": "Time for {prayer}",
        "adhan_notification_body": "It's time for {prayer}.",
        "adhan_notification_snooze": "Snooze",
        "adhan_notification_dismiss": "Dismiss",
    }

    PrayerApp._show_adhan_notification(harness, "Fajr", strings, audio_started=True)

    dialog = harness._active_adhan_dialog
    assert dialog is not None

    qt_app.processEvents()

    assert harness.window.status_messages[-1] == "It's time for Fajr."

    buttons = {button.text(): button for button in dialog.buttons()}
    assert "Snooze" in buttons and "Dismiss" in buttons

    dialog.buttonClicked.emit(buttons["Snooze"])
    qt_app.processEvents()

    assert harness.adhan_player.stop_called
    assert harness._active_adhan_dialog is None
