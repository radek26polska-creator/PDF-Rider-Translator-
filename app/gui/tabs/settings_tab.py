from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

class SettingsTab(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        self.label = QLabel("⚙️ Ustawienia")
        self.label.setStyleSheet("font-size: 24px; color: #89b4fa;")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.info = QLabel("Konfiguracja aplikacji (wkrótce)")
        self.info.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info)

        layout.addStretch()
        self.setLayout(layout)