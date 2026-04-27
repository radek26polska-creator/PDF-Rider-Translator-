"""
Okienko OCR - rozpoznawanie tekstu z PDF
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, 
    QProgressBar, QMessageBox, QLabel, QApplication
)
from PyQt5.QtCore import Qt
import fitz


class OcrDialog(QDialog):
    def __init__(self, doc, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.setWindowTitle("OCR - Rozpoznawanie tekstu")
        self.setMinimumSize(600, 500)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Informacja
        info = QLabel("Kliknij 'Analizuj dokument', aby wyciągnąć cały tekst z PDF")
        info.setStyleSheet("color: #cdd6f4; padding: 5px;")
        layout.addWidget(info)
        
        # Przycisk analizy
        self.analyze_btn = QPushButton("🔍 Analizuj dokument")
        self.analyze_btn.clicked.connect(self.analyze_document)
        self.analyze_btn.setFixedHeight(40)
        layout.addWidget(self.analyze_btn)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Pole tekstowe z wynikiem
        self.text_area = QTextEdit()
        self.text_area.setPlaceholderText("Po analizie pojawi się tutaj tekst...")
        self.text_area.setReadOnly(True)
        self.text_area.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 10px;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.text_area)
        
        # Przyciski dolne
        btn_layout = QHBoxLayout()
        self.copy_btn = QPushButton("📋 Kopiuj do schowka")
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        self.copy_btn.setEnabled(False)
        
        self.close_btn = QPushButton("Zamknij")
        self.close_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.copy_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #181825;
            }
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
        
    def analyze_document(self):
        if not self.doc:
            QMessageBox.warning(self, "Uwaga", "Brak dokumentu")
            return
            
        self.analyze_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        
        try:
            total_pages = len(self.doc)
            full_text = ""
            
            for i in range(total_pages):
                page = self.doc[i]
                text = page.get_text()
                if text:
                    full_text += text + "\n\n"
                self.progress.setValue(int((i + 1) / total_pages * 100))
                QApplication.processEvents()
                
            if full_text.strip():
                self.text_area.setText(full_text.strip())
                self.copy_btn.setEnabled(True)
                QMessageBox.information(self, "Sukces", f"Rozpoznano tekst z {total_pages} stron")
            else:
                self.text_area.setText("Nie znaleziono tekstu w dokumencie.\n\nMoże to być zeskanowany PDF. Funkcja OCR dla skanów będzie dostępna w przyszłości.")
                
        except Exception as e:
            QMessageBox.critical(self, "Błąd", str(e))
        finally:
            self.analyze_btn.setEnabled(True)
            self.progress.setVisible(False)
            
    def copy_to_clipboard(self):
        text = self.text_area.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            QMessageBox.information(self, "Sukces", "Tekst skopiowany do schowka")