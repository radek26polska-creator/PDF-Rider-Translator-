"""
Narzędzia do edycji zawartości PDF - rozszerzona wersja
Zawiera pełny zestaw narzędzi do edycji PDF (text, images, shapes, annotations, forms)
"""

import fitz
from PyQt5.QtWidgets import QMessageBox, QColorDialog
from PyQt5.QtGui import QPixmap, QColor
from typing import Tuple, Optional, List
import io
import os


class PdfEditTools:
    def __init__(self, viewer, doc, status_callback=None):
        self.viewer = viewer
        self.doc = doc
        self.status_callback = status_callback or (lambda x: None)

    # ==================== TEXT EDITING ====================

    def add_text(self, page_index: int, text: str, pos, fontname="helv", fontsize=12, color=(0, 0, 0)) -> bool:
        """Dodaj tekst w wybranej pozycji"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            x, y = pos.x() / self.viewer.zoom, pos.y() / self.viewer.zoom
            page.insert_text((x, y), text, fontname=fontname, fontsize=fontsize, color=color)
            self.status_callback(f"Dodano tekst na stronie {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd dodawania tekstu: {str(e)}")
            return False

    def edit_text(self, page_index: int, rect, new_text: str, fontname="helv", fontsize=12, color=(0, 0, 0)) -> bool:
        """Edytuj tekst w obszarze (usuń stary, dodaj nowy)"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            # Pobierz istniejący tekst
            old_text = page.get_textbox(rect)
            if old_text:
                # Usuń stary tekst (biały prostokąt)
                page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
            # Wstaw nowy tekst
            x, y = rect.x0, rect.y0
            page.insert_text((x, y), new_text, fontname=fontname, fontsize=fontsize, color=color)
            self.status_callback(f"Edytowano tekst na stronie {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd edycji tekstu: {str(e)}")
            return False

    def remove_text(self, page_index, rect) -> bool:
        """Usuń tekst z obszaru (kolor tła)"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
            self.status_callback(f"Usunięto tekst ze strony {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd usuwania tekstu: {str(e)}")
            return False

    def highlight_text(self, page_index, rect, color=(1, 1, 0, 0.3)) -> bool:
        """Podświetl tekst (nakładka)"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            # highlight_annot używa koloru w formacie RGBA
            annot = page.add_highlight_annot(rect)
            annot.set_colors(stroke=color)
            annot.update()
            self.status_callback(f"Podświetlono tekst na stronie {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd podświetlania: {str(e)}")
            return False

    def strikeout_text(self, page_index, rect) -> bool:
        """Przekreśl tekst"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            annot = page.add_strikeout_annot(rect)
            annot.update()
            self.status_callback(f"Przekreślono tekst na stronie {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd przekreślania: {str(e)}")
            return False

    def underline_text(self, page_index, rect, color=(0, 0, 1)) -> bool:
        """Podkreśl tekst"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            annot = page.add_underline_annot(rect)
            annot.set_colors(stroke=color)
            annot.update()
            self.status_callback(f"Podkreślono tekst na stronie {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd podkreślania: {str(e)}")
            return False

    # ==================== SHAPES & DRAWING ====================

    def add_shape(self, page_index, shape_type: str, pos, size=(100, 100), 
                  fill_color=None, stroke_color=(0, 0, 0), width=2) -> bool:
        """
        Dodaj kształt (prostokąt, okrąg, linia, strzałka)
        shape_type: 'rectangle', 'circle', 'line', 'arrow', 'polyline'
        """
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            x, y = pos.x() / self.viewer.zoom, pos.y() / self.viewer.zoom
            x2 = x + size[0]
            y2 = y + size[1]

            if shape_type == "rectangle":
                if fill_color:
                    page.draw_rect(fitz.Rect(x, y, x2, y2), color=stroke_color, fill=fill_color, width=width)
                else:
                    page.draw_rect(fitz.Rect(x, y, x2, y2), color=stroke_color, width=width)

            elif shape_type == "circle":
                center = (x + size[0]/2, y + size[1]/2)
                radius = min(size[0], size[1]) / 2
                page.draw_circle(center, radius, color=stroke_color, width=width)

            elif shape_type == "line":
                page.draw_line((x, y), (x2, y2), color=stroke_color, width=width)

            elif shape_type == "arrow":
                self._draw_arrow(page, (x, y), (x2, y2), color=stroke_color, width=width)

            self.status_callback(f"Dodano kształt '{shape_type}' na stronie {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd dodawania kształtu: {str(e)}")
            return False

    def _draw_arrow(self, page, start, end, color=(0, 0, 0), width=2):
        """Rysuj strzałkę"""
        import math
        x1, y1 = start
        x2, y2 = end

        # Linia główna
        page.draw_line(start, end, color=color, width=width)

        # Strzałka (trójkąt)
        angle = math.atan2(y2 - y1, x2 - x1)
        arrow_length = 15
        arrow_angle = math.pi / 6

        p1 = (x2 - arrow_length * math.cos(angle - arrow_angle),
              y2 - arrow_length * math.sin(angle - arrow_angle))
        p2 = (x2 - arrow_length * math.cos(angle + arrow_angle),
              y2 - arrow_length * math.sin(angle + arrow_angle))

        page.draw_polyline([end, p1, p2], color=color, width=width, closePath=True)

    # ==================== IMAGES ====================

    def add_image(self, page_index: int, image_path: str, pos, size=None) -> bool:
        """Dodaj obraz na stronie"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            x, y = pos.x() / self.viewer.zoom, pos.y() / self.viewer.zoom

            if size:
                rect = fitz.Rect(x, y, x + size[0], y + size[1])
            else:
                rect = fitz.Rect(x, y, x + 200, y + 150)  # domyślny rozmiar

            page.insert_image(rect, filename=image_path)
            self.status_callback(f"Dodano obraz na stronie {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd dodawania obrazu: {str(e)}")
            return False

    def add_image_from_clipboard(self, page_index: int, pos, size=None) -> bool:
        """Dodaj obraz ze schowka"""
        try:
            from PyQt5.QtGui import QImage, QPixmap
            clipboard = QApplication.clipboard()
            qimage = clipboard.image()
            if qimage.isNull():
                self.status_callback("Schowek nie zawiera obrazu")
                return False

            # Konwertuj QImage do PNG bytes
            buffer = io.BytesIO()
            qimage.save(buffer, "PNG")
            buffer.seek(0)

            page = self.doc[page_index]
            x, y = pos.x() / self.viewer.zoom, pos.y() / self.viewer.zoom

            if size:
                rect = fitz.Rect(x, y, x + size[0], y + size[1])
            else:
                rect = fitz.Rect(x, y, x + 200, y + 150)

            page.insert_image(rect, stream=buffer.read())
            self.status_callback(f"Dodano obraz ze schowka na stronie {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd dodawania obrazu ze schowka: {str(e)}")
            return False

    # ==================== ANNOTATIONS ====================

    def add_text_annotation(self, page_index: int, pos, text: str, title="Notatka", color=(1, 1, 0)) -> bool:
        """Dodaj adnotację tekstową (sticky note)"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            x, y = pos.x() / self.viewer.zoom, pos.y() / self.viewer.zoom
            annot = page.add_text_annot(fitz.Point(x, y), text)
            annot.set_title(title)
            annot.set_colors(fill=color)
            annot.update()
            self.status_callback(f"Dodano adnotację tekstową na stronie {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd dodawania adnotacji: {str(e)}")
            return False

    def add_freetext_annotation(self, page_index: int, rect, text: str, 
                                 fontname="helv", fontsize=12, text_color=(0, 0, 0), 
                                 fill_color=(1, 1, 0)) -> bool:
        """Dodaj wolną adnotację tekstową (edytowalna bezpośrednio w PDF)"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            # Konwertuj współrzędne z viewer zoom
            x0, y0 = rect.x0 / self.viewer.zoom, rect.y0 / self.viewer.zoom
            x1, y1 = rect.x1 / self.viewer.zoom, rect.y1 / self.viewer.zoom
            rect = fitz.Rect(x0, y0, x1, y1)

            annot = page.add_freetext_annot(rect, text)
            annot.set_fontname(fontname)
            annot.set_fontsize(fontsize)
            annot.set_colors(fill=fill_color, stroke=text_color)
            annot.update()
            self.status_callback(f"Dodano wolną adnotację tekstową na stronie {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd dodawania wolnej adnotacji: {str(e)}")
            return False

    # ==================== PAGE MANAGEMENT ====================

    def add_blank_page(self, page_index: int, width=595, height=842) -> bool:
        """Dodaj pustą stronę po wybranej stronie"""
        if not self.doc:
            return False

        try:
            self.doc.insert_page(page_index + 1, width=width, height=height)
            self.status_callback(f"Dodano pustą stronę po stronie {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd dodawania strony: {str(e)}")
            return False

    def delete_page(self, page_index: int) -> bool:
        """Usuń stronę"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            self.doc.delete_page(page_index)
            self.status_callback(f"Usunięto stronę {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd usuwania strony: {str(e)}")
            return False

    def rotate_page(self, page_index: int, angle: int) -> bool:
        """Obróć stronę o podany kąt (90, 180, 270)"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            current = page.get_rotation()
            page.set_rotation((current + angle) % 360)
            self.status_callback(f"Obrocono stronę {page_index + 1} o {angle}°")
            return True
        except Exception as e:
            self.status_callback(f"Błąd obracania strony: {str(e)}")
            return False

    def extract_page(self, page_index: int) -> Optional[fitz.Document]:
        """Wyodrębnij stronę do nowego dokumentu"""
        if not self.doc or page_index >= len(self.doc):
            return None

        try:
            new_doc = fitz.open()
            new_doc.insert_pdf(self.doc, from_page=page_index, to_page=page_index)
            self.status_callback(f"Wyodrębniono stronę {page_index + 1}")
            return new_doc
        except Exception as e:
            self.status_callback(f"Błąd wyodrębniania strony: {str(e)}")
            return None

    # ==================== FORMS & FIELDS ====================

    def add_text_field(self, page_index: int, rect, field_name="field", value="", 
                       fontsize=12, text_color=(0, 0, 0), fill_color=(1, 1, 1)) -> bool:
        """Dodaj edytowalne pole tekstowe"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            x0, y0 = rect.x0 / self.viewer.zoom, rect.y0 / self.viewer.zoom
            x1, y1 = rect.x1 / self.viewer.zoom, rect.y1 / self.viewer.zoom
            rect = fitz.Rect(x0, y0, x1, y1)

            # Dodaj widget (pole formularza)
            widget = fitz.Widget()
            widget.rect = rect
            widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
            widget.field_name = field_name
            widget.text_value = value
            widget.fontsize = fontsize
            widget.text_color = text_color
            widget.fill_color = fill_color
            page.add_widget(widget)
            self.status_callback(f"Dodano pole tekstowe na stronie {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd dodawania pola tekstowego: {str(e)}")
            return False

    def add_checkbox(self, page_index: int, pos, field_name="checkbox", checked=False) -> bool:
        """Dodaj pole checkbox"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            x, y = pos.x() / self.viewer.zoom, pos.y() / self.viewer.zoom
            size = 15
            rect = fitz.Rect(x, y, x + size, y + size)

            widget = fitz.Widget()
            widget.rect = rect
            widget.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
            widget.field_name = field_name
            widget.checkbox_status = fitz.PDF_CHECKBOX_ON if checked else fitz.PDF_CHECKBOX_OFF
            page.add_widget(widget)
            self.status_callback(f"Dodano checkbox na stronie {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd dodawania checkboxa: {str(e)}")
            return False

    def add_radio_button(self, page_index: int, pos, field_name="radio", group_name="group1") -> bool:
        """Dodaj przycisk radio"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            x, y = pos.x() / self.viewer.zoom, pos.y() / self.viewer.zoom
            size = 15
            rect = fitz.Rect(x, y, x + size, y + size)

            widget = fitz.Widget()
            widget.rect = rect
            widget.field_type = fitz.PDF_WIDGET_TYPE_RADIOBUTTON
            widget.field_name = field_name
            widget.button_type = f"/{group_name}"
            page.add_widget(widget)
            self.status_callback(f"Dodano przycisk radio na stronie {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd dodawania przycisku radio: {str(e)}")
            return False

    # ==================== COMMENTS / MARKUP ====================

    def add_square_annotation(self, page_index: int, rect, color=(1, 1, 0)) -> bool:
        """Dodaj adnotację kwadratową"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            x0, y0 = rect.x0 / self.viewer.zoom, rect.y0 / self.viewer.zoom
            x1, y1 = rect.x1 / self.viewer.zoom, rect.y1 / self.viewer.zoom
            annot = page.add_square_annot(fitz.Rect(x0, y0, x1, y1))
            annot.set_colors(fill=color)
            annot.update()
            self.status_callback(f"Dodano adnotację kwadratową na stronie {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd dodawania adnotacji kwadratowej: {str(e)}")
            return False

    def add_circle_annotation(self, page_index: int, rect, color=(1, 1, 0)) -> bool:
        """Dodaj adnotację okręgową"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            x0, y0 = rect.x0 / self.viewer.zoom, rect.y0 / self.viewer.zoom
            x1, y1 = rect.x1 / self.viewer.zoom, rect.y1 / self.viewer.zoom
            annot = page.add_circle_annot(fitz.Rect(x0, y0, x1, y1))
            annot.set_colors(fill=color)
            annot.update()
            self.status_callback(f"Dodano adnotację okręgową na stronie {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd dodawania adnotacji okręgowej: {str(e)}")
            return False

    def add_line_annotation(self, page_index: int, start, end, color=(1, 0, 0), width=2) -> bool:
        """Dodaj adnotację liniową (piorunujący linie)"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            x1, y1 = start.x() / self.viewer.zoom, start.y() / self.viewer.zoom
            x2, y2 = end.x() / self.viewer.zoom, end.y() / self.viewer.zoom
            annot = page.add_line_annot(fitz.Point(x1, y1), fitz.Point(x2, y2))
            annot.set_colors(stroke=color)
            annot.set_border(width=width)
            annot.update()
            self.status_callback(f"Dodano adnotację liniową na stronie {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd dodawania adnotacji liniowej: {str(e)}")
            return False

    # ==================== UTILITY ====================

    def delete_annotations(self, page_index: int, annot_types: List[int] = None) -> bool:
        """Usuń wszystkie adnotacje z strony (lub określonych typów)"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            annotations = page.annots()
            count = 0
            for annot in annotations:
                if annot_types is None or annot.type[0] in annot_types:
                    page.delete_annot(annot)
                    count += 1
            self.status_callback(f"Usunięto {count} adnotacji ze strony {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd usuwania adnotacji: {str(e)}")
            return False

    def clear_page_content(self, page_index: int) -> bool:
        """Wyczyść całą zawartość strony (zamień na białą)"""
        if not self.doc or page_index >= len(self.doc):
            return False

        try:
            page = self.doc[page_index]
            rect = page.rect
            # Wypełnij całą stronę białą
            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
            self.status_callback(f"Wyczyszczono stronę {page_index + 1}")
            return True
        except Exception as e:
            self.status_callback(f"Błąd czyszczenia strony: {str(e)}")
            return False

    def get_page_text(self, page_index: int) -> str:
        """Pobierz cały tekst ze strony"""
        if not self.doc or page_index >= len(self.doc):
            return ""

        try:
            page = self.doc[page_index]
            return page.get_text()
        except Exception as e:
            self.status_callback(f"Błąd pobierania tekstu: {str(e)}")
            return ""

    def search_text(self, page_index: int, text: str) -> List[fitz.Rect]:
        """Znajdź wszystkie wystąpienia tekstu na stronie, zwróć prostokąty"""
        if not self.doc or page_index >= len(self.doc):
            return []

        try:
            page = self.doc[page_index]
            instances = page.search_for(text)
            return instances
        except Exception as e:
            self.status_callback(f"Błąd wyszukiwania: {str(e)}")
            return []