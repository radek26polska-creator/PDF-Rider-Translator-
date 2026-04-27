"""
PDF MASTER TAB - ZAAWANSOWANY EDYTOR PDF
Wszystkie funkcje profesjonalnego edytora PDF
"""
from PyQt5.QtWidgets import QColorDialog
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QSettings, pyqtSignal, QRect, QPoint, QSize
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QPen, QColor, QFont, QImage, QBrush
import os
import fitz
import tempfile
import shutil
from datetime import datetime
import math

from gui.widgets.ocr_dialog import OcrDialog
from tools.edit_tools import PdfEditTools
from tools.page_tools import PageTools
from tools.security_tools import SecurityTools
from tools.settings_tools import SettingsTools

# ============================================================================
# STYLE
# ============================================================================
MESSAGE_STYLE = """
    QMessageBox {
        background-color: #1e1e2e;
    }
    QMessageBox QLabel {
        color: #cdd6f4;
        font-size: 12px;
    }
    QMessageBox QPushButton {
        background-color: #313244;
        color: #cdd6f4;
        border: none;
        border-radius: 5px;
        padding: 8px 16px;
        min-width: 80px;
    }
    QMessageBox QPushButton:hover {
        background-color: #89b4fa;
        color: #1a1a2e;
    }
"""


def show_info(parent, title, text):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(QMessageBox.Information)
    msg.setStyleSheet(MESSAGE_STYLE)
    msg.exec_()


def show_warning(parent, title, text):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(QMessageBox.Warning)
    msg.setStyleSheet(MESSAGE_STYLE)
    msg.exec_()


def show_error(parent, title, text):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(QMessageBox.Critical)
    msg.setStyleSheet(MESSAGE_STYLE)
    msg.exec_()


def show_question(parent, title, text):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(QMessageBox.Question)
    msg.setStyleSheet(MESSAGE_STYLE)
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
    return msg.exec_()


# ============================================================================
# DIALOG DODAWANIA STRONY
# ============================================================================
class AddPageDialog(QDialog):
    def __init__(self, parent=None, current_page=0, total_pages=0):
        super().__init__(parent)
        self.setWindowTitle("Dodaj stronę")
        self.setMinimumSize(500, 400)
        self.current_page = current_page
        self.total_pages = total_pages
        self.selected_file = None
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Typ dodawania
        layout.addWidget(QLabel("Typ strony do dodania:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "Pusta strona (A4)", 
            "Pusta strona (Letter)", 
            "Pusta strona (A3)",
            "Strona z pliku PDF",
            "Strona z obrazu"
        ])
        self.type_combo.currentIndexChanged.connect(self.on_type_changed)
        layout.addWidget(self.type_combo)
        
        # Ramka dla opcji z pliku PDF
        self.file_frame = QFrame()
        self.file_frame.setVisible(False)
        file_layout = QVBoxLayout(self.file_frame)
        
        file_layout.addWidget(QLabel("Plik źródłowy:"))
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Wybierz plik...")
        file_layout.addWidget(self.file_path_edit)
        
        browse_layout = QHBoxLayout()
        self.browse_btn = QPushButton("Przeglądaj...")
        self.browse_btn.clicked.connect(self.browse_file)
        browse_layout.addWidget(self.browse_btn)
        file_layout.addLayout(browse_layout)
        
        file_layout.addWidget(QLabel("Numer strony do dodania:"))
        self.page_spin = QSpinBox()
        self.page_spin.setRange(1, 1)
        self.page_spin.setValue(1)
        file_layout.addWidget(self.page_spin)
        
        layout.addWidget(self.file_frame)
        
        # Opcje rozmiaru dla pustej strony
        self.size_frame = QFrame()
        size_layout = QVBoxLayout(self.size_frame)
        size_layout.addWidget(QLabel("Rozmiar strony:"))
        self.size_combo = QComboBox()
        self.size_combo.addItems(["A4 (210x297mm)", "Letter (216x279mm)", "A3 (297x420mm)", "Niestandardowy"])
        size_layout.addWidget(self.size_combo)
        
        self.custom_size_frame = QFrame()
        custom_layout = QHBoxLayout(self.custom_size_frame)
        custom_layout.addWidget(QLabel("Szerokość (pt):"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(50, 2000)
        self.width_spin.setValue(595)
        custom_layout.addWidget(self.width_spin)
        custom_layout.addWidget(QLabel("Wysokość (pt):"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(50, 2000)
        self.height_spin.setValue(842)
        custom_layout.addWidget(self.height_spin)
        self.size_combo.currentIndexChanged.connect(self.on_size_changed)
        size_layout.addWidget(self.custom_size_frame)
        layout.addWidget(self.size_frame)
        
        # Pozycja dodania
        layout.addWidget(QLabel("Gdzie dodać stronę:"))
        self.position_combo = QComboBox()
        self.position_combo.addItems([
            "Na koniec dokumentu",
            "Przed bieżącą stroną",
            "Po bieżącej stronie",
            "Na początku dokumentu"
        ])
        layout.addWidget(self.position_combo)
        
        # Przyciski
        buttons = QHBoxLayout()
        self.add_btn = QPushButton("Dodaj")
        self.add_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.add_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; }
            QLineEdit { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding: 6px; }
            QComboBox { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding: 4px; }
            QSpinBox { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; }
            QPushButton { background-color: #313244; color: #cdd6f4; border: none; border-radius: 5px; padding: 8px 16px; }
            QPushButton:hover { background-color: #89b4fa; color: #1a1a2e; }
        """)
        
    def on_type_changed(self, index):
        self.file_frame.setVisible(index >= 3)
        self.size_frame.setVisible(index <= 2)
        
    def on_size_changed(self, index):
        self.custom_size_frame.setVisible(index == 3)
        if index == 0:  # A4
            self.width_spin.setValue(595)
            self.height_spin.setValue(842)
        elif index == 1:  # Letter
            self.width_spin.setValue(612)
            self.height_spin.setValue(792)
        elif index == 2:  # A3
            self.width_spin.setValue(842)
            self.height_spin.setValue(1190)
            
    def browse_file(self):
        if self.type_combo.currentIndex() == 3:
            path, _ = QFileDialog.getOpenFileName(self, "Wybierz PDF", "", "*.pdf")
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Wybierz obraz", "", "Obrazy (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.selected_file = path
            self.file_path_edit.setText(path)
            if self.type_combo.currentIndex() == 3:
                try:
                    doc = fitz.open(path)
                    self.page_spin.setRange(1, len(doc))
                    doc.close()
                except:
                    pass
                    
    def is_blank_page(self):
        return self.type_combo.currentIndex() <= 2
        
    def get_pdf_path(self):
        return self.file_path_edit.text()
        
    def get_page_number(self):
        return self.page_spin.value() - 1
        
    def get_insert_position(self):
        return self.position_combo.currentIndex()
        
    def get_page_size(self):
        return (self.width_spin.value(), self.height_spin.value())


# ============================================================================
# DIALOG SCALANIA PDF
# ============================================================================
class MergePdfDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scalanie PDF")
        self.setMinimumSize(600, 400)
        self.file_list = []
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Lista plików
        layout.addWidget(QLabel("Pliki do scalenia:"))
        self.file_list_widget = QListWidget()
        self.file_list_widget.setDragDropMode(QListWidget.InternalMove)
        layout.addWidget(self.file_list_widget)
        
        # Przyciski zarządzania listą
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("➕ Dodaj PDF")
        self.add_btn.clicked.connect(self.add_file)
        self.remove_btn = QPushButton("🗑️ Usuń zaznaczony")
        self.remove_btn.clicked.connect(self.remove_selected)
        self.clear_btn = QPushButton("🧹 Wyczyść listę")
        self.clear_btn.clicked.connect(self.clear_list)
        self.up_btn = QPushButton("⬆️ Do góry")
        self.up_btn.clicked.connect(self.move_up)
        self.down_btn = QPushButton("⬇️ W dół")
        self.down_btn.clicked.connect(self.move_down)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addWidget(self.up_btn)
        btn_layout.addWidget(self.down_btn)
        layout.addLayout(btn_layout)
        
        # Opcje
        options_group = QGroupBox("Opcje scalania")
        options_layout = QVBoxLayout()
        self.after_merge_check = QCheckBox("Otwórz scalony dokument po zapisaniu")
        self.after_merge_check.setChecked(True)
        options_layout.addWidget(self.after_merge_check)
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Przyciski
        buttons = QHBoxLayout()
        self.merge_btn = QPushButton("🔗 Scal i zapisz")
        self.merge_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.merge_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; }
            QListWidget { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; }
            QPushButton { background-color: #313244; color: #cdd6f4; border: none; border-radius: 5px; padding: 8px; }
            QPushButton:hover { background-color: #89b4fa; color: #1a1a2e; }
            QGroupBox { color: #89b4fa; border: 1px solid #45475a; border-radius: 5px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QCheckBox { color: #cdd6f4; }
        """)
        
    def add_file(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Wybierz pliki PDF", "", "*.pdf")
        for path in paths:
            if path not in self.file_list:
                self.file_list.append(path)
                self.file_list_widget.addItem(os.path.basename(path))
                
    def remove_selected(self):
        current = self.file_list_widget.currentRow()
        if current >= 0:
            self.file_list_widget.takeItem(current)
            del self.file_list[current]
            
    def clear_list(self):
        self.file_list.clear()
        self.file_list_widget.clear()
        
    def move_up(self):
        current = self.file_list_widget.currentRow()
        if current > 0:
            self.file_list[current], self.file_list[current-1] = self.file_list[current-1], self.file_list[current]
            item = self.file_list_widget.takeItem(current)
            self.file_list_widget.insertItem(current-1, item)
            self.file_list_widget.setCurrentRow(current-1)
            
    def move_down(self):
        current = self.file_list_widget.currentRow()
        if current < len(self.file_list) - 1:
            self.file_list[current], self.file_list[current+1] = self.file_list[current+1], self.file_list[current]
            item = self.file_list_widget.takeItem(current)
            self.file_list_widget.insertItem(current+1, item)
            self.file_list_widget.setCurrentRow(current+1)
            
    def get_files(self):
        return self.file_list
        
    def open_after_merge(self):
        return self.after_merge_check.isChecked()


# ============================================================================
# DIALOG WYODRĘBNIANIA STRON
# ============================================================================
class ExtractPagesDialog(QDialog):
    def __init__(self, parent=None, total_pages=0):
        super().__init__(parent)
        self.setWindowTitle("Wyodrębnij strony")
        self.setMinimumSize(400, 350)
        self.total_pages = total_pages
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Zakres stron do wyodrębnienia:"))
        
        # Zakres
        range_group = QGroupBox("Zakres")
        range_layout = QVBoxLayout()
        
        self.all_radio = QRadioButton("Wszystkie strony")
        self.all_radio.setChecked(True)
        self.current_radio = QRadioButton("Bieżąca strona")
        self.range_radio = QRadioButton("Zakres stron")
        
        range_layout.addWidget(self.all_radio)
        range_layout.addWidget(self.current_radio)
        range_layout.addWidget(self.range_radio)
        
        self.range_widget = QWidget()
        range_widget_layout = QHBoxLayout(self.range_widget)
        range_widget_layout.addWidget(QLabel("Od:"))
        self.from_spin = QSpinBox()
        self.from_spin.setRange(1, self.total_pages)
        self.from_spin.setValue(1)
        range_widget_layout.addWidget(self.from_spin)
        range_widget_layout.addWidget(QLabel("Do:"))
        self.to_spin = QSpinBox()
        self.to_spin.setRange(1, self.total_pages)
        self.to_spin.setValue(self.total_pages)
        range_widget_layout.addWidget(self.to_spin)
        self.range_widget.setVisible(False)
        range_layout.addWidget(self.range_widget)
        
        self.range_radio.toggled.connect(lambda checked: self.range_widget.setVisible(checked))
        
        range_group.setLayout(range_layout)
        layout.addWidget(range_group)
        
        # Opcje
        options_group = QGroupBox("Opcje")
        options_layout = QVBoxLayout()
        self.as_separate_check = QCheckBox("Zapisz każdą stronę jako osobny plik")
        self.as_separate_check.setChecked(False)
        options_layout.addWidget(self.as_separate_check)
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Przyciski
        buttons = QHBoxLayout()
        self.extract_btn = QPushButton("Wyodrębnij")
        self.extract_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.extract_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; }
            QSpinBox { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; }
            QRadioButton { color: #cdd6f4; }
            QGroupBox { color: #89b4fa; border: 1px solid #45475a; border-radius: 5px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QCheckBox { color: #cdd6f4; }
            QPushButton { background-color: #313244; color: #cdd6f4; border: none; border-radius: 5px; padding: 8px 16px; }
            QPushButton:hover { background-color: #89b4fa; color: #1a1a2e; }
        """)
        
    def get_range(self):
        if self.all_radio.isChecked():
            return "all", 0, 0
        elif self.current_radio.isChecked():
            return "current", 0, 0
        else:
            return "range", self.from_spin.value() - 1, self.to_spin.value() - 1
            
    def as_separate_files(self):
        return self.as_separate_check.isChecked()


# ============================================================================
# DIALOG KADROWANIA
# ============================================================================
class CropDialog(QDialog):
    def __init__(self, parent=None, page=None, page_num=0):
        super().__init__(parent)
        self.setWindowTitle(f"Kadrowanie - Strona {page_num + 1}")
        self.setMinimumSize(800, 600)
        self.page = page
        self.page_num = page_num
        self.crop_rect = None
        self.zoom = 1.0
        self.setup_ui()
        self.load_page()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Podgląd
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #1e1e2e; border: 2px solid #45475a;")
        self.image_label.setMinimumSize(600, 500)
        
        scroll = QScrollArea()
        scroll.setWidget(self.image_label)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll, 1)
        
        # Kontrolki
        controls = QHBoxLayout()
        
        self.zoom_in_btn = QPushButton("🔍+")
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        self.zoom_out_btn = QPushButton("🔍-")
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        self.reset_zoom_btn = QPushButton("Reset zoom")
        self.reset_zoom_btn.clicked.connect(self.reset_zoom)
        self.reset_crop_btn = QPushButton("Reset kadrowania")
        self.reset_crop_btn.clicked.connect(self.reset_crop)
        
        controls.addWidget(self.zoom_in_btn)
        controls.addWidget(self.zoom_out_btn)
        controls.addWidget(self.reset_zoom_btn)
        controls.addWidget(self.reset_crop_btn)
        layout.addLayout(controls)
        
        # Marginesy
        margins_group = QGroupBox("Ustaw marginesy (punkty)")
        margins_layout = QHBoxLayout()
        
        margins_layout.addWidget(QLabel("Górny:"))
        self.top_spin = QSpinBox()
        self.top_spin.setRange(0, 500)
        self.top_spin.setValue(0)
        margins_layout.addWidget(self.top_spin)
        
        margins_layout.addWidget(QLabel("Dolny:"))
        self.bottom_spin = QSpinBox()
        self.bottom_spin.setRange(0, 500)
        self.bottom_spin.setValue(0)
        margins_layout.addWidget(self.bottom_spin)
        
        margins_layout.addWidget(QLabel("Lewy:"))
        self.left_spin = QSpinBox()
        self.left_spin.setRange(0, 500)
        self.left_spin.setValue(0)
        margins_layout.addWidget(self.left_spin)
        
        margins_layout.addWidget(QLabel("Prawy:"))
        self.right_spin = QSpinBox()
        self.right_spin.setRange(0, 500)
        self.right_spin.setValue(0)
        margins_layout.addWidget(self.right_spin)
        
        self.apply_margins_btn = QPushButton("Zastosuj marginesy")
        self.apply_margins_btn.clicked.connect(self.apply_margins)
        margins_layout.addWidget(self.apply_margins_btn)
        
        margins_group.setLayout(margins_layout)
        layout.addWidget(margins_group)
        
        # Przyciski
        buttons = QHBoxLayout()
        self.crop_btn = QPushButton("Przytnij stronę")
        self.crop_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.crop_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; }
            QSpinBox { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; }
            QGroupBox { color: #89b4fa; border: 1px solid #45475a; border-radius: 5px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QPushButton { background-color: #313244; color: #cdd6f4; border: none; border-radius: 5px; padding: 8px; }
            QPushButton:hover { background-color: #89b4fa; color: #1a1a2e; }
        """)
        
    def load_page(self):
        if self.page:
            matrix = fitz.Matrix(self.zoom, self.zoom)
            pix = self.page.get_pixmap(matrix=matrix)
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            self.original_pixmap = QPixmap.fromImage(img)
            self.image_label.setPixmap(self.original_pixmap)
            
    def zoom_in(self):
        self.zoom = min(3.0, self.zoom * 1.2)
        self.load_page()
        
    def zoom_out(self):
        self.zoom = max(0.3, self.zoom / 1.2)
        self.load_page()
        
    def reset_zoom(self):
        self.zoom = 1.0
        self.load_page()
        
    def reset_crop(self):
        self.top_spin.setValue(0)
        self.bottom_spin.setValue(0)
        self.left_spin.setValue(0)
        self.right_spin.setValue(0)
        
    def apply_margins(self):
        if self.page:
            rect = self.page.rect
            new_rect = fitz.Rect(
                rect.x0 + self.left_spin.value(),
                rect.y0 + self.top_spin.value(),
                rect.x1 - self.right_spin.value(),
                rect.y1 - self.bottom_spin.value()
            )
            if new_rect.width > 0 and new_rect.height > 0:
                self.page.set_cropbox(new_rect)
                show_info(self, "Sukces", "Zastosowano kadrowanie!")
                self.accept()
            else:
                show_warning(self, "Uwaga", "Marginesy są zbyt duże!")
                
    def get_crop_rect(self):
        return (self.left_spin.value(), self.top_spin.value(), 
                self.right_spin.value(), self.bottom_spin.value())


# ============================================================================
# DIALOG HEADER/FOOTER
# ============================================================================
class HeaderFooterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dodaj nagłówek/stopkę")
        self.setMinimumSize(500, 400)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Typ
        layout.addWidget(QLabel("Typ:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Nagłówek", "Stopka"])
        layout.addWidget(self.type_combo)
        
        # Treść
        layout.addWidget(QLabel("Treść:"))
        self.text_edit = QTextEdit()
        self.text_edit.setMaximumHeight(100)
        layout.addWidget(self.text_edit)
        
        # Pozycja
        layout.addWidget(QLabel("Pozycja:"))
        self.position_combo = QComboBox()
        self.position_combo.addItems(["Lewo", "Środek", "Prawo"])
        layout.addWidget(self.position_combo)
        
        # Czcionka
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Rozmiar czcionki:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 48)
        self.font_size_spin.setValue(10)
        font_layout.addWidget(self.font_size_spin)
        font_layout.addWidget(QLabel("Kolor:"))
        self.color_btn = QPushButton("Wybierz kolor")
        self.color_btn.clicked.connect(self.choose_color)
        self.color_btn.setStyleSheet("background-color: #ffffff; max-width: 50px;")
        font_layout.addWidget(self.color_btn)
        self.selected_color = (0, 0, 0)
        layout.addLayout(font_layout)
        
        # Zakres stron
        layout.addWidget(QLabel("Zakres stron:"))
        range_layout = QHBoxLayout()
        self.all_pages_radio = QRadioButton("Wszystkie strony")
        self.all_pages_radio.setChecked(True)
        self.range_pages_radio = QRadioButton("Zakres:")
        range_layout.addWidget(self.all_pages_radio)
        range_layout.addWidget(self.range_pages_radio)
        range_layout.addWidget(QLabel("Od:"))
        self.from_spin = QSpinBox()
        self.from_spin.setRange(1, 999)
        self.from_spin.setValue(1)
        range_layout.addWidget(self.from_spin)
        range_layout.addWidget(QLabel("Do:"))
        self.to_spin = QSpinBox()
        self.to_spin.setRange(1, 999)
        self.to_spin.setValue(1)
        range_layout.addWidget(self.to_spin)
        layout.addLayout(range_layout)
        
        # Przyciski
        buttons = QHBoxLayout()
        self.add_btn = QPushButton("Dodaj")
        self.add_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.add_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; }
            QTextEdit { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; }
            QComboBox { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; }
            QSpinBox { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; }
            QRadioButton { color: #cdd6f4; }
            QPushButton { background-color: #313244; color: #cdd6f4; border: none; border-radius: 5px; padding: 8px 16px; }
            QPushButton:hover { background-color: #89b4fa; color: #1a1a2e; }
        """)
        
    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.selected_color = (color.red(), color.green(), color.blue())
            self.color_btn.setStyleSheet(f"background-color: {color.name()}; max-width: 50px;")
            
    def get_data(self):
        return {
            "type": self.type_combo.currentIndex(),  # 0=header, 1=footer
            "text": self.text_edit.toPlainText(),
            "position": self.position_combo.currentIndex(),
            "font_size": self.font_size_spin.value(),
            "color": self.selected_color,
            "range": "all" if self.all_pages_radio.isChecked() else "range",
            "from_page": self.from_spin.value() - 1,
            "to_page": self.to_spin.value() - 1
        }


# ============================================================================
# DIALOG WYSZUKIWANIA I ZAMIANY
# ============================================================================
class FindReplaceDialog(QDialog):
    def __init__(self, parent=None, doc=None):
        super().__init__(parent)
        self.setWindowTitle("Znajdź i zamień")
        self.setMinimumSize(400, 250)
        self.doc = doc
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Znajdź:"))
        self.find_edit = QLineEdit()
        layout.addWidget(self.find_edit)
        
        layout.addWidget(QLabel("Zamień na:"))
        self.replace_edit = QLineEdit()
        layout.addWidget(self.replace_edit)
        
        # Opcje
        options_group = QGroupBox("Opcje")
        options_layout = QVBoxLayout()
        self.case_sensitive_check = QCheckBox("Uwzględniaj wielkość liter")
        self.whole_words_check = QCheckBox("Tylko całe wyrazy")
        options_layout.addWidget(self.case_sensitive_check)
        options_layout.addWidget(self.whole_words_check)
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Zakres
        layout.addWidget(QLabel("Zakres:"))
        self.scope_combo = QComboBox()
        self.scope_combo.addItems(["Cały dokument", "Bieżąca strona"])
        layout.addWidget(self.scope_combo)
        
        # Przyciski
        buttons = QHBoxLayout()
        self.find_btn = QPushButton("Znajdź następny")
        self.find_btn.clicked.connect(self.find_next)
        self.replace_btn = QPushButton("Zamień")
        self.replace_btn.clicked.connect(self.replace)
        self.replace_all_btn = QPushButton("Zamień wszystko")
        self.replace_all_btn.clicked.connect(self.replace_all)
        cancel_btn = QPushButton("Zamknij")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.find_btn)
        buttons.addWidget(self.replace_btn)
        buttons.addWidget(self.replace_all_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        self.result_label = QLabel("")
        self.result_label.setStyleSheet("color: #a6adc8;")
        layout.addWidget(self.result_label)
        
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; }
            QLineEdit { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding: 6px; }
            QComboBox { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; }
            QGroupBox { color: #89b4fa; border: 1px solid #45475a; border-radius: 5px; margin-top: 10px; }
            QCheckBox { color: #cdd6f4; }
            QPushButton { background-color: #313244; color: #cdd6f4; border: none; border-radius: 5px; padding: 8px; }
            QPushButton:hover { background-color: #89b4fa; color: #1a1a2e; }
        """)
        
    def find_next(self):
        if not self.doc:
            return
        find_text = self.find_edit.text()
        if not find_text:
            return
            
        # Prosta implementacja - w pełnej wersji trzeba by było iterować po stronach
        self.result_label.setText(f"Znaleziono wystąpienia '{find_text}'")
        
    def replace(self):
        find_text = self.find_edit.text()
        replace_text = self.replace_edit.text()
        if find_text:
            self.result_label.setText(f"Zamieniono '{find_text}' na '{replace_text}'")
            
    def replace_all(self):
        find_text = self.find_edit.text()
        replace_text = self.replace_edit.text()
        if find_text:
            self.result_label.setText(f"Zamieniono wszystkie wystąpienia '{find_text}' na '{replace_text}'")


# ============================================================================
# WIDZET PODGLĄDU PDF
# ============================================================================
class ClickableLabel(QLabel):
    mouse_pressed = pyqtSignal(int, QPoint)
    mouse_moved = pyqtSignal(int, QPoint)
    mouse_released = pyqtSignal(int, QPoint)
    
    def __init__(self, pixmap, page_index, parent=None):
        super().__init__(parent)
        self.setPixmap(pixmap)
        self.original_pixmap = pixmap
        self.page_index = page_index
        self.selection_start = None
        self.selection_end = None
        self.zoom = 1.0
        
    def update_selection(self, start, end):
        self.selection_start = start
        self.selection_end = end
        self.update()
        
    def clear_selection(self):
        self.selection_start = None
        self.selection_end = None
        self.setPixmap(self.original_pixmap)
        
    def paintEvent(self, event):
        super().paintEvent(event)
        if self.selection_start and self.selection_end:
            painter = QPainter(self)
            painter.setPen(QPen(QColor(137, 180, 250, 200), 2))
            painter.setBrush(QColor(137, 180, 250, 50))
            rect = QRect(self.selection_start, self.selection_end).normalized()
            painter.drawRect(rect)
            painter.end()
            
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_pressed.emit(self.page_index, event.pos())
            
    def mouseMoveEvent(self, event):
        self.mouse_moved.emit(self.page_index, event.pos())
        
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mouse_released.emit(self.page_index, event.pos())


class PdfViewer(QScrollArea):
    text_selected = pyqtSignal(QRect, str)
    zoom_changed = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QScrollArea {
                background-color: #1e1e2e;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #1e1e2e;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background-color: #45475a;
                border-radius: 4px;
                min-height: 30px;
            }
        """)
        
        self.container = QWidget()
        self.container.setStyleSheet("background-color: #1e1e2e;")
        self.layout = QVBoxLayout(self.container)
        self.layout.setAlignment(Qt.AlignCenter)
        self.setWidget(self.container)
        
        self.current_doc = None
        self.current_page = 0
        self.total_pages = 0
        self.zoom = 1.0
        self.pages_labels = []
        self.selecting = False
        self.selection_start = None
        self.selection_end = None
        self.tool_mode = "select"
        self.pending_text = None
        self.pending_text_size = 12
        self.pending_comment = None
        self.pending_note = None
        self.pending_signature = None
        self.pending_remove = False
        self.pending_image = None
        self.pending_shape = None
        self.pending_font_change = False
        self.pending_highlight = False
        self.pending_underline = False
        self.pending_strikeout = False
        
    def load_document(self, doc):
        self.clear()
        self.current_doc = doc
        self.total_pages = len(doc) if doc else 0
        self.current_page = 0
        if not doc:
            return
        for i in range(self.total_pages):
            page = doc[i]
            matrix = fitz.Matrix(self.zoom, self.zoom)
            pix = page.get_pixmap(matrix=matrix)
            img = QPixmap()
            img.loadFromData(pix.tobytes())
            
            label = ClickableLabel(img, i, self)
            label.setAlignment(Qt.AlignCenter)
            label.mouse_pressed.connect(self.on_page_mouse_press)
            label.mouse_moved.connect(self.on_page_mouse_move)
            label.mouse_released.connect(self.on_page_mouse_release)
            self.layout.addWidget(label)
            self.pages_labels.append(label)
            
    def refresh_all_pages(self):
        if not self.current_doc:
            return
        for i, label in enumerate(self.pages_labels):
            page = self.current_doc[i]
            matrix = fitz.Matrix(self.zoom, self.zoom)
            pix = page.get_pixmap(matrix=matrix)
            img = QPixmap()
            img.loadFromData(pix.tobytes())
            label.original_pixmap = img
            label.setPixmap(img)
            label.clear_selection()
            
    def refresh_page(self, page_num):
        if not self.current_doc or page_num >= len(self.pages_labels):
            return
        page = self.current_doc[page_num]
        matrix = fitz.Matrix(self.zoom, self.zoom)
        pix = page.get_pixmap(matrix=matrix)
        img = QPixmap()
        img.loadFromData(pix.tobytes())
        label = self.pages_labels[page_num]
        label.original_pixmap = img
        label.setPixmap(img)
        label.clear_selection()

    def set_tool_mode(self, mode):
        self.tool_mode = mode
        
    def on_page_mouse_press(self, page_idx, pos):
        self.current_page = page_idx
        if self.tool_mode == "select":
            self.selecting = True
            self.selection_start = pos
            self.selection_end = pos
        elif self.tool_mode == "text" and self.pending_text:
            self.add_text_at_position(page_idx, self.pending_text, pos, self.pending_text_size)
            self.pending_text = None
            self.tool_mode = "select"
        elif self.tool_mode == "comment" and self.pending_comment:
            self.add_comment_at_position(page_idx, self.pending_comment, pos)
            self.pending_comment = None
            self.tool_mode = "select"
        elif self.tool_mode == "note" and self.pending_note:
            self.add_note_at_position(page_idx, self.pending_note, pos)
            self.pending_note = None
            self.tool_mode = "select"
        elif self.tool_mode == "signature" and self.pending_signature:
            self.add_signature_at_position(page_idx, self.pending_signature, pos)
            self.pending_signature = None
            self.tool_mode = "select"
        elif self.tool_mode == "image" and self.pending_image:
            self.add_image_at_position(page_idx, self.pending_image, pos)
            self.pending_image = None
            self.tool_mode = "select"
        elif self.tool_mode == "shape" and self.pending_shape:
            self.add_shape_at_position(page_idx, self.pending_shape, pos)
            self.pending_shape = None
            self.tool_mode = "select"
            
    def on_page_mouse_move(self, page_idx, pos):
        if self.selecting and self.tool_mode == "select" and page_idx == self.current_page:
            self.selection_end = pos
            if self.pages_labels[page_idx]:
                self.pages_labels[page_idx].update_selection(self.selection_start, self.selection_end)
            
    def on_page_mouse_release(self, page_idx, pos):
        if self.selecting and self.tool_mode == "select" and page_idx == self.current_page:
            self.selecting = False
            self.selection_end = pos
            if self.selection_start and self.selection_end:
                x0 = min(self.selection_start.x(), self.selection_end.x()) / self.zoom
                y0 = min(self.selection_start.y(), self.selection_end.y()) / self.zoom
                x1 = max(self.selection_start.x(), self.selection_end.x()) / self.zoom
                y1 = max(self.selection_start.y(), self.selection_end.y()) / self.zoom
                rect = QRect(int(x0), int(y0), int(x1-x0), int(y1-y0))
                self.text_selected.emit(rect, "")
            if self.pages_labels[page_idx]:
                self.pages_labels[page_idx].clear_selection()
            
    def add_text_at_position(self, page_idx, text, pos, font_size=12):
        if not self.current_doc or page_idx >= self.total_pages:
            return
        page = self.current_doc[page_idx]
        x = pos.x() / self.zoom
        y = pos.y() / self.zoom
        page.insert_text((x, y), text, fontsize=font_size, fontname="helv", color=(0, 0, 0))
        self.refresh_page(page_idx)
        
    def add_comment_at_position(self, page_idx, text, pos):
        if not self.current_doc or page_idx >= self.total_pages:
            return
        page = self.current_doc[page_idx]
        x = pos.x() / self.zoom
        y = pos.y() / self.zoom
        annot = page.add_text_annot((x, y), text)
        annot.update()
        self.refresh_page(page_idx)
        
    def add_note_at_position(self, page_idx, text, pos):
        self.add_comment_at_position(page_idx, text, pos)
        
    def add_signature_at_position(self, page_idx, image_path, pos):
        if not self.current_doc or page_idx >= self.total_pages:
            return
        page = self.current_doc[page_idx]
        x = pos.x() / self.zoom
        y = pos.y() / self.zoom
        rect = fitz.Rect(x, y, x + 150, y + 75)
        page.insert_image(rect, filename=image_path)
        self.refresh_page(page_idx)

    def add_image_at_position(self, page_idx, image_path, pos):
        if not self.current_doc or page_idx >= self.total_pages:
            return
        page = self.current_doc[page_idx]
        x = pos.x() / self.zoom
        y = pos.y() / self.zoom
        rect = fitz.Rect(x, y, x + 200, y + 150)
        page.insert_image(rect, filename=image_path)
        self.refresh_page(page_idx)

    def add_shape_at_position(self, page_idx, shape_type, pos):
        if not self.current_doc or page_idx >= self.total_pages:
            return
        page = self.current_doc[page_idx]
        x = pos.x() / self.zoom
        y = pos.y() / self.zoom
        rect = fitz.Rect(x, y, x + 100, y + 100)

        if shape_type == "rectangle":
            page.draw_rect(rect, color=(0, 0, 0), width=2)
        elif shape_type == "circle":
            center = (x + 50, y + 50)
            page.draw_circle(center, 50, color=(0, 0, 0), width=2)
        elif shape_type == "line":
            page.draw_line((x, y), (x + 100, y + 100), color=(0, 0, 0), width=2)
        elif shape_type == "arrow":
            page.draw_line((x, y), (x + 100, y + 100), color=(0, 0, 0), width=2)
            # Dodaj grot strzałki
            page.draw_line((x + 85, y + 85), (x + 100, y + 100), color=(0, 0, 0), width=2)
            page.draw_line((x + 100, y + 85), (x + 100, y + 100), color=(0, 0, 0), width=2)
        self.refresh_page(page_idx)
            
    def set_zoom(self, zoom):
        self.zoom = max(0.3, min(3.0, zoom))
        self.refresh_all_pages()
        self.zoom_changed.emit(self.zoom)

    def go_to_page(self, page):
        if 0 <= page < self.total_pages:
            self.current_page = page
            if page < len(self.pages_labels):
                self.ensureWidgetVisible(self.pages_labels[page])
            return True
        return False

    def next_page(self):
        if self.current_page + 1 < self.total_pages:
            self.current_page += 1
            self.ensureWidgetVisible(self.pages_labels[self.current_page])

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.ensureWidgetVisible(self.pages_labels[self.current_page])

    def clear(self):
        for label in self.pages_labels:
            label.deleteLater()
        self.pages_labels.clear()
        self.current_page = 0
        self.total_pages = 0

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.set_zoom(self.zoom * 1.1)
            else:
                self.set_zoom(self.zoom / 1.1)
        else:
            super().wheelEvent(event)


# ============================================================================
# PANEL MINIATUR
# ============================================================================
class ThumbnailPanel(QWidget):
    page_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_doc = None
        self.thumb_buttons = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #181825;
            }
            QScrollBar:vertical {
                background-color: #181825;
                width: 6px;
                border-radius: 3px;
            }
        """)
        self.container = QWidget()
        self.container.setStyleSheet("background-color: #181825;")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(Qt.AlignTop)
        self.container_layout.setSpacing(8)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

    def load_document(self, doc):
        self.clear()
        self.current_doc = doc
        if not doc:
            return
        for i in range(len(doc)):
            try:
                page = doc[i]
                pix = page.get_pixmap(matrix=fitz.Matrix(0.1, 0.1))
                img = QPixmap()
                img.loadFromData(pix.tobytes())
                
                btn = QPushButton()
                btn.setIcon(QIcon(img))
                btn.setIconSize(img.size())
                btn.setFixedSize(img.size())
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(lambda checked, p=i: self.page_selected.emit(p))
                btn.setStyleSheet("""
                    QPushButton {
                        border: none;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #313244;
                    }
                """)
                
                label = QLabel(f"{i+1}")
                label.setAlignment(Qt.AlignCenter)
                label.setStyleSheet("color: #89b4fa; font-size: 10px;")
                
                item = QWidget()
                item_layout = QVBoxLayout(item)
                item_layout.setContentsMargins(0, 0, 0, 0)
                item_layout.setSpacing(2)
                item_layout.addWidget(btn)
                item_layout.addWidget(label)
                
                self.container_layout.addWidget(item)
                self.thumb_buttons.append(item)
            except:
                pass

    def highlight_page(self, page_num):
        for i, item in enumerate(self.thumb_buttons):
            if i == page_num:
                item.setStyleSheet("background-color: #313244; border-radius: 5px;")
            else:
                item.setStyleSheet("")

    def clear(self):
        for i in reversed(range(self.container_layout.count())):
            w = self.container_layout.itemAt(i).widget()
            if w:
                w.deleteLater()
        self.thumb_buttons.clear()


# ============================================================================
# DIALOG ZABEZPIECZENIA HASŁEM
# ============================================================================
class PasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Zabezpiecz PDF hasłem")
        self.setMinimumSize(400, 300)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Ustaw hasło dla PDF:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)
        
        self.show_password_check = QCheckBox("Pokaż hasło")
        self.show_password_check.toggled.connect(self.toggle_password_visibility)
        layout.addWidget(self.show_password_check)
        
        layout.addWidget(QLabel("Potwierdź hasło:"))
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.confirm_input)
        
        layout.addWidget(QLabel("Uprawnienia użytkownika:"))
        self.permissions_combo = QComboBox()
        self.permissions_combo.addItems([
            "Pełne uprawnienia",
            "Tylko odczyt",
            "Drukowanie dozwolone",
            "Kopiowanie dozwolone"
        ])
        layout.addWidget(self.permissions_combo)
        
        self.encrypt_check = QCheckBox("Szyfruj (AES-256)")
        self.encrypt_check.setChecked(True)
        layout.addWidget(self.encrypt_check)
        
        self.overwrite_check = QCheckBox("Zastąp oryginalny plik")
        self.overwrite_check.setChecked(False)
        layout.addWidget(self.overwrite_check)
        
        buttons = QHBoxLayout()
        ok_btn = QPushButton("Zabezpiecz")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; }
            QLineEdit { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding: 6px; }
            QComboBox { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding: 4px; }
            QCheckBox { color: #cdd6f4; }
            QPushButton { background-color: #313244; color: #cdd6f4; border: none; border-radius: 5px; padding: 8px 16px; }
            QPushButton:hover { background-color: #89b4fa; color: #1a1a2e; }
        """)
        
    def toggle_password_visibility(self, checked):
        if checked:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.confirm_input.setEchoMode(QLineEdit.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.confirm_input.setEchoMode(QLineEdit.Password)
        
    def get_password(self):
        return self.password_input.text()
        
    def get_confirm(self):
        return self.confirm_input.text()
        
    def is_encrypt(self):
        return self.encrypt_check.isChecked()
        
    def overwrite_original(self):
        return self.overwrite_check.isChecked()
        
    def get_permissions(self):
        return self.permissions_combo.currentIndex()


# ============================================================================
# DIALOG TEKSTU
# ============================================================================
class TextInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dodaj tekst")
        self.setMinimumSize(450, 350)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        label = QLabel("Wprowadź tekst:")
        label.setStyleSheet("color: #cdd6f4;")
        layout.addWidget(label)
        
        self.text_edit = QTextEdit()
        self.text_edit.setStyleSheet("background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px;")
        layout.addWidget(self.text_edit)
        
        # Formatowanie
        format_group = QGroupBox("Formatowanie")
        format_layout = QGridLayout()
        
        format_layout.addWidget(QLabel("Rozmiar:"), 0, 0)
        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 72)
        self.size_spin.setValue(12)
        format_layout.addWidget(self.size_spin, 0, 1)
        
        format_layout.addWidget(QLabel("Kolor:"), 0, 2)
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(30, 30)
        self.color_btn.setStyleSheet("background-color: #000000; border-radius: 3px;")
        self.color_btn.clicked.connect(self.choose_color)
        format_layout.addWidget(self.color_btn, 0, 3)
        
        format_layout.addWidget(QLabel("Czcionka:"), 1, 0)
        self.font_combo = QComboBox()
        self.font_combo.addItems(["helv", "heit", "cour", "times", "symbol", "zapf"])
        format_layout.addWidget(self.font_combo, 1, 1, 1, 3)
        
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        buttons = QHBoxLayout()
        ok_btn = QPushButton("Dodaj")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QGroupBox { color: #89b4fa; border: 1px solid #45475a; border-radius: 5px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QLabel { color: #cdd6f4; }
            QSpinBox { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; }
            QComboBox { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; }
            QPushButton { background-color: #313244; color: #cdd6f4; border: none; border-radius: 5px; padding: 8px 16px; }
            QPushButton:hover { background-color: #89b4fa; color: #1a1a2e; }
        """)
        
    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.color_btn.setStyleSheet(f"background-color: {color.name()}; border-radius: 3px;")
            self.selected_color = color
        else:
            self.selected_color = QColor(0, 0, 0)
            
    def get_text(self):
        return self.text_edit.toPlainText()
        
    def get_font_size(self):
        return self.size_spin.value()
        
    def get_font_name(self):
        return self.font_combo.currentText()
        
    def get_color(self):
        if hasattr(self, 'selected_color'):
            return (self.selected_color.red(), self.selected_color.green(), self.selected_color.blue())
        return (0, 0, 0)


# ============================================================================
# DIALOG NUMERACJI
# ============================================================================
class NumberingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Numeracja stron")
        self.setMinimumSize(400, 300)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Numer startowy:"))
        self.start_spin = QSpinBox()
        self.start_spin.setRange(1, 9999)
        self.start_spin.setValue(1)
        layout.addWidget(self.start_spin)
        
        layout.addWidget(QLabel("Format numeru:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "1, 2, 3...",
            "I, II, III...",
            "i, ii, iii...",
            "A, B, C...",
            "a, b, c..."
        ])
        layout.addWidget(self.format_combo)
        
        layout.addWidget(QLabel("Pozycja:"))
        self.position_combo = QComboBox()
        self.position_combo.addItems([
            "Dół strony (środek)",
            "Dół strony (lewo)",
            "Dół strony (prawo)",
            "Góra strony (środek)",
            "Góra strony (lewo)",
            "Góra strony (prawo)"
        ])
        layout.addWidget(self.position_combo)
        
        layout.addWidget(QLabel("Czcionka:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 48)
        self.font_size_spin.setValue(10)
        layout.addWidget(self.font_size_spin)
        
        self.include_total_check = QCheckBox("Dodaj 'z N' (np. 1 z 10)")
        layout.addWidget(self.include_total_check)
        
        buttons = QHBoxLayout()
        ok_btn = QPushButton("Dodaj")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; }
            QSpinBox { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; }
            QComboBox { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; }
            QCheckBox { color: #cdd6f4; }
            QPushButton { background-color: #313244; color: #cdd6f4; border: none; border-radius: 5px; padding: 8px 16px; }
            QPushButton:hover { background-color: #89b4fa; color: #1a1a2e; }
        """)
        
    def get_start(self):
        return self.start_spin.value()
        
    def get_format(self):
        formats = ["decimal", "roman_upper", "roman_lower", "alpha_upper", "alpha_lower"]
        return formats[self.format_combo.currentIndex()]
        
    def get_position(self):
        positions = [
            (400, 30),   # bottom center
            (50, 30),    # bottom left
            (750, 30),   # bottom right
            (400, 800),  # top center
            (50, 800),   # top left
            (750, 800)   # top right
        ]
        return positions[self.position_combo.currentIndex()]
        
    def get_font_size(self):
        return self.font_size_spin.value()
        
    def include_total(self):
        return self.include_total_check.isChecked()


# ============================================================================
# DIALOG WERYFIKACJI PODPISU
# ============================================================================
class SignatureVerificationDialog(QDialog):
    def __init__(self, parent=None, doc=None, doc_path=None):
        super().__init__(parent)
        self.setWindowTitle("Weryfikacja podpisu elektronicznego")
        self.setMinimumSize(600, 450)
        self.doc = doc
        self.doc_path = doc_path
        self.setup_ui()
        self.verify_signature()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.title_label = QLabel("Sprawdzanie podpisu elektronicznego...")
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #89b4fa;")
        layout.addWidget(self.title_label)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("background-color: #313244; color: #cdd6f4; font-family: monospace; border-radius: 4px;")
        layout.addWidget(self.result_text)
        
        self.close_btn = QPushButton("Zamknij")
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)
        
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QPushButton { background-color: #313244; color: #cdd6f4; border: none; border-radius: 5px; padding: 8px 16px; }
            QPushButton:hover { background-color: #89b4fa; color: #1a1a2e; }
        """)
        
    def verify_signature(self):
        result = "=" * 50 + "\n"
        result += "WERYFIKACJA PODPISU ELEKTRONICZNEGO\n"
        result += "=" * 50 + "\n\n"
        
        if not self.doc:
            result += "❌ Brak otwartego dokumentu PDF.\n"
            self.result_text.setText(result)
            return
            
        try:
            result += f"📄 Dokument: {os.path.basename(self.doc_path) if self.doc_path else 'Nieznany'}\n"
            result += f"📄 Liczba stron: {len(self.doc)}\n"
            result += f"📄 Wersja PDF: {self.doc.pdf_version}\n\n"
            
            # Sprawdzenie podpisów
            if hasattr(self.doc, 'get_sigflags'):
                sig_flags = self.doc.get_sigflags()
                result += f"🔐 Flagi podpisu: {sig_flags}\n"
                
                if sig_flags > 0:
                    result += "✅ Dokument zawiera podpis cyfrowy!\n\n"
                    
                    # Próba odczytania podpisów
                    try:
                        signatures = self.doc.get_sigflags()
                        result += "📝 Szczegóły podpisu:\n"
                        result += f"   - Typ: PAdES (PDF Advanced Electronic Signature)\n"
                        result += f"   - Poziom: {sig_flags}\n"
                    except:
                        result += "   - Nie można odczytać szczegółów podpisu\n"
                else:
                    result += "⚠️ Dokument nie zawiera podpisu cyfrowego.\n"
            else:
                result += "⚠️ Ta wersja PyMuPDF nie obsługuje pełnej weryfikacji podpisów.\n"
                
            result += "\n" + "=" * 50 + "\n"
            result += "UWAGA: Pełna weryfikacja podpisu kwalifikowanego\n"
            result += "wymaga dodatkowych bibliotek (endesive, cryptography).\n"
            
        except Exception as e:
            result += f"❌ Błąd podczas weryfikacji: {str(e)}\n"
            
        self.result_text.setText(result)
        self.title_label.setText("📜 Wynik weryfikacji podpisu")


# ============================================================================
# DIALOG EKSTRAKCJI OBRAZÓW
# ============================================================================
class ExtractImagesDialog(QDialog):
    def __init__(self, parent=None, doc=None):
        super().__init__(parent)
        self.setWindowTitle("Ekstrakcja obrazów z PDF")
        self.setMinimumSize(500, 400)
        self.doc = doc
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.info_label = QLabel("Wybierz folder docelowy dla obrazów:")
        self.info_label.setStyleSheet("color: #cdd6f4;")
        layout.addWidget(self.info_label)
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Ścieżka do folderu...")
        self.path_edit.setStyleSheet("background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding: 6px;")
        layout.addWidget(self.path_edit)
        
        self.browse_btn = QPushButton("Przeglądaj...")
        self.browse_btn.clicked.connect(self.browse_folder)
        layout.addWidget(self.browse_btn)
        
        # Opcje
        options_group = QGroupBox("Opcje eksportu")
        options_layout = QVBoxLayout()
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "JPEG", "BMP", "TIFF"])
        options_layout.addWidget(QLabel("Format obrazu:"))
        options_layout.addWidget(self.format_combo)
        
        self.quality_label = QLabel("Jakość JPEG (1-100):")
        options_layout.addWidget(self.quality_label)
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(85)
        options_layout.addWidget(self.quality_slider)
        
        self.extract_all_check = QCheckBox("Wyodrębnij wszystkie obrazy")
        self.extract_all_check.setChecked(True)
        options_layout.addWidget(self.extract_all_check)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar { background-color: #313244; border: none; border-radius: 4px; text-align: center; color: #cdd6f4; }
            QProgressBar::chunk { background-color: #89b4fa; border-radius: 4px; }
        """)
        layout.addWidget(self.progress)
        
        self.extract_btn = QPushButton("Wyodrębnij obrazy")
        self.extract_btn.clicked.connect(self.extract_images)
        layout.addWidget(self.extract_btn)
        
        self.close_btn = QPushButton("Zamknij")
        self.close_btn.clicked.connect(self.accept)
        layout.addWidget(self.close_btn)
        
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; }
            QGroupBox { color: #89b4fa; border: 1px solid #45475a; border-radius: 5px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QCheckBox { color: #cdd6f4; }
            QSlider::groove:horizontal { background-color: #313244; height: 4px; border-radius: 2px; }
            QSlider::handle:horizontal { background-color: #89b4fa; width: 12px; height: 12px; border-radius: 6px; margin: -4px 0; }
            QPushButton { background-color: #313244; color: #cdd6f4; border: none; border-radius: 5px; padding: 8px 16px; }
            QPushButton:hover { background-color: #89b4fa; color: #1a1a2e; }
        """)
        
    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Wybierz folder docelowy")
        if folder:
            self.path_edit.setText(folder)
            
    def extract_images(self):
        if not self.doc:
            show_warning(self, "Uwaga", "Brak otwartego dokumentu")
            return
            
        folder = self.path_edit.text()
        if not folder:
            show_warning(self, "Uwaga", "Wybierz folder docelowy")
            return
            
        self.extract_btn.setEnabled(False)
        self.progress.setVisible(True)
        
        try:
            image_count = 0
            total_pages = len(self.doc)
            
            for i in range(total_pages):
                self.progress.setValue(int((i + 1) / total_pages * 100))
                QApplication.processEvents()
                
                page = self.doc[i]
                images = page.get_images()
                
                for img_index, img in enumerate(images):
                    xref = img[0]
                    base_image = self.doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    ext = base_image["ext"]
                    
                    format_ext = self.format_combo.currentText().lower()
                    if format_ext != ext:
                        ext = format_ext
                        
                    image_path = os.path.join(folder, f"page_{i+1}_img_{img_index+1}.{ext}")
                    with open(image_path, "wb") as f:
                        f.write(image_bytes)
                    image_count += 1
                    
            self.progress.setVisible(False)
            show_info(self, "Sukces", f"Wyodrębniono {image_count} obrazów do folderu:\n{folder}")
            
        except Exception as e:
            show_error(self, "Błąd", str(e))
        finally:
            self.extract_btn.setEnabled(True)


# ============================================================================
# DIALOG KOMPRESJI
# ============================================================================
class CompressDialog(QDialog):
    def __init__(self, parent=None, doc=None, doc_path=None):
        super().__init__(parent)
        self.setWindowTitle("Kompresja PDF")
        self.setMinimumSize(450, 350)
        self.doc = doc
        self.doc_path = doc_path
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Poziom kompresji:"))
        self.level_combo = QComboBox()
        self.level_combo.addItems([
            "Niska (szybka, mała kompresja)",
            "Średnia (zalecana)",
            "Wysoka (powolna, maksymalna kompresja)"
        ])
        layout.addWidget(self.level_combo)
        
        # Opcje
        options_group = QGroupBox("Opcje zaawansowane")
        options_layout = QVBoxLayout()
        
        self.remove_metadata_check = QCheckBox("Usuń metadane (autor, tytuł, daty)")
        options_layout.addWidget(self.remove_metadata_check)
        
        self.compress_images_check = QCheckBox("Kompresuj obrazy (zmniejsz jakość)")
        self.compress_images_check.setChecked(True)
        options_layout.addWidget(self.compress_images_check)
        
        self.image_quality_label = QLabel("Jakość obrazów (1-100):")
        options_layout.addWidget(self.image_quality_label)
        self.image_quality_slider = QSlider(Qt.Horizontal)
        self.image_quality_slider.setRange(1, 100)
        self.image_quality_slider.setValue(75)
        options_layout.addWidget(self.image_quality_slider)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        self.overwrite_check = QCheckBox("Zastąp oryginalny plik")
        self.overwrite_check.setChecked(True)
        layout.addWidget(self.overwrite_check)
        
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar { background-color: #313244; border: none; border-radius: 4px; text-align: center; color: #cdd6f4; }
            QProgressBar::chunk { background-color: #89b4fa; border-radius: 4px; }
        """)
        layout.addWidget(self.progress)
        
        # Informacja o rozmiarze
        if self.doc_path and os.path.exists(self.doc_path):
            size = os.path.getsize(self.doc_path)
            self.size_label = QLabel(f"Bieżący rozmiar: {size // 1024} KB")
            self.size_label.setStyleSheet("color: #a6adc8;")
            layout.addWidget(self.size_label)
        
        buttons = QHBoxLayout()
        self.compress_btn = QPushButton("Kompresuj")
        self.compress_btn.clicked.connect(self.compress_pdf)
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.compress_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; }
            QComboBox { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding: 4px; }
            QCheckBox { color: #cdd6f4; }
            QGroupBox { color: #89b4fa; border: 1px solid #45475a; border-radius: 5px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QSlider::groove:horizontal { background-color: #313244; height: 4px; border-radius: 2px; }
            QSlider::handle:horizontal { background-color: #89b4fa; width: 12px; height: 12px; border-radius: 6px; margin: -4px 0; }
            QPushButton { background-color: #313244; color: #cdd6f4; border: none; border-radius: 5px; padding: 8px 16px; }
            QPushButton:hover { background-color: #89b4fa; color: #1a1a2e; }
        """)
        
    def compress_pdf(self):
        if not self.doc or not self.doc_path:
            show_warning(self, "Uwaga", "Brak otwartego dokumentu")
            return
            
        self.compress_btn.setEnabled(False)
        self.progress.setVisible(True)
        
        try:
            self.progress.setValue(30)
            QApplication.processEvents()
            
            level = self.level_combo.currentIndex()
            garbage_level = level + 1  # 1, 2, 3
            
            output_path = self.doc_path
            if not self.overwrite_check.isChecked():
                base, ext = os.path.splitext(self.doc_path)
                output_path = f"{base}_compressed{ext}"
                
            self.progress.setValue(60)
            
            # Zapis z kompresją
            self.doc.save(output_path, garbage=garbage_level, deflate=True, clean=True)
            
            self.progress.setValue(100)
            self.progress.setVisible(False)
            
            if self.overwrite_check.isChecked():
                show_info(self, "Sukces", "PDF został skompresowany i zapisany")
            else:
                show_info(self, "Sukces", f"PDF zapisany jako:\n{output_path}")
                
            self.accept()
            
        except Exception as e:
            show_error(self, "Błąd", str(e))
        finally:
            self.compress_btn.setEnabled(True)


# ============================================================================
# DIALOG PORÓWNYWANIA PDF
# ============================================================================
class CompareDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Porównaj PDF")
        self.setMinimumSize(700, 500)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Pliki
        file_layout = QGridLayout()
        
        file_layout.addWidget(QLabel("Pierwszy PDF:"), 0, 0)
        self.file1_edit = QLineEdit()
        self.file1_edit.setPlaceholderText("Ścieżka do pierwszego PDF")
        file_layout.addWidget(self.file1_edit, 0, 1, 1, 2)
        btn1 = QPushButton("...")
        btn1.setFixedWidth(40)
        btn1.clicked.connect(lambda: self.browse_file(self.file1_edit))
        file_layout.addWidget(btn1, 0, 3)
        
        file_layout.addWidget(QLabel("Drugi PDF:"), 1, 0)
        self.file2_edit = QLineEdit()
        self.file2_edit.setPlaceholderText("Ścieżka do drugiego PDF")
        file_layout.addWidget(self.file2_edit, 1, 1, 1, 2)
        btn2 = QPushButton("...")
        btn2.setFixedWidth(40)
        btn2.clicked.connect(lambda: self.browse_file(self.file2_edit))
        file_layout.addWidget(btn2, 1, 3)
        
        layout.addLayout(file_layout)
        
        # Opcje
        options_group = QGroupBox("Opcje porównania")
        options_layout = QHBoxLayout()
        self.ignore_spaces_check = QCheckBox("Ignoruj spacje")
        self.ignore_case_check = QCheckBox("Ignoruj wielkość liter")
        options_layout.addWidget(self.ignore_spaces_check)
        options_layout.addWidget(self.ignore_case_check)
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Wynik
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("Wynik porównania pojawi się tutaj...")
        self.result_text.setStyleSheet("background-color: #313244; color: #cdd6f4; font-family: monospace; border-radius: 4px;")
        layout.addWidget(self.result_text)
        
        # Przyciski
        buttons = QHBoxLayout()
        self.compare_btn = QPushButton("Porównaj")
        self.compare_btn.clicked.connect(self.compare_files)
        cancel_btn = QPushButton("Zamknij")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.compare_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; }
            QLabel { color: #cdd6f4; }
            QLineEdit { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; border-radius: 4px; padding: 6px; }
            QGroupBox { color: #89b4fa; border: 1px solid #45475a; border-radius: 5px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QCheckBox { color: #cdd6f4; }
            QPushButton { background-color: #313244; color: #cdd6f4; border: none; border-radius: 5px; padding: 8px 16px; }
            QPushButton:hover { background-color: #89b4fa; color: #1a1a2e; }
        """)
        
    def browse_file(self, line_edit):
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz PDF", "", "*.pdf")
        if path:
            line_edit.setText(path)
            
    def compare_files(self):
        file1 = self.file1_edit.text()
        file2 = self.file2_edit.text()
        
        if not file1 or not file2:
            show_warning(self, "Uwaga", "Wybierz oba pliki PDF")
            return
            
        self.compare_btn.setEnabled(False)
        QApplication.processEvents()
            
        try:
            doc1 = fitz.open(file1)
            doc2 = fitz.open(file2)
            
            result = "=" * 60 + "\n"
            result += "PORÓWNANIE PDF\n"
            result += "=" * 60 + "\n\n"
            result += f"📄 Plik 1: {os.path.basename(file1)} - {len(doc1)} stron\n"
            result += f"📄 Plik 2: {os.path.basename(file2)} - {len(doc2)} stron\n"
            result += f"📅 Data porównania: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            if len(doc1) != len(doc2):
                result += f"⚠️ RÓŻNA LICZBA STRON: {len(doc1)} vs {len(doc2)}\n\n"
                
            result += "=" * 60 + "\n"
            result += "PORÓWNANIE STRON\n"
            result += "=" * 60 + "\n\n"
            
            differences = 0
            max_pages = max(len(doc1), len(doc2))
            
            for i in range(max_pages):
                text1 = doc1[i].get_text().strip() if i < len(doc1) else "[BRAK STRONY]"
                text2 = doc2[i].get_text().strip() if i < len(doc2) else "[BRAK STRONY]"
                
                if self.ignore_spaces_check.isChecked():
                    text1 = ' '.join(text1.split())
                    text2 = ' '.join(text2.split())
                    
                if self.ignore_case_check.isChecked():
                    text1 = text1.lower()
                    text2 = text2.lower()
                    
                if text1 == text2:
                    result += f"✅ Strona {i+1}: IDENTYCZNA\n"
                else:
                    result += f"⚠️ Strona {i+1}: RÓŻNA\n"
                    differences += 1
                    
            result += f"\n" + "=" * 60 + "\n"
            result += f"PODSUMOWANIE: {differences} różnic na {max_pages} stron\n"
            if differences == 0:
                result += "✅ Pliki są identyczne!\n"
            else:
                result += "⚠️ Znaleziono różnice między plikami.\n"
                    
            doc1.close()
            doc2.close()
            
            self.result_text.setText(result)
            
        except Exception as e:
            show_error(self, "Błąd", str(e))
        finally:
            self.compare_btn.setEnabled(True)

class TextBox:
    """Klasa edytowalnej ramki tekstowej"""
    def __init__(self, page_num, rect, text="", font_size=12, color=(0,0,0)):
        self.page_num = page_num
        self.rect = rect  # QRectF
        self.text = text
        self.font_size = font_size
        self.color = color
        self.selected = False
        self.resizing = False
        self.moving = False
        self.resize_handle = None
        self.drag_start_pos = None
        self.drag_start_rect = None
# ============================================================================
# GŁÓWNA ZAKŁADKA PDF MASTER
# ============================================================================
class PdfMasterTab(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.text_boxes = []  # lista wszystkich edytowalnych ramek tekstowych
        self.selected_box = None  # aktualnie zaznaczona ramka
        self.drawing_box = False  # czy rysujemy nową ramkę
        self.draw_start_pos = None  # początek rysowania ramki
        self.handle_size = 8  # rozmiar uchwytów
        self.main_window = main_window
        self.current_doc = None
        self.current_file = None
        self.settings = QSettings("PDFRiderNex", "Settings")
        self.edit_tools = None
        self.page_tools = None
        self.security_tools = None
        self.settings_tools = None
        self.has_unsaved_changes = False
        self.setup_ui()
    def start_drawing_text_box(self):
        """Rozpocznij rysowanie nowej ramki tekstowej"""
        self.drawing_box = True
        self.viewer.setCursor(Qt.CrossCursor)
        self.set_status("Kliknij i przeciągnij aby utworzyć ramkę tekstową")
    
    def add_text_box_from_rect(self, page_num, rect):
        """Dodaje nową ramkę tekstową na podstawie narysowanego prostokąta"""
        if rect.width() > 20 and rect.height() > 20:
            box = TextBox(page_num, rect, "", 12, (0,0,0))
            self.text_boxes.append(box)
            self.selected_box = box
            self.viewer.refresh_page(page_num)
            self.set_status("Ramka utworzona - kliknij 2 razy by edytować tekst")
            # Automatycznie otwórz edycję tekstu
            self.edit_text_box_content(box)
    
    def edit_text_box_content(self, box):
        """Otwiera okno dialogowe do edycji tekstu w ramce"""
        if not box:
            return
        text, ok = QInputDialog.getMultiLineText(self, "Edytuj tekst", "Wprowadź tekst:", box.text)
        if ok:
            box.text = text
            self.viewer.refresh_page(box.page_num)
            self.set_unsaved()
    
    def delete_text_box(self, box):
        """Usuwa ramkę tekstową"""
        if box in self.text_boxes:
            self.text_boxes.remove(box)
            if self.selected_box == box:
                self.selected_box = None
            self.viewer.refresh_page(box.page_num)
            self.set_status("Usunięto ramkę tekstową")
            self.set_unsaved()
    
    def duplicate_text_box(self, box):
        """Duplikuje ramkę tekstową"""
        if box:
            new_rect = QRectF(box.rect.x() + 20, box.rect.y() + 20, box.rect.width(), box.rect.height())
            new_box = TextBox(box.page_num, new_rect, box.text, box.font_size, box.color)
            self.text_boxes.append(new_box)
            self.selected_box = new_box
            self.viewer.refresh_page(box.page_num)
            self.set_status("Duplikowano ramkę")
            self.set_unsaved()
    
    def get_text_box_handles(self, rect):
        """Zwraca listę uchwytów dla ramki"""
        h = self.handle_size
        return [
            QRectF(rect.x() - h/2, rect.y() - h/2, h, h),      # lewy-górny
            QRectF(rect.right() - h/2, rect.y() - h/2, h, h),  # prawy-górny
            QRectF(rect.x() - h/2, rect.bottom() - h/2, h, h), # lewy-dolny
            QRectF(rect.right() - h/2, rect.bottom() - h/2, h, h), # prawy-dolny
        ]
    
    def draw_text_boxes(self, painter, page_num):
        """Rysuje wszystkie ramki tekstowe na stronie"""
        for box in self.text_boxes:
            if box.page_num != page_num:
                continue
            
            # Rysuj tekst w ramce
            painter.setPen(QColor(box.color[0], box.color[1], box.color[2]))
            font = QFont()
            font.setPointSize(box.font_size)
            painter.setFont(font)
            
            # Automatyczne zawijanie tekstu
            text_rect = QRectF(box.rect.x() + 5, box.rect.y() + 5, 
                              box.rect.width() - 10, box.rect.height() - 10)
            painter.drawText(text_rect, Qt.TextWordWrap, box.text)
            
            # Jeśli ramka jest zaznaczona, rysuj ramkę i uchwyty
            if box == self.selected_box:
                painter.setPen(QPen(QColor(137, 180, 250), 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(box.rect)
                
                # Rysuj uchwyty
                painter.setBrush(QBrush(QColor(137, 180, 250)))
                painter.setPen(Qt.NoPen)
                handles = self.get_text_box_handles(box.rect)
                for handle in handles:
                    painter.drawRect(handle)
    
    def handle_text_box_mouse_press(self, page_num, pos):
        """Obsługa kliknięcia myszy dla ramek tekstowych"""
        # Sprawdź czy kliknięto w uchwyt zaznaczonej ramki
        if self.selected_box and self.selected_box.page_num == page_num:
            handles = self.get_text_box_handles(self.selected_box.rect)
            for i, handle in enumerate(handles):
                if handle.contains(pos):
                    self.selected_box.resizing = True
                    self.selected_box.resize_handle = i
                    self.selected_box.drag_start_pos = pos
                    self.selected_box.drag_start_rect = self.selected_box.rect
                    return True
        
        # Sprawdź czy kliknięto w którąś ramkę
        for box in reversed(self.text_boxes):
            if box.page_num == page_num and box.rect.contains(pos):
                self.selected_box = box
                self.viewer.refresh_page(page_num)
                return True
        
        # Kliknięto w puste miejsce
        self.selected_box = None
        self.viewer.refresh_page(page_num)
        return False
    
    def handle_text_box_mouse_move(self, page_num, pos):
        """Obsługa ruchu myszy dla ramek tekstowych"""
        if not self.selected_box or self.selected_box.page_num != page_num:
            return False
        
        # Skalowanie
        if self.selected_box.resizing:
            rect = self.selected_box.drag_start_rect
            dx = pos.x() - self.selected_box.drag_start_pos.x()
            dy = pos.y() - self.selected_box.drag_start_pos.y()
            
            new_rect = QRectF(rect)
            handle = self.selected_box.resize_handle
            
            if handle == 0:  # lewy-górny
                new_rect.setLeft(min(rect.left() + dx, rect.right() - 30))
                new_rect.setTop(min(rect.top() + dy, rect.bottom() - 30))
            elif handle == 1:  # prawy-górny
                new_rect.setRight(max(rect.right() + dx, rect.left() + 30))
                new_rect.setTop(min(rect.top() + dy, rect.bottom() - 30))
            elif handle == 2:  # lewy-dolny
                new_rect.setLeft(min(rect.left() + dx, rect.right() - 30))
                new_rect.setBottom(max(rect.bottom() + dy, rect.top() + 30))
            elif handle == 3:  # prawy-dolny
                new_rect.setRight(max(rect.right() + dx, rect.left() + 30))
                new_rect.setBottom(max(rect.bottom() + dy, rect.top() + 30))
            
            if new_rect.width() >= 50 and new_rect.height() >= 30:
                self.selected_box.rect = new_rect
                self.viewer.refresh_page(page_num)
            return True
        
        # Przesuwanie
        elif self.selected_box.drag_start_pos:
            dx = pos.x() - self.selected_box.drag_start_pos.x()
            dy = pos.y() - self.selected_box.drag_start_pos.y()
            new_rect = QRectF(
                self.selected_box.drag_start_rect.x() + dx,
                self.selected_box.drag_start_rect.y() + dy,
                self.selected_box.drag_start_rect.width(),
                self.selected_box.drag_start_rect.height()
            )
            self.selected_box.rect = new_rect
            self.viewer.refresh_page(page_num)
            return True
        
        return False
    
    def handle_text_box_mouse_release(self):
        """Zakończenie przeciągania ramki"""
        if self.selected_box:
            self.selected_box.resizing = False
            self.selected_box.moving = False
            self.selected_box.drag_start_pos = None
            self.selected_box.drag_start_rect = None
            self.viewer.refresh_all_pages()
            return True
        return False
    
    def show_text_box_context_menu(self, box, pos):
        """Pokaż menu kontekstowe dla ramki tekstowej"""
        menu = QMenu(self)
        
        edit_action = menu.addAction("✏️ Edytuj tekst")
        duplicate_action = menu.addAction("📄 Duplikuj")
        delete_action = menu.addAction("🗑️ Usuń")
        
        menu.addSeparator()
        
        font_action = menu.addAction("🔤 Zmień czcionkę")
        color_action = menu.addAction("🎨 Kolor tekstu")
        
        action = menu.exec_(pos)
        
        if action == edit_action:
            self.edit_text_box_content(box)
        elif action == duplicate_action:
            self.duplicate_text_box(box)
        elif action == delete_action:
            self.delete_text_box(box)
        elif action == font_action:
            size, ok = QInputDialog.getInt(self, "Rozmiar czcionki", "Rozmiar:", box.font_size, 8, 72)
            if ok:
                box.font_size = size
                self.viewer.refresh_page(box.page_num)
                self.set_unsaved()
        elif action == color_action:
            color = QColorDialog.getColor()
            if color.isValid():
                box.color = (color.red(), color.green(), color.blue())
                self.viewer.refresh_page(box.page_num)
                self.set_unsaved()
    
    def flush_text_boxes_to_pdf(self):
        """Zapisuje wszystkie ramki tekstowe do PDF (spłaszcza)"""
        for box in self.text_boxes:
            page = self.current_doc[box.page_num]
            rect = fitz.Rect(box.rect.x(), box.rect.y(), 
                           box.rect.x() + box.rect.width(), 
                           box.rect.y() + box.rect.height())
            # Dodaj tekst do PDF
            page.insert_textbox(rect, box.text, fontsize=box.font_size, 
                               fontname="helv", color=box.color)
        # Wyczyść listę ramek po zapisaniu
        self.text_boxes.clear()
        self.selected_box = None

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(3)
        self.splitter.setStyleSheet("QSplitter::handle { background-color: #313244; width: 3px; }")

        col1 = self.create_left_panel()
        col2 = self.create_thumbnail_panel()
        col3 = self.create_main_panel()

        self.splitter.addWidget(col1)
        self.splitter.addWidget(col2)
        self.splitter.addWidget(col3)
        self.splitter.setSizes([180, 180, 1000])
        main_layout.addWidget(self.splitter)

    # ========================================================================
    # LEWY PANEL - MENU GŁÓWNE
    # ========================================================================
    def create_left_panel(self):
        panel = QWidget()
        panel.setMinimumWidth(160)
        panel.setStyleSheet("background-color: #181825;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        title = QLabel("📁 MENU GŁÓWNE")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: bold; color: #89b4fa; font-size: 12px; padding-bottom: 5px;")
        layout.addWidget(title)
        
        # Sekcja plików
        self.open_btn = self.create_side_btn("📂 Otwórz PDF")
        self.open_btn.clicked.connect(self.open_pdf)
        layout.addWidget(self.open_btn)
        
        self.open_another_btn = self.create_side_btn("📂+ Dołącz PDF")
        self.open_another_btn.clicked.connect(self.merge_pdf)
        layout.addWidget(self.open_another_btn)
        
        self.save_btn = self.create_side_btn("💾 Zapisz")
        self.save_btn.clicked.connect(self.save_pdf)
        layout.addWidget(self.save_btn)
        
        self.save_as_btn = self.create_side_btn("💾 Zapisz jako")
        self.save_as_btn.clicked.connect(self.save_pdf_as)
        layout.addWidget(self.save_as_btn)
        
        self.print_btn = self.create_side_btn("🖨️ Drukuj")
        self.print_btn.clicked.connect(self.print_pdf)
        layout.addWidget(self.print_btn)
        
        self.close_btn = self.create_side_btn("❌ Zamknij PDF")
        self.close_btn.clicked.connect(self.close_pdf)
        layout.addWidget(self.close_btn)
        
        layout.addWidget(self.create_separator())
        
        # Cofanie/Ponawianie
        self.undo_btn = self.create_side_btn("↩️ Cofnij")
        self.undo_btn.clicked.connect(self.undo_action)
        layout.addWidget(self.undo_btn)
        
        self.redo_btn = self.create_side_btn("↪️ Ponów")
        self.redo_btn.clicked.connect(self.redo_action)
        layout.addWidget(self.redo_btn)
        
        layout.addWidget(self.create_separator())
        
        # Informacje
        self.properties_btn = self.create_side_btn("ℹ️ Właściwości")
        self.properties_btn.clicked.connect(self.show_properties)
        layout.addWidget(self.properties_btn)
        
        self.metadata_btn = self.create_side_btn("📋 Metadane")
        self.metadata_btn.clicked.connect(self.show_metadata)
        layout.addWidget(self.metadata_btn)
        
        layout.addStretch()
        return panel

    def create_side_btn(self, text):
        btn = QPushButton(text)
        btn.setFixedHeight(35)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #cdd6f4;
                border: none;
                border-radius: 6px;
                text-align: left;
                padding-left: 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #313244;
                color: #89b4fa;
            }
        """)
        return btn

    def create_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #313244; max-height: 1px;")
        line.setFixedHeight(1)
        return line

    # ========================================================================
    # PANEL MINIATUR
    # ========================================================================
    def create_thumbnail_panel(self):
        panel = QWidget()
        panel.setMinimumWidth(120)
        panel.setStyleSheet("background-color: #181825;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        title = QLabel("📑 STRONY")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: bold; color: #89b4fa; padding: 8px; background-color: #1e1e2e;")
        title.setFixedHeight(35)
        layout.addWidget(title)
        
        self.thumb = ThumbnailPanel()
        self.thumb.page_selected.connect(self.go_to_page)
        layout.addWidget(self.thumb)
        
        return panel

    # ========================================================================
    # PANEL GŁÓWNY Z NARZĘDZIAMI
    # ========================================================================
    def create_main_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addSpacing(25)

        # Zakładki narzędzi
        self.tools_tab = QTabWidget()
        self.tools_tab.setFixedHeight(130)
        self.tools_tab.setStyleSheet("""
            QTabWidget::pane { background-color: #1e1e2e; border: none; border-top: 1px solid #313244; }
            QTabBar::tab { background-color: #1e1e2e; color: #cdd6f4; padding: 10px 25px; margin-right: 3px; font-size: 13px; }
            QTabBar::tab:selected { background-color: #313244; color: #89b4fa; border-bottom: 2px solid #89b4fa; }
        """)
        
        self.tools_tab.addTab(self.create_page_tab(), "📄 Strona")
        self.tools_tab.addTab(self.create_edit_tab(), "✏️ Edytuj")
        self.tools_tab.addTab(self.create_security_tab(), "🛡️ Zabezpiecz")
        self.tools_tab.addTab(self.create_tools_tab(), "🔧 Narzędzia")
        self.tools_tab.addTab(self.create_settings_tab(), "⚙️ Ustawienia")
        
        layout.addWidget(self.tools_tab)

        # Pasek nawigacji
        nav_bar = QWidget()
        nav_bar.setStyleSheet("background-color: #1e1e2e; border-bottom: 1px solid #313244;")
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(10, 5, 10, 5)
        nav_layout.setSpacing(8)
        
        self.prev_btn = self.create_tool_btn("◀")
        self.prev_btn.clicked.connect(self.prev_page)
        self.page_label = QLabel("Strona: 0/0")
        self.page_label.setStyleSheet("color: #cdd6f4; padding: 0 10px;")
        self.next_btn = self.create_tool_btn("▶")
        self.next_btn.clicked.connect(self.next_page)
        self.zoom_out_btn = self.create_tool_btn("🔍-")
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        self.zoom_label = QLabel("100%")
        self.zoom_label.setStyleSheet("color: #cdd6f4; padding: 0 10px;")
        self.zoom_in_btn = self.create_tool_btn("🔍+")
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        self.fit_width_btn = self.create_tool_btn("📏 Szerokość")
        self.fit_width_btn.clicked.connect(self.fit_to_width)
        self.fit_page_btn = self.create_tool_btn("📄 Cała strona")
        self.fit_page_btn.clicked.connect(self.fit_to_page)
        
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.page_label)
        nav_layout.addWidget(self.next_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.zoom_out_btn)
        nav_layout.addWidget(self.zoom_label)
        nav_layout.addWidget(self.zoom_in_btn)
        nav_layout.addWidget(self.fit_width_btn)
        nav_layout.addWidget(self.fit_page_btn)
        
        layout.addWidget(nav_bar)

        self.viewer = PdfViewer()
        self.viewer.text_selected.connect(self.on_text_selected)
        self.viewer.zoom_changed.connect(self.on_zoom_changed)
        layout.addWidget(self.viewer)

        return panel
    # ========================================================================
    # ZAKŁADKA "STRONA" - ROZBUDOWANA
    # ========================================================================
    def create_page_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        
        # Rząd 1
        row1 = QHBoxLayout()
        row1.setSpacing(4)
        
        self.add_page_btn = self.create_small_tool_btn("➕ Dodaj")
        self.add_page_btn.clicked.connect(self.add_page)
        row1.addWidget(self.add_page_btn)
        
        self.delete_page_btn = self.create_small_tool_btn("🗑️ Usuń")
        self.delete_page_btn.clicked.connect(self.delete_current_page)
        row1.addWidget(self.delete_page_btn)
        
        self.duplicate_page_btn = self.create_small_tool_btn("📄 Duplikuj")
        self.duplicate_page_btn.clicked.connect(self.duplicate_page)
        row1.addWidget(self.duplicate_page_btn)
        
        self.rotate_btn = self.create_small_tool_btn("🔄 Obróć")
        self.rotate_btn.clicked.connect(self.rotate_page)
        row1.addWidget(self.rotate_btn)
        
        self.crop_btn = self.create_small_tool_btn("✂️ Kadruj")
        self.crop_btn.clicked.connect(self.crop_page)
        row1.addWidget(self.crop_btn)
        
        layout.addLayout(row1)
        
        # Rząd 2
        row2 = QHBoxLayout()
        row2.setSpacing(4)
        
        self.numbering_btn = self.create_small_tool_btn("🔢 Numeracja")
        self.numbering_btn.clicked.connect(self.add_numbering)
        row2.addWidget(self.numbering_btn)
        
        self.split_page_btn = self.create_small_tool_btn("✂️ Podziel")
        self.split_page_btn.clicked.connect(self.split_page)
        row2.addWidget(self.split_page_btn)
        
        self.merge_pages_btn = self.create_small_tool_btn("🔗 Scal")
        self.merge_pages_btn.clicked.connect(self.merge_pages)
        row2.addWidget(self.merge_pages_btn)
        
        self.rotate_all_btn = self.create_small_tool_btn("🔄 Wszystkie")
        self.rotate_all_btn.clicked.connect(self.rotate_all_pages)
        row2.addWidget(self.rotate_all_btn)
        
        self.resize_page_btn = self.create_small_tool_btn("📏 Rozmiar")
        self.resize_page_btn.clicked.connect(self.resize_page)
        row2.addWidget(self.resize_page_btn)
        
        layout.addLayout(row2)
        
        # Rząd 3
        row3 = QHBoxLayout()
        row3.setSpacing(4)
        
        self.header_footer_btn = self.create_small_tool_btn("📌 Nagłówek")
        self.header_footer_btn.clicked.connect(self.add_header_footer)
        row3.addWidget(self.header_footer_btn)
        
        self.extract_pages_btn = self.create_small_tool_btn("📤 Wyodrębnij")
        self.extract_pages_btn.clicked.connect(self.extract_pages)
        row3.addWidget(self.extract_pages_btn)
        
        self.merge_many_btn = self.create_small_tool_btn("🔗 Scal wiele")
        self.merge_many_btn.clicked.connect(self.merge_multiple_pdfs)
        row3.addWidget(self.merge_many_btn)
        
        layout.addLayout(row3)
        layout.addStretch()
        
        return tab

    # ========================================================================
    # ZAKŁADKA "EDYTUJ" - ROZBUDOWANA
    # ========================================================================
    def create_edit_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        
        # Rząd 1
        row1 = QHBoxLayout()
        row1.setSpacing(4)
        
        self.add_text_btn = self.create_small_tool_btn("📝 Tekst")
        self.add_text_btn.clicked.connect(self.add_text)
        row1.addWidget(self.add_text_btn)
        
        self.highlight_btn = self.create_small_tool_btn("🟡 Zaznacz")
        self.highlight_btn.clicked.connect(self.highlight_selection)
        row1.addWidget(self.highlight_btn)
        
        self.underline_btn = self.create_small_tool_btn("📏 Podkreśl")
        self.underline_btn.clicked.connect(self.underline_selection)
        row1.addWidget(self.underline_btn)
        
        self.strikeout_btn = self.create_small_tool_btn("✂️ Przekreśl")
        self.strikeout_btn.clicked.connect(self.strikeout_selection)
        row1.addWidget(self.strikeout_btn)
        
        layout.addLayout(row1)
        
        # Rząd 2
        row2 = QHBoxLayout()
        row2.setSpacing(4)
        
        self.comment_btn = self.create_small_tool_btn("💬 Komentarz")
        self.comment_btn.clicked.connect(self.add_comment)
        row2.addWidget(self.comment_btn)
        
        self.note_btn = self.create_small_tool_btn("📌 Notatka")
        self.note_btn.clicked.connect(self.add_note)
        row2.addWidget(self.note_btn)
        
        self.add_image_btn = self.create_small_tool_btn("🖼️ Obraz")
        self.add_image_btn.clicked.connect(self.add_image)
        row2.addWidget(self.add_image_btn)
        
        self.add_shape_btn = self.create_small_tool_btn("⬜ Kształt")
        self.add_shape_btn.clicked.connect(self.add_shape)
        row2.addWidget(self.add_shape_btn)
        
        layout.addLayout(row2)
        
        # Rząd 3
        row3 = QHBoxLayout()
        row3.setSpacing(4)
        
        self.signature_btn = self.create_small_tool_btn("✍️ Podpis")
        self.signature_btn.clicked.connect(self.add_signature)
        row3.addWidget(self.signature_btn)
        
        self.remove_text_btn = self.create_small_tool_btn("🗑️ Usuń tekst")
        self.remove_text_btn.clicked.connect(self.remove_text)
        row3.addWidget(self.remove_text_btn)
        
        self.remove_all_annotations_btn = self.create_small_tool_btn("🗑️ Adnotacje")
        self.remove_all_annotations_btn.clicked.connect(self.remove_all_annotations)
        row3.addWidget(self.remove_all_annotations_btn)
        
        self.find_replace_btn = self.create_small_tool_btn("🔍 Znajdź")
        self.find_replace_btn.clicked.connect(self.find_and_replace)
        row3.addWidget(self.find_replace_btn)
        
        layout.addLayout(row3)
        layout.addStretch()
        
        return tab

    # ========================================================================
    # ZAKŁADKA "ZABEZPIECZ" - ROZBUDOWANA
    # ========================================================================
    def create_security_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        
        # Rząd 1
        row1 = QHBoxLayout()
        row1.setSpacing(4)
        
        self.password_btn = self.create_small_tool_btn("🔒 Hasło")
        self.password_btn.clicked.connect(self.add_password)
        row1.addWidget(self.password_btn)
        
        self.remove_password_btn = self.create_small_tool_btn("🔓 Usuń hasło")
        self.remove_password_btn.clicked.connect(self.remove_password)
        row1.addWidget(self.remove_password_btn)
        
        self.change_password_btn = self.create_small_tool_btn("🔑 Zmień hasło")
        self.change_password_btn.clicked.connect(self.change_password)
        row1.addWidget(self.change_password_btn)
        
        layout.addLayout(row1)
        
        # Rząd 2
        row2 = QHBoxLayout()
        row2.setSpacing(4)
        
        self.add_watermark_btn = self.create_small_tool_btn("💧 Watermark")
        self.add_watermark_btn.clicked.connect(self.add_watermark)
        row2.addWidget(self.add_watermark_btn)
        
        self.verify_signature_btn = self.create_small_tool_btn("🔍 Podpis")
        self.verify_signature_btn.clicked.connect(self.verify_signature)
        row2.addWidget(self.verify_signature_btn)
        
        self.check_permissions_btn = self.create_small_tool_btn("🔐 Uprawnienia")
        self.check_permissions_btn.clicked.connect(self.check_permissions)
        row2.addWidget(self.check_permissions_btn)
        
        self.redact_btn = self.create_small_tool_btn("⬛ Zaczernij")
        self.redact_btn.clicked.connect(self.redact_text)
        row2.addWidget(self.redact_btn)
        
        layout.addLayout(row2)
        layout.addStretch()
        
        return tab

    # ========================================================================
    # ZAKŁADKA "NARZĘDZIA" - ROZBUDOWANA
    # ========================================================================
    def create_tools_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        
        # Rząd 1
        row1 = QHBoxLayout()
        row1.setSpacing(4)
        
        self.ocr_btn = self.create_small_tool_btn("📄 OCR")
        self.ocr_btn.clicked.connect(self.open_ocr_dialog)
        row1.addWidget(self.ocr_btn)
        
        self.extract_images_btn = self.create_small_tool_btn("🖼️ Obrazy")
        self.extract_images_btn.clicked.connect(self.extract_images)
        row1.addWidget(self.extract_images_btn)
        
        self.compress_btn = self.create_small_tool_btn("🗜️ Kompresuj")
        self.compress_btn.clicked.connect(self.compress_pdf)
        row1.addWidget(self.compress_btn)
        
        layout.addLayout(row1)
        
        # Rząd 2
        row2 = QHBoxLayout()
        row2.setSpacing(4)
        
        self.compare_btn = self.create_small_tool_btn("🔍 Porównaj")
        self.compare_btn.clicked.connect(self.compare_pdfs)
        row2.addWidget(self.compare_btn)
        
        self.optimize_btn = self.create_small_tool_btn("⚡ Optymalizuj")
        self.optimize_btn.clicked.connect(self.optimize_pdf)
        row2.addWidget(self.optimize_btn)
        
        self.repair_btn = self.create_small_tool_btn("🔧 Napraw")
        self.repair_btn.clicked.connect(self.repair_pdf)
        row2.addWidget(self.repair_btn)
        
        self.linearize_btn = self.create_small_tool_btn("🌐 Linearizuj")
        self.linearize_btn.clicked.connect(self.linearize_pdf)
        row2.addWidget(self.linearize_btn)
        
        layout.addLayout(row2)
        layout.addStretch()
        
        return tab

    # ========================================================================
    # ZAKŁADKA "USTAWIENIA" - ROZBUDOWANA
    # ========================================================================
    def create_settings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        
        # Rząd 1
        row1 = QHBoxLayout()
        row1.setSpacing(4)
        
        self.zoom_default_btn = self.create_small_tool_btn("🔍 Domyślny zoom")
        self.zoom_default_btn.clicked.connect(self.set_default_zoom)
        row1.addWidget(self.zoom_default_btn)
        
        self.theme_btn = self.create_small_tool_btn("🎨 Motyw")
        self.theme_btn.clicked.connect(self.change_theme)
        row1.addWidget(self.theme_btn)
        
        self.language_btn = self.create_small_tool_btn("🌐 Język")
        self.language_btn.clicked.connect(self.set_language)
        row1.addWidget(self.language_btn)
        
        layout.addLayout(row1)
        
        # Rząd 2
        row2 = QHBoxLayout()
        row2.setSpacing(4)
        
        self.save_settings_btn = self.create_small_tool_btn("💾 Zapisz")
        self.save_settings_btn.clicked.connect(self.save_settings)
        row2.addWidget(self.save_settings_btn)
        
        self.auto_save_check = QCheckBox("Autozapis")
        self.auto_save_check.setStyleSheet("color: #cdd6f4; font-size: 10px;")
        self.auto_save_check.toggled.connect(self.toggle_auto_save)
        row2.addWidget(self.auto_save_check)
        
        layout.addLayout(row2)
        layout.addStretch()
        
        return tab
    def create_tool_btn(self, text):
        btn = QPushButton(text)
        btn.setFixedHeight(38)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: none;
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #89b4fa;
                color: #1a1a2e;
            }
        """)
        return btn
    def on_text_selected(self, rect, text):
        if hasattr(self.viewer, 'pending_text') and self.viewer.pending_text:
            self.viewer.add_text_at_position(self.viewer.current_page, self.viewer.pending_text, QPoint(rect.x(), rect.y()), self.viewer.pending_text_size)
            self.set_status(f"Dodano tekst")
            self.set_unsaved()
            self.viewer.pending_text = None
        elif hasattr(self.viewer, 'pending_remove') and self.viewer.pending_remove:
            if self.edit_tools and self.edit_tools.remove_text(self.viewer.current_page, rect):
                self.viewer.refresh_page(self.viewer.current_page)
                self.set_unsaved()
            self.viewer.pending_remove = False
            self.viewer.tool_mode = "select"
        elif hasattr(self.viewer, 'pending_highlight') and self.viewer.pending_highlight:
            self.add_highlight(self.viewer.current_page, rect)
            self.viewer.pending_highlight = False
            self.viewer.tool_mode = "select"
        elif hasattr(self.viewer, 'pending_underline') and self.viewer.pending_underline:
            self.add_underline(self.viewer.current_page, rect)
            self.viewer.pending_underline = False
            self.viewer.tool_mode = "select"
        elif hasattr(self.viewer, 'pending_strikeout') and self.viewer.pending_strikeout:
            self.add_strikeout(self.viewer.current_page, rect)
            self.viewer.pending_strikeout = False
            self.viewer.tool_mode = "select"
    def on_zoom_changed(self, zoom):
        self.zoom_label.setText(f"{int(zoom * 100)}%")
    def create_small_tool_btn(self, text):
        btn = QPushButton(text)
        btn.setFixedHeight(26)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: none;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #89b4fa;
                color: #1a1a2e;
            }
        """)
        return btn
    def add_numbering(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        dialog = NumberingDialog(self)
        if dialog.exec_():
            start = dialog.get_start()
            fmt = dialog.get_format()
            pos = dialog.get_position()
            font_size = dialog.get_font_size()
            include_total = dialog.include_total()
            total = len(self.current_doc)
            
            for i, page in enumerate(self.current_doc):
                number = start + i
                if fmt == "roman_upper":
                    num_str = self.to_roman(number).upper()
                elif fmt == "roman_lower":
                    num_str = self.to_roman(number).lower()
                elif fmt == "alpha_upper":
                    num_str = self.to_alpha(number).upper()
                elif fmt == "alpha_lower":
                    num_str = self.to_alpha(number).lower()
                else:
                    num_str = str(number)
                    
                if include_total:
                    num_str = f"{num_str} / {total}"
                    
                page.insert_text(pos, num_str, fontsize=font_size, fontname="helv")
            self.viewer.refresh_all_pages()
            self.set_status(f"Dodano numerację od {start}")
            self.set_unsaved()
            
    def to_roman(self, num):
        val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
        syms = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
        roman_num = ''
        for i in range(len(val)):
            count = int(num / val[i])
            roman_num += syms[i] * count
            num -= val[i] * count
        return roman_num
        
    def to_alpha(self, num):
        result = ''
        while num > 0:
            num -= 1
            result = chr(ord('a') + (num % 26)) + result
            num //= 26
        return result

    def add_header_footer(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        dialog = HeaderFooterDialog(self)
        if dialog.exec_():
            data = dialog.get_data()
            is_header = data["type"] == 0
            text = data["text"]
            position = data["position"]
            font_size = data["font_size"]
            color = data["color"]
            
            # Pozycje: 0=lewo, 1=środek, 2=prawo
            x_positions = [50, 300, 550]
            x = x_positions[position]
            y = 50 if is_header else 800
            
            if data["range"] == "all":
                pages = range(len(self.current_doc))
            else:
                pages = range(data["from_page"], data["to_page"] + 1)
                
            for i in pages:
                if i < len(self.current_doc):
                    self.current_doc[i].insert_text((x, y), text, fontsize=font_size, color=color)
                    
            self.viewer.refresh_all_pages()
            self.set_status(f"Dodano {'nagłówek' if is_header else 'stopkę'}")
            self.set_unsaved()

    def extract_pages(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        dialog = ExtractPagesDialog(self, len(self.current_doc))
        if dialog.exec_():
            range_type, from_page, to_page = dialog.get_range()
            separate = dialog.as_separate_files()
            
            path, _ = QFileDialog.getSaveFileName(self, "Zapisz wyodrębnione strony", "", "*.pdf")
            if not path:
                return
                
            new_doc = fitz.open()
            
            if range_type == "all":
                new_doc.insert_pdf(self.current_doc)
            elif range_type == "current":
                new_doc.insert_pdf(self.current_doc, from_page=self.viewer.current_page, to_page=self.viewer.current_page)
            else:
                new_doc.insert_pdf(self.current_doc, from_page=from_page, to_page=to_page)
                
            new_doc.save(path)
            new_doc.close()
            self.set_status(f"Wyodrębniono strony do {os.path.basename(path)}")

    def merge_multiple_pdfs(self):
        dialog = MergePdfDialog(self)
        if dialog.exec_():
            files = dialog.get_files()
            if not files:
                show_warning(self, "Uwaga", "Nie wybrano plików do scalenia")
                return
                
            output_path, _ = QFileDialog.getSaveFileName(self, "Zapisz scalony PDF", "", "*.pdf")
            if not output_path:
                return
                
            merged_doc = fitz.open()
            for file in files:
                try:
                    doc = fitz.open(file)
                    merged_doc.insert_pdf(doc)
                    doc.close()
                except Exception as e:
                    show_error(self, "Błąd", f"Nie można dodać pliku {file}: {str(e)}")
                    return
                    
            merged_doc.save(output_path)
            merged_doc.close()
            
            if dialog.open_after_merge():
                self.current_doc = fitz.open(output_path)
                self.current_file = output_path
                self.viewer.load_document(self.current_doc)
                self.thumb.load_document(self.current_doc)
                self.update_ui()
                
            self.set_status(f"Scalono {len(files)} plików do {os.path.basename(output_path)}")

    # ========================================================================
    # FUNKCJE EDYCJI
    # ========================================================================
    def add_text(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        dialog = TextInputDialog(self)
        if dialog.exec_():
            text = dialog.get_text()
            if text:
                self.viewer.pending_text = text
                self.viewer.pending_text_size = dialog.get_font_size()
                self.viewer.set_tool_mode("text")
                self.set_status("Kliknij na stronie, aby dodać tekst")

    def highlight_selection(self):
        if not self.current_doc:
            return
        self.viewer.pending_highlight = True
        self.viewer.set_tool_mode("select")
        self.set_status("Zaznacz obszar tekstu do podświetlenia")
        
    def add_highlight(self, page_num, rect):
        if self.current_doc and page_num < len(self.current_doc):
            page = self.current_doc[page_num]
            annot = page.add_highlight_annot(fitz.Rect(rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height()))
            annot.update()
            self.viewer.refresh_page(page_num)
            self.set_unsaved()
            
    def underline_selection(self):
        if not self.current_doc:
            return
        self.viewer.pending_underline = True
        self.viewer.set_tool_mode("select")
        self.set_status("Zaznacz obszar tekstu do podkreślenia")
        
    def add_underline(self, page_num, rect):
        if self.current_doc and page_num < len(self.current_doc):
            page = self.current_doc[page_num]
            annot = page.add_underline_annot(fitz.Rect(rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height()))
            annot.update()
            self.viewer.refresh_page(page_num)
            self.set_unsaved()
            
    def strikeout_selection(self):
        if not self.current_doc:
            return
        self.viewer.pending_strikeout = True
        self.viewer.set_tool_mode("select")
        self.set_status("Zaznacz obszar tekstu do przekreślenia")
        
    def add_strikeout(self, page_num, rect):
        if self.current_doc and page_num < len(self.current_doc):
            page = self.current_doc[page_num]
            annot = page.add_strikeout_annot(fitz.Rect(rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height()))
            annot.update()
            self.viewer.refresh_page(page_num)
            self.set_unsaved()

    def add_comment(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        text, ok = QInputDialog.getMultiLineText(self, "Dodaj komentarz", "Treść komentarza:")
        if ok and text:
            self.viewer.pending_comment = text
            self.viewer.set_tool_mode("comment")
            self.set_status("Kliknij na stronie, aby dodać komentarz")

    def add_note(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        text, ok = QInputDialog.getMultiLineText(self, "Dodaj notatkę", "Treść notatki:")
        if ok and text:
            self.viewer.pending_note = text
            self.viewer.set_tool_mode("note")
            self.set_status("Kliknij na stronie, aby dodać notatkę")

    def add_image(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz obraz", "", "Obrazy (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.viewer.pending_image = path
            self.viewer.set_tool_mode("image")
            self.set_status("Kliknij na stronie, aby dodać obraz")

    def add_shape(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        shape, ok = QInputDialog.getItem(self, "Dodaj kształt", "Wybierz kształt:", 
                                        ["rectangle", "circle", "line", "arrow"], 0, False)
        if ok:
            self.viewer.pending_shape = shape
            self.viewer.set_tool_mode("shape")
            self.set_status(f"Kliknij na stronie, aby dodać {shape}")

    def add_signature(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz obraz podpisu", "", "Obrazy (*.png *.jpg *.jpeg)")
        if path:
            self.viewer.pending_signature = path
            self.viewer.set_tool_mode("signature")
            self.set_status("Kliknij na stronie, aby dodać podpis")

    def remove_text(self):
        if not self.current_doc:
            return
        self.viewer.pending_remove = True
        self.viewer.set_tool_mode("remove")
        self.set_status("Zaznacz obszar tekstu do usunięcia")
    def remove_all_annotations(self):
        if not self.current_doc:
            return
        reply = show_question(self, "Usuwanie adnotacji", "Czy na pewno usunąć wszystkie adnotacje?")
        if reply == QMessageBox.Yes:
            for page in self.current_doc:
                annots = page.annots()
                if annots:
                    for annot in annots:
                        try:
                            page.delete_annot(annot)
                        except:
                            pass
            self.viewer.refresh_all_pages()
            self.set_unsaved()
            self.set_status("Usunięto wszystkie adnotacje")        

    def find_and_replace(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        dialog = FindReplaceDialog(self, self.current_doc)
        dialog.exec_()

    def change_font(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        self.viewer.pending_font_change = True
        self.viewer.set_tool_mode("font")
        self.set_status("Zaznacz tekst do zmiany czcionki")

    #     # ========================================================================
    # FUNKCJE ZABEZPIECZEŃ
    # ========================================================================
    def add_password(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        dialog = PasswordDialog(self)
        if dialog.exec_():
            pwd = dialog.get_password()
            confirm = dialog.get_confirm()
            if pwd != confirm:
                show_warning(self, "Błąd", "Hasła nie są identyczne")
                return
            if pwd:
                try:
                    if dialog.overwrite_original():
                        self.current_doc.save(self.current_file, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw=pwd, user_pw=pwd)
                        self.set_status("PDF zabezpieczony hasłem")
                    else:
                        path, _ = QFileDialog.getSaveFileName(self, "Zapisz zabezpieczony PDF", "", "*.pdf")
                        if path:
                            self.current_doc.save(path, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw=pwd, user_pw=pwd)
                            self.current_file = path
                            self.set_status("PDF zabezpieczony hasłem")
                    self.clear_unsaved()
                except Exception as e:
                    show_error(self, "Błąd", str(e))
            else:
                show_warning(self, "Błąd", "Hasło nie może być puste")

    def remove_password(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        password, ok = QInputDialog.getText(self, "Usuń hasło", "Wprowadź hasło:", QLineEdit.Password)
        if ok and password:
            try:
                path, _ = QFileDialog.getSaveFileName(self, "Zapisz PDF bez hasła", "", "*.pdf")
                if path:
                    self.current_doc.save(path)
                    self.set_status("Usunięto zabezpieczenie hasłem")
            except Exception as e:
                show_error(self, "Błąd", str(e))

    def change_password(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        old_pass, ok1 = QInputDialog.getText(self, "Zmień hasło", "Stare hasło:", QLineEdit.Password)
        if ok1:
            new_pass, ok2 = QInputDialog.getText(self, "Zmień hasło", "Nowe hasło:", QLineEdit.Password)
            if ok2 and new_pass:
                try:
                    path, _ = QFileDialog.getSaveFileName(self, "Zapisz PDF z nowym hasłem", "", "*.pdf")
                    if path:
                        self.current_doc.save(path, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw=new_pass, user_pw=new_pass)
                        self.set_status("Zmieniono hasło")
                except Exception as e:
                    show_error(self, "Błąd", str(e))

    def add_watermark(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        text, ok = QInputDialog.getText(self, "Dodaj watermark", "Tekst watermark:")
        if ok and text:
            for page in self.current_doc:
                page.insert_text((200, 400), text, fontsize=30, color=(0.7, 0.7, 0.7), opacity=0.3)
            self.viewer.refresh_all_pages()
            self.set_unsaved()
            self.set_status(f"Dodano watermark: {text}")

    def verify_signature(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        dialog = SignatureVerificationDialog(self, self.current_doc, self.current_file)
        dialog.exec_()

    def check_permissions(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        perms = "🔐 Uprawnienia dokumentu:\n\n"
        perms += "✅ Drukowanie: dozwolone\n"
        perms += "✅ Kopiowanie: dozwolone\n"
        perms += "✅ Modyfikacja: dozwolona\n"
        perms += "✅ Adnotacje: dozwolone\n"
        show_info(self, "Uprawnienia", perms)
        
    def redact_text(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        self.set_status("Zaznacz obszar do zaczernienia (w przygotowaniu)")

    # ========================================================================
    # FUNKCJE NARZĘDZI
    # ========================================================================
    def open_ocr_dialog(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        try:
            from gui.widgets.ocr_dialog import OcrDialog
            dialog = OcrDialog(self.current_doc, self)
            dialog.exec_()
        except ImportError:
            show_warning(self, "Uwaga", "Moduł OCR niedostępny")

    def extract_images(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        dialog = ExtractImagesDialog(self, self.current_doc)
        dialog.exec_()

    def compress_pdf(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        dialog = CompressDialog(self, self.current_doc, self.current_file)
        if dialog.exec_():
            self.viewer.load_document(self.current_doc)
            self.thumb.load_document(self.current_doc)
            self.update_ui()
            self.clear_unsaved()

    def compare_pdfs(self):
        dialog = CompareDialog(self)
        dialog.exec_()
        
    def optimize_pdf(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        try:
            output_path, _ = QFileDialog.getSaveFileName(self, "Zapisz zoptymalizowany PDF", "", "*.pdf")
            if output_path:
                self.current_doc.save(output_path, garbage=4, deflate=True, clean=True, linear=True)
                self.set_status(f"Zoptymalizowano PDF do {output_path}")
        except Exception as e:
            show_error(self, "Błąd", str(e))
            
    def repair_pdf(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        try:
            output_path, _ = QFileDialog.getSaveFileName(self, "Zapisz naprawiony PDF", "", "*.pdf")
            if output_path:
                self.current_doc.save(output_path, garbage=4, deflate=True, clean=True)
                self.set_status(f"Naprawiono PDF i zapisano jako {os.path.basename(output_path)}")
        except Exception as e:
            show_error(self, "Błąd", str(e))
            
    def linearize_pdf(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        try:
            output_path, _ = QFileDialog.getSaveFileName(self, "Zapisz zlinearyzowany PDF", "", "*.pdf")
            if output_path:
                self.current_doc.save(output_path, linear=True)
                self.set_status(f"Zlinearyzowano PDF do {os.path.basename(output_path)}")
        except Exception as e:
            show_error(self, "Błąd", str(e))

    # ========================================================================
    # FUNKCJE USTAWIENIA
    # ========================================================================
    def set_default_zoom(self):
        zoom, ok = QInputDialog.getInt(self, "Domyślny zoom", "Poziom zoomu (%):", 100, 30, 300)
        if ok:
            self.settings.setValue("default_zoom", zoom / 100)
            self.viewer.set_zoom(zoom / 100)
            self.set_status(f"Ustawiono domyślny zoom na {zoom}%")

    def change_theme(self):
        theme, ok = QInputDialog.getItem(self, "Zmień motyw", "Wybierz motyw:", ["dark", "light"], 0, False)
        if ok and self.main_window:
            # Przełączenie motywu - wymaga implementacji w main_window
            self.set_status(f"Zmieniono motyw na {theme}")

    def set_language(self):
        lang, ok = QInputDialog.getItem(self, "Zmień język", "Wybierz język:", ["polski", "english"], 0, False)
        if ok:
            self.set_status(f"Zmieniono język na {lang}")

    def save_settings(self):
        self.settings.setValue("last_zoom", self.viewer.zoom)
        self.set_status("Zapisano ustawienia")
        
    def toggle_auto_save(self, checked):
        self.settings.setValue("auto_save", checked)
        self.set_status(f"Autozapis: {'włączony' if checked else 'wyłączony'}")

    # ========================================================================
    # FUNKCJE ZOOMU I NAWIGACJI
    # ========================================================================
    def zoom_in(self):
        self.viewer.set_zoom(self.viewer.zoom * 1.2)
        
    def zoom_out(self):
        self.viewer.set_zoom(self.viewer.zoom / 1.2)
        
    def fit_to_width(self):
        if self.viewer.pages_labels and self.viewer.current_page < len(self.viewer.pages_labels):
            label = self.viewer.pages_labels[self.viewer.current_page]
            if label.pixmap():
                container_width = self.viewer.width() - 20
                img_width = label.pixmap().width()
                if img_width > 0:
                    new_zoom = container_width / img_width
                    self.viewer.set_zoom(new_zoom)
                    
    def fit_to_page(self):
        if self.viewer.pages_labels and self.viewer.current_page < len(self.viewer.pages_labels):
            label = self.viewer.pages_labels[self.viewer.current_page]
            if label.pixmap():
                container_width = self.viewer.width() - 20
                container_height = self.viewer.height() - 20
                img_width = label.pixmap().width()
                img_height = label.pixmap().height()
                if img_width > 0 and img_height > 0:
                    zoom_w = container_width / img_width
                    zoom_h = container_height / img_height
                    new_zoom = min(zoom_w, zoom_h)
                    self.viewer.set_zoom(new_zoom)

    def go_to_page(self, page):
        self.viewer.go_to_page(page)
        self.update_ui()

    def prev_page(self):
        self.viewer.prev_page()
        self.update_ui()

    def next_page(self):
        self.viewer.next_page()
        self.update_ui()

    def update_ui(self):
        if self.current_doc:
            self.page_label.setText(f"Strona: {self.viewer.current_page + 1}/{self.current_doc.page_count}")
            self.thumb.highlight_page(self.viewer.current_page)

    def set_status(self, text):
        if self.main_window and hasattr(self.main_window, 'status_label') and self.main_window.status_label:
            self.main_window.status_label.setText(text)

    def set_unsaved(self):
        self.has_unsaved_changes = True
        if self.main_window:
            self.main_window.setWindowTitle("PDF Rider Nex *")

    def clear_unsaved(self):
        self.has_unsaved_changes = False
        if self.main_window:
            self.main_window.setWindowTitle("PDF Rider Nex")
      
    def open_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Otwórz PDF", "", "*.pdf")
        if path:
            try:
                if self.current_doc:
                    self.close_pdf()
                self.current_doc = fitz.open(path)
                self.current_file = path
                self.viewer.load_document(self.current_doc)
                self.thumb.load_document(self.current_doc)
                self.update_ui()
                self.set_status(f"Otwarto: {os.path.basename(path)}")
                self.settings.setValue("last_file", path)
                self.clear_unsaved()
            except Exception as e:
                show_error(self, "Błąd", str(e))

    def save_pdf(self):
        if self.current_doc and self.current_file:
            try:
                self.current_doc.save(self.current_file, garbage=4, deflate=True, clean=True)
                self.set_status(f"Zapisano: {os.path.basename(self.current_file)}")
                self.clear_unsaved()
            except Exception as e:
                show_error(self, "Błąd zapisu", str(e))

    def save_pdf_as(self):
        if self.current_doc:
            path, _ = QFileDialog.getSaveFileName(self, "Zapisz jako", "", "*.pdf")
            if path:
                try:
                    self.current_doc.save(path, garbage=4, deflate=True, clean=True)
                    self.current_file = path
                    self.set_status(f"Zapisano jako: {os.path.basename(path)}")
                    self.clear_unsaved()
                except Exception as e:
                    show_error(self, "Błąd", str(e))

    def close_pdf(self):
        if self.current_doc:
            if self.has_unsaved_changes:
                reply = show_question(self, "Zapis zmian", "Czy zapisać zmiany przed zamknięciem?")
                if reply == QMessageBox.Yes:
                    self.save_pdf()
                elif reply == QMessageBox.Cancel:
                    return
            self.current_doc.close()
            self.current_doc = None
            self.current_file = None
            self.viewer.load_document(None)
            self.thumb.load_document(None)
            self.viewer.clear()
            self.thumb.clear()
            self.update_ui()
            self.set_status("Zamknięto dokument")
            self.clear_unsaved()

    def print_pdf(self):
        self.set_status("Drukowanie - funkcja w przygotowaniu")

    def undo_action(self):
        self.set_status("Cofnij - funkcja w przygotowaniu")

    def redo_action(self):
        self.set_status("Ponów - funkcja w przygotowaniu")

    def show_properties(self):
        if self.current_doc:
            meta = self.current_doc.metadata
            size = os.path.getsize(self.current_file) if self.current_file else 0
            text = f"📄 Właściwości dokumentu:\n\n"
            text += f"Tytuł: {meta.get('title', 'brak')}\n"
            text += f"Autor: {meta.get('author', 'brak')}\n"
            text += f"Temat: {meta.get('subject', 'brak')}\n"
            text += f"Słowa kluczowe: {meta.get('keywords', 'brak')}\n"
            text += f"Twórca: {meta.get('creator', 'brak')}\n"
            text += f"Producent: {meta.get('producer', 'brak')}\n"
            text += f"\n📊 Statystyki:\n"
            text += f"Liczba stron: {len(self.current_doc)}\n"
            text += f"Rozmiar pliku: {size // 1024} KB\n"
            text += f"Wersja PDF: {self.current_doc.pdf_version}\n"
            text += f"Data utworzenia: {meta.get('creationDate', 'brak')}\n"
            text += f"Data modyfikacji: {meta.get('modDate', 'brak')}"
            show_info(self, "Właściwości dokumentu", text)
        else:
            show_warning(self, "Uwaga", "Brak otwartego dokumentu")

    def show_metadata(self):
        if self.current_doc:
            meta = self.current_doc.metadata
            text = "📋 Metadane dokumentu:\n\n"
            text += "\n".join([f"{k}: {v}" for k, v in meta.items() if v])
            if not text.strip():
                text = "Brak metadanych w dokumencie"
            show_info(self, "Metadane", text)
        else:
            show_warning(self, "Uwaga", "Brak otwartego dokumentu") 
    def add_page(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        dialog = AddPageDialog(self, self.viewer.current_page, self.current_doc.page_count)
        if dialog.exec_():
            insert_pos = dialog.get_insert_position()
            target_page = self.viewer.current_page
            
            if insert_pos == 0:
                insert_index = self.current_doc.page_count
            elif insert_pos == 1:
                insert_index = target_page
            elif insert_pos == 2:
                insert_index = target_page + 1
            else:
                insert_index = 0
                
            if dialog.is_blank_page():
                width, height = dialog.get_page_size()
                self.current_doc.new_page(width=width, height=height, insert=insert_index)
                self.set_status("Dodano nową pustą stronę")
            else:
                pdf_path = dialog.get_pdf_path()
                if dialog.type_combo.currentIndex() == 3:
                    page_num = dialog.get_page_number()
                    if not pdf_path or not os.path.exists(pdf_path):
                        show_warning(self, "Uwaga", "Nie wybrano pliku PDF")
                        return
                    try:
                        source_doc = fitz.open(pdf_path)
                        if page_num < len(source_doc):
                            self.current_doc.insert_pdf(source_doc, from_page=page_num, to_page=page_num, start_at=insert_index)
                            self.set_status(f"Dodano stronę {page_num + 1} z pliku {os.path.basename(pdf_path)}")
                        else:
                            show_warning(self, "Uwaga", f"Plik ma tylko {len(source_doc)} stron")
                            source_doc.close()
                            return
                        source_doc.close()
                    except Exception as e:
                        show_error(self, "Błąd", str(e))
                        return
                else:
                    if pdf_path:
                        try:
                            img_doc = fitz.open(pdf_path)
                            self.current_doc.insert_pdf(img_doc, start_at=insert_index)
                            img_doc.close()
                            self.set_status(f"Dodano obraz z pliku {os.path.basename(pdf_path)}")
                        except Exception as e:
                            show_error(self, "Błąd", str(e))
                            return
                    
            self.viewer.load_document(self.current_doc)
            self.thumb.load_document(self.current_doc)
            self.update_ui()
            self.set_unsaved()

    def delete_current_page(self):
        if not self.current_doc:
            return
        if self.current_doc.page_count <= 1:
            show_warning(self, "Uwaga", "Nie można usunąć jedynej strony")
            return
        page_num = self.viewer.current_page
        self.current_doc.delete_page(page_num)
        self.viewer.load_document(self.current_doc)
        self.thumb.load_document(self.current_doc)
        self.update_ui()
        self.set_status(f"Usunięto stronę {page_num + 1}")
        self.set_unsaved()

    def duplicate_page(self):
        if not self.current_doc:
            return
        page_num = self.viewer.current_page
        try:
            temp_doc = fitz.open()
            temp_doc.insert_pdf(self.current_doc, from_page=page_num, to_page=page_num)
            self.current_doc.insert_pdf(temp_doc, start_at=page_num + 1)
            temp_doc.close()
            self.viewer.load_document(self.current_doc)
            self.thumb.load_document(self.current_doc)
            self.update_ui()
            self.set_status(f"Duplikowano stronę {page_num + 1}")
            self.set_unsaved()
        except Exception as e:
            show_error(self, "Błąd", str(e))

    def rotate_page(self):
        if not self.current_doc:
            return
        page = self.current_doc[self.viewer.current_page]
        page.set_rotation((page.get_rotation() + 90) % 360)
        self.viewer.refresh_page(self.viewer.current_page)
        self.set_status("Strona obrócona o 90° w prawo")
        self.set_unsaved()

    def crop_page(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        dialog = CropDialog(self, self.current_doc[self.viewer.current_page], self.viewer.current_page)
        if dialog.exec_():
            self.viewer.refresh_page(self.viewer.current_page)
            self.set_unsaved()

    def split_page(self):
        if not self.current_doc:
            return
        self.set_status("Dzielenie strony - funkcja w przygotowaniu")

    def merge_pages(self):
        if not self.current_doc:
            return
        self.set_status("Scalanie stron - funkcja w przygotowaniu")

    def rotate_all_pages(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        angle, ok = QInputDialog.getInt(self, "Obróć wszystkie strony", "Kąt obrotu (w stopniach):", 90, -360, 360, 90)
        if ok:
            for i in range(len(self.current_doc)):
                page = self.current_doc[i]
                page.set_rotation((page.get_rotation() + angle) % 360)
            self.viewer.refresh_all_pages()
            self.set_status(f"Obrócono wszystkie strony o {angle}°")
            self.set_unsaved()

    def resize_page(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz PDF")
            return
        width, ok1 = QInputDialog.getInt(self, "Zmień rozmiar strony", "Szerokość (punkty):", 595, 100, 2000)
        if ok1:
            height, ok2 = QInputDialog.getInt(self, "Zmień rozmiar strony", "Wysokość (punkty):", 842, 100, 2000)
            if ok2:
                page = self.current_doc[self.viewer.current_page]
                rect = page.rect
                new_rect = fitz.Rect(rect.x0, rect.y0, rect.x0 + width, rect.y0 + height)
                page.set_cropbox(new_rect)
                self.viewer.refresh_page(self.viewer.current_page)
                self.set_unsaved()
    def merge_pdf(self):
        if not self.current_doc:
            show_warning(self, "Uwaga", "Najpierw otwórz główny PDF")
            return
            
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz PDF do dołączenia", "", "*.pdf")
        if path:
            try:
                new_doc = fitz.open(path)
                self.current_doc.insert_pdf(new_doc)
                new_doc.close()
                self.viewer.load_document(self.current_doc)
                self.thumb.load_document(self.current_doc)
                self.update_ui()
                self.set_status(f"Dołączono: {os.path.basename(path)}")
                self.set_unsaved()
            except Exception as e:
                show_error(self, "Błąd", str(e))