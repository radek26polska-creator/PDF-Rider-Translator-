"""
Wspólny silnik PDF - Singleton
Zapewnia, że ten sam plik PDF jest otwarty tylko raz w całej aplikacji
"""

import fitz


class PDFEngineManager:
    """Singleton - zarządza jednym otwartym PDF dla całej aplikacji"""
    
    _instance = None
    _current_doc = None
    _current_file = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def open_pdf(self, path):
        """
        Otwiera PDF tylko jeśli nie jest już otwarty.
        Zwraca dokument PDF.
        """
        if path == self._current_file and self._current_doc:
            return self._current_doc
        
        # Zamknij poprzedni dokument jeśli był inny
        if self._current_doc:
            self._current_doc.close()
        
        self._current_doc = fitz.open(path)
        self._current_file = path
        return self._current_doc
    
    def get_document(self):
        """Zwraca aktualnie otwarty dokument"""
        return self._current_doc
    
    def get_file_path(self):
        """Zwraca ścieżkę aktualnie otwartego pliku"""
        return self._current_file
    
    def close_pdf(self):
        """Zamyka aktualny dokument"""
        if self._current_doc:
            self._current_doc.close()
            self._current_doc = None
            self._current_file = None
    
    def has_document(self):
        """Sprawdza czy jakiś dokument jest otwarty"""
        return self._current_doc is not None