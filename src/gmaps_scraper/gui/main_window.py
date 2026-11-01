"""
Hauptfenster (PySide6): Eingabe (Branche + Städte) oben, Start/Stop mit
Fortschrittsanzeige, Ergebnistabelle + Log, Export-Buttons unten.
Die Scraping-Logik selbst liegt in scraper.py/worker.py, hier geht es nur
um Darstellung und Nutzerinteraktion.
"""

from __future__ import annotations

import logging
import os

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QPlainTextEdit,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gmaps_scraper.extractor import BusinessRecord
from gmaps_scraper.logging_config import get_logger
from gmaps_scraper.scraper import ScrapeOptions, SearchQuery
from gmaps_scraper.storage import COLUMNS, deduplicate, records_to_dataframe, save_csv, save_excel

from .log_bridge import QtLogHandler
from .worker import ScraperWorker

logger = get_logger(__name__)

APP_TITLE = "Google Maps Lead Scraper"
DEFAULT_OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "GMapsScraper", "output")

EMAIL_CELL_BACKGROUND = QColor("#1e5631")
EMAIL_CELL_FOREGROUND = QColor("white")

TOGGLE_STYLE_ON = "background-color: #2e7d32; color: white; font-weight: bold;"
TOGGLE_STYLE_OFF = "background-color: #c62828; color: white; font-weight: bold;"

# Beide Buttons mit demselben Radius, damit sie optisch zusammenpassen.
# Start: dunkelgrün solange klickbar, grau sobald das Scraping läuft (disabled).
START_BUTTON_STYLE = """
    QPushButton { border-radius: 6px; padding: 6px 14px; }
    QPushButton:enabled { background-color: #1b5e20; color: white; }
    QPushButton:disabled { background-color: #9e9e9e; color: #616161; }
"""
# Stop: grau/inaktiv bis das Scraping läuft, dann rote Schrift auf schwarzem Grund.
STOP_BUTTON_STYLE = """
    QPushButton { border-radius: 6px; padding: 6px 14px; }
    QPushButton:enabled { background-color: black; color: red; }
    QPushButton:disabled { background-color: #9e9e9e; color: #616161; }
"""

# Hinzufügen: grün sobald im Eingabefeld Text steht, sonst normales Aussehen.
ADD_CITY_BUTTON_STYLE_ACTIVE = (
    "background-color: #2e7d32; color: white; font-weight: bold; border-radius: 6px; padding: 4px 10px;"
)
# Entfernen: dunkelrot sobald mindestens eine Stadt ausgewählt ist, sonst ausgegraut (disabled).
REMOVE_CITY_BUTTON_STYLE = """
    QPushButton { border-radius: 6px; padding: 4px 10px; }
    QPushButton:enabled { background-color: #8b0000; color: white; font-weight: bold; }
    QPushButton:disabled { background-color: #9e9e9e; color: #616161; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1100, 750)

        self.worker: ScraperWorker | None = None
        self.records: list[BusinessRecord] = []

        self._build_ui()
        self._connect_log_bridge()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)

        root_layout.addWidget(self._build_input_group())
        root_layout.addWidget(self._build_control_row())

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self._build_table())
        splitter.addWidget(self._build_log_view())
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        root_layout.addWidget(splitter, stretch=1)

        root_layout.addWidget(self._build_export_row())

    def _build_input_group(self) -> QGroupBox:
        group = QGroupBox("Suchanfrage")
        layout = QVBoxLayout(group)

        # Branche
        branche_row = QHBoxLayout()
        branche_row.addWidget(QLabel("Branche:"))
        self.branche_input = QLineEdit()
        self.branche_input.setPlaceholderText("z. B. Fitnessstudio")
        branche_row.addWidget(self.branche_input)
        layout.addLayout(branche_row)

        # Städte: Eingabe + Hinzufügen-Button + Liste
        stadt_row = QHBoxLayout()
        stadt_row.addWidget(QLabel("Stadt/Städte:"))
        self.stadt_input = QLineEdit()
        self.stadt_input.setPlaceholderText(
            "z. B. Düsseldorf (mehrere Städte auch Komma-getrennt möglich)"
        )
        self.stadt_input.returnPressed.connect(self._on_add_city_clicked)
        self.stadt_input.textChanged.connect(self._on_stadt_input_changed)
        stadt_row.addWidget(self.stadt_input)

        self.add_city_button = QPushButton("Hinzufügen")
        self.add_city_button.clicked.connect(self._on_add_city_clicked)
        stadt_row.addWidget(self.add_city_button)
        layout.addLayout(stadt_row)

        # Liste der hinzugefügten Städte + Entfernen-Button
        city_list_row = QHBoxLayout()
        self.city_list_widget = QListWidget()
        self.city_list_widget.setMaximumHeight(90)
        self.city_list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.city_list_widget.itemSelectionChanged.connect(self._on_city_selection_changed)
        city_list_row.addWidget(self.city_list_widget)

        self.remove_city_button = QPushButton("Ausgewählte\nentfernen")
        self.remove_city_button.setStyleSheet(REMOVE_CITY_BUTTON_STYLE)
        self.remove_city_button.setEnabled(False)
        self.remove_city_button.clicked.connect(self._on_remove_selected_cities)
        city_list_row.addWidget(self.remove_city_button)
        layout.addLayout(city_list_row)

        # Erweiterte Optionen
        options_row = QHBoxLayout()
        options_row.addWidget(QLabel("Scroll-Tiefe (mehr = mehr Ergebnisse, aber langsamer):"))
        self.scroll_count_input = QSpinBox()
        self.scroll_count_input.setRange(3, 60)
        self.scroll_count_input.setValue(20)
        options_row.addWidget(self.scroll_count_input)

        self.fetch_email_checkbox = QPushButton("E-Mail-Suche: An")
        self.fetch_email_checkbox.setCheckable(True)
        self.fetch_email_checkbox.setChecked(True)
        self.fetch_email_checkbox.toggled.connect(self._on_toggle_email_fetch)
        self._on_toggle_email_fetch(self.fetch_email_checkbox.isChecked())
        options_row.addWidget(self.fetch_email_checkbox)

        options_row.addStretch(1)
        layout.addLayout(options_row)

        return group

    def _build_control_row(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self.start_button = QPushButton("▶ Scraping starten")
        self.start_button.setStyleSheet(START_BUTTON_STYLE)
        self.start_button.clicked.connect(self._on_start_clicked)
        layout.addWidget(self.start_button)

        self.stop_button = QPushButton("■ Stoppen")
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet(STOP_BUTTON_STYLE)
        self.stop_button.clicked.connect(self._on_stop_clicked)
        layout.addWidget(self.stop_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar, stretch=1)

        self.status_label = QLabel("Bereit.")
        layout.addWidget(self.status_label)

        return container

    def _build_table(self) -> QWidget:
        container = QGroupBox("Ergebnisse")
        layout = QVBoxLayout(container)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        self.count_label = QLabel("0 Einträge")
        layout.addWidget(self.count_label)

        return container

    def _build_log_view(self) -> QWidget:
        container = QGroupBox("Protokoll")
        layout = QVBoxLayout(container)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        # Begrenzung, damit das Protokoll bei langen Läufen nicht endlos wächst
        self.log_view.setMaximumBlockCount(500)
        layout.addWidget(self.log_view)
        return container

    def _build_export_row(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        export_excel_button = QPushButton("Als Excel exportieren (.xlsx)")
        export_excel_button.clicked.connect(lambda: self._on_export_clicked("xlsx"))
        layout.addWidget(export_excel_button)

        export_csv_button = QPushButton("Als CSV exportieren (.csv)")
        export_csv_button.clicked.connect(lambda: self._on_export_clicked("csv"))
        layout.addWidget(export_csv_button)

        self.last_export_label = QLabel("Daten: –")
        self.last_export_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.last_export_label.setOpenExternalLinks(False)
        self.last_export_label.linkActivated.connect(self._on_open_exported_file)
        layout.addWidget(self.last_export_label)

        layout.addStretch(1)
        return container

    def _connect_log_bridge(self) -> None:
        """Hängt einen Qt-fähigen Logging-Handler an das Root-Logging, um Logzeilen live anzuzeigen."""
        self.log_handler = QtLogHandler()
        self.log_handler.setLevel(logging.INFO)
        self.log_handler.message_logged.connect(self._append_log_line)
        logging.getLogger().addHandler(self.log_handler)

    def _on_add_city_clicked(self) -> None:
        raw_text = self.stadt_input.text().strip()
        if not raw_text:
            return

        # Komma-getrennte Liste erlauben, z. B. "Köln, Bonn, Aachen"
        cities = [c.strip() for c in raw_text.split(",") if c.strip()]
        existing = {self.city_list_widget.item(i).text() for i in range(self.city_list_widget.count())}

        for city in cities:
            if city not in existing:
                self.city_list_widget.addItem(city)
                existing.add(city)

        self.stadt_input.clear()

    def _on_remove_selected_cities(self) -> None:
        for item in self.city_list_widget.selectedItems():
            self.city_list_widget.takeItem(self.city_list_widget.row(item))

    def _on_stadt_input_changed(self, text: str) -> None:
        self.add_city_button.setStyleSheet(ADD_CITY_BUTTON_STYLE_ACTIVE if text.strip() else "")

    def _on_city_selection_changed(self) -> None:
        self.remove_city_button.setEnabled(bool(self.city_list_widget.selectedItems()))

    def _on_toggle_email_fetch(self, checked: bool) -> None:
        self.fetch_email_checkbox.setText("E-Mail-Suche: An" if checked else "E-Mail-Suche: Aus")
        self.fetch_email_checkbox.setStyleSheet(TOGGLE_STYLE_ON if checked else TOGGLE_STYLE_OFF)

    def _collect_queries(self) -> list[SearchQuery] | None:
        branche = self.branche_input.text().strip()
        cities = [self.city_list_widget.item(i).text() for i in range(self.city_list_widget.count())]

        if not branche:
            QMessageBox.warning(self, APP_TITLE, "Bitte eine Branche eingeben (z. B. 'Fitnessstudio').")
            return None

        if not cities:
            QMessageBox.warning(
                self, APP_TITLE, "Bitte mindestens eine Stadt hinzufügen und mit 'Hinzufügen' bestätigen."
            )
            return None

        return [SearchQuery(branche=branche, stadt=stadt) for stadt in cities]

    def _on_start_clicked(self) -> None:
        queries = self._collect_queries()
        if not queries:
            return

        self.records.clear()
        self.table.setRowCount(0)
        self._update_count_label()

        options = ScrapeOptions(
            scroll_count=self.scroll_count_input.value(),
            fetch_emails=self.fetch_email_checkbox.isChecked(),
        )

        self.worker = ScraperWorker(queries, options)
        self.worker.progress_changed.connect(self._on_progress_changed)
        self.worker.record_found.connect(self._on_record_found)
        self.worker.finished_ok.connect(self._on_finished_ok)
        self.worker.failed.connect(self._on_failed)
        self.worker.chrome_missing.connect(self._on_chrome_missing)
        self.worker.finished.connect(self._on_thread_finished)

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("Scraping läuft ...")
        self.progress_bar.setRange(0, 0)  # unbestimmter Fortschritt, bis erste Query Ergebnisse liefert

        self.worker.start()

    def _on_stop_clicked(self) -> None:
        if self.worker is not None:
            self.status_label.setText("Wird gestoppt ...")
            self.stop_button.setEnabled(False)
            self.worker.request_stop()

    def _on_thread_finished(self) -> None:
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)

    def _on_progress_changed(self, current: int, total: int, message: str) -> None:
        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(current)
        self.status_label.setText(message)

    def _on_record_found(self, record: BusinessRecord) -> None:
        self.records.append(record)
        self._append_table_row(record)
        self._update_count_label()

    def _on_finished_ok(self, count: int) -> None:
        self.status_label.setText(f"Fertig. {count} Einträge gefunden.")

    def _on_failed(self, message: str) -> None:
        self.status_label.setText("Fehler beim Scraping.")
        QMessageBox.critical(self, APP_TITLE, f"Beim Scraping ist ein Fehler aufgetreten:\n\n{message}")

    def _on_chrome_missing(self, message: str) -> None:
        self.status_label.setText("Google Chrome nicht gefunden.")
        QMessageBox.critical(self, APP_TITLE, message)

    def _append_table_row(self, record: BusinessRecord) -> None:
        # Sortierung während des Einfügens abschalten, sonst landen Zellen
        # einer neuen Zeile (durch Zwischensortierung) in falschen Zeilen.
        self.table.setSortingEnabled(False)
        try:
            row_index = self.table.rowCount()
            self.table.insertRow(row_index)

            values = [record.name, record.address, record.phone, record.website, record.email]
            for col_index, value in enumerate(values):
                item = QTableWidgetItem(value or "N/A")
                if col_index == 4 and value:  # E-Mail gefunden -> optisch hervorheben
                    item.setBackground(EMAIL_CELL_BACKGROUND)
                    item.setForeground(EMAIL_CELL_FOREGROUND)
                self.table.setItem(row_index, col_index, item)
        finally:
            self.table.setSortingEnabled(True)

    def _update_count_label(self) -> None:
        self.count_label.setText(f"{len(self.records)} Einträge")

    def _append_log_line(self, level: str, formatted_message: str) -> None:
        self.log_view.appendPlainText(formatted_message)

    def _on_export_clicked(self, file_format: str) -> None:
        if not self.records:
            QMessageBox.information(self, APP_TITLE, "Es gibt noch keine Ergebnisse zum Exportieren.")
            return

        os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
        default_name = f"firmenliste.{file_format}"
        default_path = os.path.join(DEFAULT_OUTPUT_DIR, default_name)

        file_filter = "Excel-Datei (*.xlsx)" if file_format == "xlsx" else "CSV-Datei (*.csv)"
        filepath, _ = QFileDialog.getSaveFileName(self, "Ergebnisse exportieren", default_path, file_filter)
        if not filepath:
            return

        df = deduplicate(records_to_dataframe(self.records))
        try:
            if file_format == "xlsx":
                save_excel(df, filepath)
            else:
                save_csv(df, filepath)
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Export fehlgeschlagen:\n\n{exc}")
            return

        file_url = QUrl.fromLocalFile(filepath).toString()
        self.last_export_label.setText(f'Daten: <a href="{file_url}">{filepath}</a>')

        QMessageBox.information(self, APP_TITLE, f"Export erfolgreich gespeichert unter:\n{filepath}")

    def _on_open_exported_file(self, href: str) -> None:
        QDesktopServices.openUrl(QUrl(href))

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt-Namenskonvention)
        if self.worker is not None and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                APP_TITLE,
                "Das Scraping läuft noch. Wirklich beenden?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return
            self.worker.request_stop()
            self.worker.wait(5000)
        event.accept()
