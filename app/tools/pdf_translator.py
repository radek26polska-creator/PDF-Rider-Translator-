"""
Prosty translator PDF – tłumaczy tekst strona po stronie, zachowując layout.
Używa istniejących silników z translator.py.
"""

import fitz
from typing import Optional, Callable, List, Tuple
from pathlib import Path
import tempfile
import os

from app.tools.pdf2zh.translator import ConfigManager, BaseTranslator


class SimplePDFTranslator:
    """Tłumaczy tekst w PDF, zachowując wszystkie elementy (tabele, obrazy, pozycję)"""

    def __init__(
        self,
        pdf_path: str,
        lang_in: str = "pl",
        lang_out: str = "uk",
        translator: str = "openai",
        model: Optional[str] = None,
        status_callback: Optional[Callable[[str], None]] = None
    ):
        self.pdf_path = pdf_path
        self.lang_in = lang_in
        self.lang_out = lang_out
        self.translator_name = translator
        self.model = model
        self.status = status_callback or (lambda x: None)

        # Mapowanie języków
        self.lang_map = {
            "polski": "pl", "angielski": "en", "ukraiński": "uk",
            "hiszpański": "es", "niemiecki": "de", "francuski": "fr",
            "włoski": "it", "rosyjski": "ru", "chiński": "zh",
            "pl": "pl", "en": "en", "uk": "uk", "es": "es",
            "de": "de", "fr": "fr", "it": "it", "ru": "ru", "zh": "zh"
        }

        src = self.lang_map.get(lang_in.lower(), "pl")
        dst = self.lang_map.get(lang_out.lower(), "en")

        # Pobierz klasę tłumacza
        translator_class = ConfigManager.get_translator_by_name(translator)
        if not translator_class:
            raise ValueError(f"Nieznany silnik tłumaczenia: {translator}")

        # Stwórz instancję
        self.translator: BaseTranslator = translator_class(
            lang_in=src,
            lang_out=dst,
            model=model or "",
            ignore_cache=False
        )

        # Otwórz PDF
        self.doc = fitz.open(pdf_path)
        self.total_pages = len(self.doc)

    def translate_page(self, page_num: int, progress_callback: Optional[Callable[[int, str], None]] = None) -> fitz.Page:
        """Tłumaczy pojedyńczą stronę"""
        if page_num >= self.total_pages:
            return None

        page = self.doc[page_num]
        text_dict = page.get_text("dict")
        blocks = text_dict.get("blocks", [])

        total_blocks = sum(1 for b in blocks if b["type"] == 0 and b.get("lines"))
        processed = 0

        for block in blocks:
            if block["type"] != 0:  # tylko tekst
                continue

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    orig_text = span.get("text", "").strip()
                    if not orig_text:
                        continue

                    try:
                        # Tłumacz
                        translated = self.translator.translate(orig_text)

                        # Pozycja i styl
                        bbox = span["bbox"]  # (x0, y0, x1, y1)
                        x0, y0, x1, y1 = bbox
                        font = span.get("font", "helv")
                        size = span.get("size", 12)
                        color = span.get("color", (0, 0, 0))

                        # Usuń stary tekst (biały prostokąt)
                        page.draw_rect(fitz.Rect(x0, y0, x1, y1), color=(1, 1, 1), fill=(1, 1, 1))

                        # Wstaw przetłumaczony tekst
                        page.insert_text(
                            (x0, y0),
                            translated,
                            fontname=font,
                            fontsize=size,
                            color=color
                        )
                    except Exception as e:
                        self.status(f"Błąd tłumaczenia fragmentu: {e}")

                    processed += 1
                    if progress_callback and total_blocks > 0:
                        pct = int(90 * processed / total_blocks)
                        progress_callback(pct, f"Strona {page_num + 1}/{self.total_pages}")

        return page

    def translate_all(self, progress_callback: Optional[Callable[[int, str], None]] = None) -> fitz.Document:
        """Tłumaczy cały dokument"""
        new_doc = fitz.open()

        for page_num in range(self.total_pages):
            if progress_callback:
                progress_callback(int(10 + 80 * page_num / self.total_pages), f"Strona {page_num + 1}/{self.total_pages}")

            # Tłumacz stronę
            translated_page = self.translate_page(page_num, progress_callback)
            if translated_page:
                new_doc.insert_pdf(self.doc, from_page=page_num, to_page=page_num)

        return new_doc

    def save(self, output_path: str) -> bool:
        """Zapisz przetłumaczony PDF"""
        try:
            new_doc = self.translate_all()
            new_doc.save(output_path, deflate=True, garbage=3)
            new_doc.close()
            return True
        except Exception as e:
            self.status(f"Błąd zapisu: {e}")
            return False

    def close(self):
        if self.doc:
            self.doc.close()
