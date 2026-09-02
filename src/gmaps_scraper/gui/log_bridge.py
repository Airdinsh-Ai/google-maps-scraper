"""
Verbindet logging mit der Qt-Oberfläche. Log-Aufrufe kommen aus dem
Worker-Thread, GUI-Änderungen sind aber nur im Haupt-Thread erlaubt - der
Handler sendet deshalb nur ein Signal, Qt übernimmt den Thread-Wechsel.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal


class QtLogHandler(logging.Handler, QObject):
    """Logging-Handler, der jede Logzeile als Qt-Signal weitergibt."""

    # Hinweis: Mehrfachvererbung von QObject + logging.Handler ist in PySide6
    # ein gängiges, funktionierendes Muster.
    message_logged = Signal(str, str)  # level, formatted_message

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)
        self.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%H:%M:%S"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            formatted = self.format(record)
            self.message_logged.emit(record.levelname, formatted)
        except Exception:
            pass
