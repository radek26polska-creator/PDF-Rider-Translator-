"""
Zakładka Tłumaczenie PDF - zintegrowana z PDFMathTranslate
Zachowuje tabele, formatowanie i strukturę dokumentu
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QFileDialog, QMessageBox, QProgressBar,
    QSplitter, QComboBox, QScrollArea, QApplication,
    QGroupBox, QRadioButton
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor
import fitz

# Dodaj ścieżkę do tools
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
tools_path = os.path.join(project_root, "tools")
if tools_path not in sys.path:
    sys.path.insert(0, tools_path)

# Import naszego prostego translatora
from app.tools.pdf_translator import SimplePDFTranslator

PDF2ZH_AVAILABLE = True  # Nasz translator zawsze dostępny


class PdfTranslateThread(QThread):
    """Wątek tłumaczenia PDF wykorzystujący SimplePDFTranslator"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, pdf_path, source_lang, target_lang, translator="openai", model=None):
        super().__init__()
        self.pdf_path = pdf_path
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.translator_name = translator
        self.model = model
        self._is_cancelled = False
        
    def cancel(self):
        self._is_cancelled = True
        
    def run(self):
        try:
            self.progress.emit(5, "Ładowanie dokumentu...")
            
            # Mapa języków
            lang_map = {
                "polski": "pl", "angielski": "en", "ukraiński": "uk",
                "hiszpański": "es", "niemiecki": "de", "francuski": "fr",
                "pl": "pl", "en": "en", "uk": "uk"
            }
            src = lang_map.get(self.source_lang, "pl")
            dst = lang_map.get(self.target_lang, "en")
            
            # Callback postępu
            def progress_cb(pct, msg):
                if not self._is_cancelled:
                    self.progress.emit(pct, msg)
                QApplication.processEvents()
                if self._is_cancelled:
                    raise Exception("Anulowano")
            
            self.progress.emit(10, "Inicjalizacja tłumacza...")
            
            # Stwórz translator
            translator = SimplePDFTranslator(
                pdf_path=self.pdf_path,
                lang_in=src,
                lang_out=dst,
                translator=self.translator_name,
                model=self.model,
                status_callback=lambda x: self.progress.emit(0, x)
            )
            
            self.progress.emit(20, f"Tłumaczenie z {self.source_lang} na {self.target_lang}...")
            
            # Tłumacz
            output_path = self.get_output_path()
            success = translator.save(output_path)
            translator.close()
            
            if not success:
                raise Exception("Tłumaczenie nieudane")
            
            self.progress.emit(100, "Gotowe!")
            self.finished.emit(output_path)
            
        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))
     
    def get_output_path(self):
        """Generuje ścieżkę dla przetłumaczonego pliku"""
        base_name = os.path.splitext(os.path.basename(str(self.pdf_path)))[0]
        temp_dir = tempfile.gettempdir()
        return os.path.join(temp_dir, f"{base_name}_przetlumaczony.pdf")


class PdfViewerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.page = None
        self.zoom_factor = 1.0
        self.setMinimumSize(400, 500)
        self.setStyleSheet("background-color: #1e1e2e;")
        
    def set_page(self, page, zoom=1.0):
        self.page = page
        self.zoom_factor = zoom
        self.update()
        
    def paintEvent(self, event):
        if self.page:
            try:
                matrix = fitz.Matrix(self.zoom_factor, self.zoom_factor)
                pix = self.page.get_pixmap(matrix=matrix)
                img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(img)
                
                painter = QPainter(self)
                painter.fillRect(self.rect(), QColor(30, 30, 46))
                x = (self.width() - pixmap.width()) // 2
                y = (self.height() - pixmap.height()) // 2
                if x < 0:
                    x = 0
                if y < 0:
                    y = 0
                painter.drawPixmap(x, y, pixmap)
                painter.end()
            except Exception as e:
                print(f"Błąd renderowania: {e}")


class TranslateTab(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.current_doc = None
        self.translated_doc = None
        self.translated_path = None
        self.pdf_path = None
        self.current_page_num = 0
        self.total_pages = 0
        self.zoom_level = 1.0
        self.translate_thread = None
        self.setup_ui()
        
        if not PDF2ZH_AVAILABLE:
            self._set_status("⚠️ Silnik tłumaczenia niedostępny - sprawdź instalację")
            self.translate_btn.setEnabled(False)
            self.translate_btn.setToolTip("Zainstaluj PDFMathTranslate w folderze tools/")
        else:
            self._set_status("Gotowy do tłumaczenia (zachowuje tabele!)")
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # === Pasek narzędzi ===
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        
        self.open_btn = QPushButton("📂 Otwórz PDF")
        self.open_btn.clicked.connect(self.open_pdf)
        self.open_btn.setStyleSheet(self._btn_style())
        toolbar.addWidget(self.open_btn)
        
        toolbar.addSpacing(20)
        
        src_layout = QHBoxLayout()
        src_label = QLabel("Z języka:")
        src_label.setStyleSheet("color: #cdd6f4;")
        src_layout.addWidget(src_label)
        
        self.source_lang = QComboBox()
        self.source_lang.addItems(["polski", "angielski", "ukraiński", "hiszpański", "niemiecki", "francuski"])
        self.source_lang.setCurrentText("polski")
        self.source_lang.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4; padding: 5px; border-radius: 4px;")
        src_layout.addWidget(self.source_lang)
        toolbar.addLayout(src_layout)
        
        arrow_label = QLabel("→")
        arrow_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #89b4fa;")
        toolbar.addWidget(arrow_label)
        
        dst_layout = QHBoxLayout()
        dst_label = QLabel("na język:")
        dst_label.setStyleSheet("color: #cdd6f4;")
        dst_layout.addWidget(dst_label)
        
        self.target_lang = QComboBox()
        self.target_lang.addItems(["angielski", "polski", "ukraiński", "hiszpański", "niemiecki", "francuski"])
        self.target_lang.setCurrentText("angielski")
        self.target_lang.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4; padding: 5px; border-radius: 4px;")
        dst_layout.addWidget(self.target_lang)
        toolbar.addLayout(dst_layout)
        
        toolbar.addStretch()
        
        self.translate_btn = QPushButton("🌐 ROZPOCZNIJ TŁUMACZENIE (zachowuje tabele)")
        self.translate_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 10px 25px;
                border-radius: 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
        """)
        self.translate_btn.clicked.connect(self.translate_pdf)
        self.translate_btn.setEnabled(False)
        toolbar.addWidget(self.translate_btn)
        
        self.cancel_btn = QPushButton("❌ Anuluj")
        self.cancel_btn.setStyleSheet(self._btn_style())
        self.cancel_btn.clicked.connect(self.cancel_translation)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setVisible(False)
        toolbar.addWidget(self.cancel_btn)
        
        layout.addLayout(toolbar)
        
        # === Pasek postępu ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 4px;
                text-align: center;
                color: #cdd6f4;
            }
            QProgressBar::chunk {
                background-color: #89b4fa;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("color: #a6adc8;")
        layout.addWidget(self.progress_label)
        
        # === Podgląd PDF ===
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #313244; width: 2px; }")
        
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_header = QLabel("📄 ORYGINAŁ")
        left_header.setAlignment(Qt.AlignCenter)
        left_header.setStyleSheet("font-weight: bold; color: #89b4fa; padding: 8px; background-color: #181825;")
        left_layout.addWidget(left_header)
        
        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setStyleSheet("background-color: #1e1e2e; border: none;")
        self.original_viewer = PdfViewerWidget()
        self.left_scroll.setWidget(self.original_viewer)
        left_layout.addWidget(self.left_scroll)
        
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        right_header = QLabel("🌍 TŁUMACZENIE")
        right_header.setAlignment(Qt.AlignCenter)
        right_header.setStyleSheet("font-weight: bold; color: #a6e3a1; padding: 8px; background-color: #181825;")
        right_layout.addWidget(right_header)
        
        self.right_scroll = QScrollArea()
        self.right_scroll.setWidgetResizable(True)
        self.right_scroll.setStyleSheet("background-color: #1e1e2e; border: none;")
        self.translated_viewer = PdfViewerWidget()
        self.right_scroll.setWidget(self.translated_viewer)
        right_layout.addWidget(self.right_scroll)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([500, 500])
        layout.addWidget(splitter, 1)
        
        # === Nawigacja ===
        nav_panel = QHBoxLayout()
        nav_panel.setSpacing(10)
        
        self.prev_btn = QPushButton("◀ Poprzednia")
        self.prev_btn.clicked.connect(self.prev_page)
        self.prev_btn.setEnabled(False)
        self.prev_btn.setStyleSheet(self._btn_style())
        nav_panel.addWidget(self.prev_btn)
        
        self.page_label = QLabel("Strona: 0 / 0")
        self.page_label.setStyleSheet("font-weight: bold; padding: 5px 15px; color: #cdd6f4;")
        nav_panel.addWidget(self.page_label)
        
        self.next_btn = QPushButton("Następna ▶")
        self.next_btn.clicked.connect(self.next_page)
        self.next_btn.setEnabled(False)
        self.next_btn.setStyleSheet(self._btn_style())
        nav_panel.addWidget(self.next_btn)
        
        nav_panel.addStretch()
        
        self.zoom_out_btn = QPushButton("🔍 -")
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        self.zoom_out_btn.setEnabled(False)
        self.zoom_out_btn.setStyleSheet(self._btn_style())
        nav_panel.addWidget(self.zoom_out_btn)
        
        self.zoom_label = QLabel("Zoom: 100%")
        self.zoom_label.setStyleSheet("padding: 5px; color: #a6adc8;")
        nav_panel.addWidget(self.zoom_label)
        
        self.zoom_in_btn = QPushButton("🔍 +")
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        self.zoom_in_btn.setEnabled(False)
        self.zoom_in_btn.setStyleSheet(self._btn_style())
        nav_panel.addWidget(self.zoom_in_btn)
        
        self.save_btn = QPushButton("💾 Zapisz tłumaczenie")
        self.save_btn.clicked.connect(self.save_translation)
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet(self._btn_style())
        nav_panel.addWidget(self.save_btn)
        
        layout.addLayout(nav_panel)
        self.setLayout(layout)
        
    def _btn_style(self):
        return """
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #89b4fa;
                color: #1a1a2e;
            }
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
        """
    
    def open_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Otwórz PDF do tłumaczenia", "", "Pliki PDF (*.pdf)")
        if path:
            try:
                if self.current_doc:
                    self.current_doc.close()
                if self.translated_doc:
                    self.translated_doc.close()
                    
                self.current_doc = fitz.open(path)
                self.pdf_path = path
                self.total_pages = len(self.current_doc)
                self.current_page_num = 0
                self.display_current_page()
                
                self.prev_btn.setEnabled(True)
                self.next_btn.setEnabled(self.total_pages > 1)
                self.zoom_in_btn.setEnabled(True)
                self.zoom_out_btn.setEnabled(True)
                self.translate_btn.setEnabled(True)
                self.page_label.setText(f"Strona: 1/{self.total_pages}")
                
                self._set_status(f"Otwarto: {os.path.basename(path)}")
                
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Nie można otworzyć pliku:\n{str(e)}")
    
    def display_current_page(self):
        if self.current_doc and self.current_page_num < len(self.current_doc):
            self.original_viewer.set_page(self.current_doc[self.current_page_num], self.zoom_level)
        if self.translated_doc and self.current_page_num < len(self.translated_doc):
            self.translated_viewer.set_page(self.translated_doc[self.current_page_num], self.zoom_level)
    
    def translate_pdf(self):
        if not self.pdf_path:
            QMessageBox.warning(self, "Uwaga", "Najpierw otwórz plik PDF!")
            return
            
        if not PDF2ZH_AVAILABLE:
            QMessageBox.critical(self, "Błąd", "Silnik tłumaczenia PDFMathTranslate nie jest dostępny.\n\nUpewnij się, że folder tools/ zawiera wszystkie pliki.")
            return
        
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.translate_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.translate_thread = PdfTranslateThread(
            self.pdf_path,
            self.source_lang.currentText(),
            self.target_lang.currentText()
        )
        self.translate_thread.progress.connect(self.update_progress)
        self.translate_thread.finished.connect(self.on_translate_finished)
        self.translate_thread.error.connect(self.on_translate_error)
        self.translate_thread.start()
        
        self._set_status("Rozpoczęto tłumaczenie...")
    
    def cancel_translation(self):
        if self.translate_thread and self.translate_thread.isRunning():
            self.translate_thread.cancel()
            self._set_status("Anulowanie tłumaczenia...")
    
    def update_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
        QApplication.processEvents()
    
    def on_translate_finished(self, translated_path):
        try:
            self.translated_doc = fitz.open(translated_path)
            self.translated_path = translated_path
            self.current_page_num = 0
            self.display_current_page()
            self.save_btn.setEnabled(True)
            self.page_label.setText(f"Strona: 1/{len(self.translated_doc)}")
            self._set_status("Tłumaczenie zakończone pomyślnie!")
            QMessageBox.information(self, "Sukces", "PDF został przetłumaczony!\n\nTłumaczenie zachowuje tabele i formatowanie.\nKliknij 'Zapisz tłumaczenie' aby zapisać plik.")
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie można otworzyć przetłumaczonego pliku:\n{str(e)}")
        finally:
            self.progress_bar.setVisible(False)
            self.progress_label.setVisible(False)
            self.translate_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            self.cancel_btn.setVisible(False)
    
    def on_translate_error(self, error_msg):
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.translate_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setVisible(False)
        QMessageBox.critical(self, "Błąd tłumaczenia", error_msg)
        self._set_status("Błąd tłumaczenia")
    
    def save_translation(self):
        if not self.translated_path or not os.path.exists(self.translated_path):
            QMessageBox.warning(self, "Uwaga", "Brak przetłumaczonego dokumentu do zapisu.")
            return
        
        base_name = os.path.splitext(os.path.basename(self.pdf_path))[0]
        default_name = f"{base_name}_przetlumaczony.pdf"
        
        save_path, _ = QFileDialog.getSaveFileName(self, "Zapisz przetłumaczony PDF", default_name, "Pliki PDF (*.pdf)")
        if save_path:
            try:
                shutil.copy2(self.translated_path, save_path)
                self._set_status(f"Zapisano: {os.path.basename(save_path)}")
                QMessageBox.information(self, "Sukces", f"Plik zapisany jako:\n{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Nie można zapisać pliku:\n{str(e)}")
    
    def next_page(self):
        doc = self.translated_doc if self.translated_doc else self.current_doc
        if doc and self.current_page_num < len(doc) - 1:
            self.current_page_num += 1
            self.display_current_page()
            self.page_label.setText(f"Strona: {self.current_page_num + 1}/{len(doc)}")
    
    def prev_page(self):
        doc = self.translated_doc if self.translated_doc else self.current_doc
        if doc and self.current_page_num > 0:
            self.current_page_num -= 1
            self.display_current_page()
            self.page_label.setText(f"Strona: {self.current_page_num + 1}/{len(doc)}")
    
    def zoom_in(self):
        self.zoom_level = min(3.0, self.zoom_level * 1.2)
        self.display_current_page()
        self.zoom_label.setText(f"Zoom: {int(self.zoom_level * 100)}%")
    
    def zoom_out(self):
        self.zoom_level = max(0.3, self.zoom_level / 1.2)
        self.display_current_page()
        self.zoom_label.setText(f"Zoom: {int(self.zoom_level * 100)}%")
    
    def _set_status(self, text):
        try:
            if self.main_window and self.main_window.status_label:
                self.main_window.status_label.setText(text)
            else:
                print(f"STATUS: {text}")
        except Exception as e:
            print(f"STATUS: {text}")