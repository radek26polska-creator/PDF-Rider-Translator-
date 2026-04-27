import sys
import os

# Dodaj ścieżkę do folderu app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())