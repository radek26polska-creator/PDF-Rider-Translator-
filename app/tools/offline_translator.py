"""
Offline PDF Translator – moduł do tłumaczenia bez internetu
Używa Argos Translate (lokalne pakiety językowe)

Instalacja:
  python offline_translator.py install pl uk  # pobiera pakiety polski→ukraiński
  python offline_translator.py translate input.pdf output.pdf pl uk

Lub w Python API:
  translator = OfflineTranslator("pl", "uk")
  translator.translate_file("input.pdf", "output.pdf")
"""

import sys
import os
import subprocess
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class OfflineTranslator:
    """Tłumacz offline – Argos Translate, bez API key"""

    def __init__(self, lang_in: str = "pl", lang_out: str = "uk", model: str = "argos"):
        self.lang_in = lang_in
        self.lang_out = lang_out
        self.model = model
        self._ensure_deps()

    def _ensure_deps(self):
        """Sprawdź czy argostranslate jest zainstalowany"""
        try:
            import argostranslate.package
            import argostranslate.translate
            self.argos_available = True
        except ImportError:
            self.argos_available = False
            raise ImportError(
                "Argos Translate nie jest zainstalowany.\n"
                "Zainstaluj: pip install argostranslate\n"
                "Możesz też uruchomić: python offline_translator.py install pl uk"
            )

    def install_languages(self, lang_in: str = None, lang_out: str = None):
        """Pobierz i zainstaluj pakiety językowe"""
        lang_in = lang_in or self.lang_in
        lang_out = lang_out or self.lang_out

        import argostranslate.package

        print(f"🔍 Szukam pakietów językowych: {lang_in} → {lang_out}...")
        argostranslate.package.update_package_index()
        available_packages = argostranslate.package.get_available_packages()

        # Znajdź pakiet
        package = next(
            (p for p in available_packages if p.from_code == lang_in and p.to_code == lang_out),
            None
        )

        if not package:
            raise ValueError(f"Brak pakietu językowe {lang_in} → {lang_out}.\n"
                             f"Dostępne pary: {[(p.from_code, p.to_code) for p in available_packages[:10]]}")

        print(f"⬇️ Pobieram pakiet: {package}...")
        download_path = package.download()
        print(f"📦 Instaluję...")
        argostranslate.package.install_from_path(download_path)
        print(f"✅ Pakiet {lang_in}→{lang_out} zainstalowany!")

    def translate_text(self, text: str) -> str:
        """Przetłumacz pojedynczy tekst"""
        import argostranslate.translate

        installed_languages = argostranslate.translate.get_installed_languages()
        from_lang = next((l for l in installed_languages if l.code == self.lang_in), None)
        to_lang = next((l for l in installed_languages if l.code == self.lang_out), None)

        if not from_lang or not to_lang:
            raise RuntimeError(f"Języki nie zainstalowane. Uruchom: python offline_translator.py install {self.lang_in} {self.lang_out}")

        translation = from_lang.get_translation(to_lang)
        return translation.translate(text)

    def translate_file(self, input_pdf: str, output_pdf: str, progress_callback=None) -> bool:
        """
        Tłumaczy cały plik PDF, zachowując layout.
        Używa PyMuPDF do edycji istniejącego PDF (nie konwertuje!).
        """
        try:
            import fitz  # PyMuPDF

            # Otwórz PDF
            doc = fitz.open(input_pdf)
            total_pages = len(doc)

            for page_num in range(total_pages):
                if progress_callback:
                    progress_callback(int(90 * page_num / total_pages), f"Strona {page_num+1}/{total_pages}")

                page = doc[page_num]
                text_dict = page.get_text("dict")
                blocks = text_dict.get("blocks", [])

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
                                translated = self.translate_text(orig_text)

                                # Pozycja
                                x0, y0, x1, y1 = span["bbox"]
                                font = span.get("font", "helv")
                                size = span.get("size", 12)
                                color = span.get("color", (0, 0, 0))

                                # Usuń stary tekst
                                page.draw_rect(fitz.Rect(x0, y0, x1, y1), color=(1, 1, 1), fill=(1, 1, 1))

                                # Wstaw nowy
                                page.insert_text((x0, y0), translated, fontname=font, fontsize=size, color=color)

                            except Exception as e:
                                logger.warning(f"Błąd tłumaczenia fragmentu: {e}")

                if progress_callback:
                    progress_callback(int(90 + 10 * page_num / total_pages), "Zapisywanie...")

            # Zapisz
            doc.save(output_pdf, deflate=True, garbage=3)
            doc.close()
            return True

        except Exception as e:
            logger.error(f"Błąd tłumaczenia PDF: {e}")
            return False


def main():
    """CLI – uruchom: python offline_translator.py [install|translate] ..."""
    import argparse

    parser = argparse.ArgumentParser(description="Offline PDF Translator (Argos)")
    subparsers = parser.add_subparsers(dest="command", help="Dostępne komendy")

    # install
    parser_install = subparsers.add_parser("install", help="Zainstaluj pakiety językowe")
    parser_install.add_argument("lang_in", help="Język źródłowy (np. pl)")
    parser_install.add_argument("lang_out", help="Język docelowy (np. uk)")

    # translate
    parser_trans = subparsers.add_parser("translate", help="Przetłumacz PDF")
    parser_trans.add_argument("input", help="Plik PDF wejściowy")
    parser_trans.add_argument("output", help="Plik PDF wyjściowy")
    parser_trans.add_argument("lang_in", help="Język źródłowy")
    parser_trans.add_argument("lang_out", help="Język docelowy")

    args = parser.parse_args()

    if args.command == "install":
        translator = OfflineTranslator(args.lang_in, args.lang_out)
        translator.install_languages()
        print("✅ Gotowe! Możesz tłumaczyć offline.")

    elif args.command == "translate":
        translator = OfflineTranslator(args.lang_in, args.lang_out)
        print(f"🔤 Tłumaczę {args.input} → {args.output} ...")
        success = translator.translate_file(args.input, args.output)
        if success:
            print("✅ Tłumaczenie zakończone!")
        else:
            print("❌ Błąd tłumaczenia")
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
