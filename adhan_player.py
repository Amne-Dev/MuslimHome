"""Audio playback utilities for the Adhan."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

try:  # Prefer PyQt5 multimedia bindings, fall back to Qt for Python variants
    from PyQt5 import QtCore, QtMultimedia  # type: ignore
except Exception:  # pragma: no cover - fallback path
    try:
        from PySide2 import QtCore, QtMultimedia  # type: ignore
    except Exception:
        from PySide6 import QtCore, QtMultimedia  # type: ignore

LOGGER = logging.getLogger(__name__)

try:  # Compatibility aliases for signals/slots
    Signal = QtCore.pyqtSignal  # type: ignore[attr-defined]
    Slot = QtCore.pyqtSlot  # type: ignore[attr-defined]
except AttributeError:  # pragma: no cover - PySide compatibility
    Signal = QtCore.Signal  # type: ignore[attr-defined]
    Slot = QtCore.Slot  # type: ignore[attr-defined]


class AdhanPlayer(QtCore.QObject):
    """Manage Adhan playback using Qt Multimedia for stop/snooze control."""

    playback_started = Signal(str)
    playback_finished = Signal()

    def __init__(
        self,
        full_path: str,
        short_path: str,
        parent: Optional[QtCore.QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.full_path = Path(full_path)
        self.short_path = Path(short_path)
        self._player = QtMultimedia.QMediaPlayer(self)
        self._audio_output = None
        if hasattr(QtMultimedia, "QAudioOutput"):
            self._audio_output = QtMultimedia.QAudioOutput()
            if hasattr(self._audio_output, "setParent"):
                self._audio_output.setParent(self)
            if hasattr(self._player, "setAudioOutput"):
                self._player.setAudioOutput(self._audio_output)
            self._audio_output.setVolume(1.0)
        else:
            # Qt5 API uses direct volume control on the player
            if hasattr(self._player, "setVolume"):
                self._player.setVolume(100)

        self._using_new_api = hasattr(self._player, "setSource")
        self._current_path: Optional[Path] = None
        self._was_emitting = False

        self._player.stateChanged.connect(self._on_state_changed)  # type: ignore
        if hasattr(self._player, "errorOccurred"):
            self._player.errorOccurred.connect(self._on_error)  # type: ignore
        elif hasattr(self._player, "error"):
            self._player.error.connect(self._on_error)  # type: ignore

    def play(self, use_short: bool) -> bool:
        """Play either the full or short Adhan clip."""
        target = self.short_path if use_short else self.full_path
        if not target.exists():
            LOGGER.error("Adhan audio file missing: %s", target)
            return False

        url = QtCore.QUrl.fromLocalFile(str(target))
        self._current_path = target
        self._was_emitting = False

        if self._using_new_api:
            # Qt6-style API
            if hasattr(self._player, "stop"):
                self._player.stop()
            self._player.setSource(url)
            if self._audio_output and hasattr(self._audio_output, "setVolume"):
                self._audio_output.setVolume(1.0)
        else:
            # Qt5 API using QMediaContent
            if hasattr(self._player, "stop"):
                self._player.stop()
            content = QtMultimedia.QMediaContent(url)  # type: ignore[attr-defined]
            self._player.setMedia(content)
            if hasattr(self._player, "setVolume"):
                self._player.setVolume(100)

        LOGGER.debug("Playing Adhan audio via Qt multimedia: %s", target)
        self._player.play()
        return True

    def stop(self) -> None:
        """Stop Adhan playback if it is currently running."""
        if self._player.state() != QtMultimedia.QMediaPlayer.StoppedState:
            LOGGER.debug("Stopping active Adhan playback")
            self._player.stop()

    def _on_state_changed(self, state: int) -> None:
        playing_state = QtMultimedia.QMediaPlayer.PlayingState
        stopped_state = QtMultimedia.QMediaPlayer.StoppedState
        paused_state = getattr(QtMultimedia.QMediaPlayer, "PausedState", stopped_state)

        if state == playing_state:
            self._was_emitting = True
            self.playback_started.emit(str(self._current_path or ""))
        elif state in (stopped_state, paused_state):
            if self._was_emitting:
                self._was_emitting = False
                self.playback_finished.emit()

    def _on_error(self, error: object) -> None:  # pragma: no cover - backend dependent
        # Log the error for troubleshooting; playback_finished will still be emitted via state change
        if hasattr(QtMultimedia.QMediaPlayer, "NoError") and error == QtMultimedia.QMediaPlayer.NoError:
            return
        LOGGER.error("Adhan playback error: %s", getattr(self._player, "errorString", lambda: "unknown")())
