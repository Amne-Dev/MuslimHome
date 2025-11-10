"""Audio playback utilities for the Adhan."""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Optional

from playsound3 import playsound

LOGGER = logging.getLogger(__name__)


class AdhanPlayer:
    """Manage playback for Adhan audio clips using playsound3."""

    def __init__(self, full_path: str, short_path: str) -> None:
        self.full_path = Path(full_path)
        self.short_path = Path(short_path)
        self._lock = threading.Lock()
        self._playback_thread: Optional[threading.Thread] = None

    def play(self, use_short: bool) -> None:
        """Play either the full or short Adhan in a background thread."""
        target = self.short_path if use_short else self.full_path
        if not target.exists():
            LOGGER.error("Adhan audio file missing: %s", target)
            return

        def _play() -> None:
            try:
                LOGGER.debug("Playing Adhan audio: %s", target)
                playsound(target.as_posix(), block=True)
            except Exception:  # pragma: no cover - backend dependent
                LOGGER.exception("Failed to play Adhan audio: %s", target)

        with self._lock:
            if self._playback_thread and self._playback_thread.is_alive():
                LOGGER.debug("Adhan already playing; skipping new request")
                return
            thread = threading.Thread(target=_play, daemon=True)
            self._playback_thread = thread
            thread.start()

    def stop(self) -> None:
        """playsound does not support stopping playback mid-stream."""
        with self._lock:
            if self._playback_thread and self._playback_thread.is_alive():
                LOGGER.info("playsound does not support stopping an active Adhan playback")
