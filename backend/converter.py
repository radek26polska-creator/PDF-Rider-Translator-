"""
PDF to DOCX Converter - Idealne odwzorowanie layoutu
Zachowuje: tekst (pogrubienie, kursywa, rozmiary), tabele, pozycjonowanie, obrazy
"""

import fitz  # PyMuPDF
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
import pdfplumber
import io
from typing import List, Optional


class PDFtoDOCXConverter:
    def __init__(self, pdf_path: str, docx_path: str):
        self.pdf_path = pdf_path
        self.docx_path = docx_path
        self.doc = Document()
        self.pdf_doc = None
        self.page_width = 0
        self.page_height = 0

        # Ustaw marginesy (1 cal)
        sections = self.doc.sections
        for section in sections:
            section.left_margin = Inches(1)
            section.right_margin = Inches(1)
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)

    def open_pdf(self):
        self.pdf_doc = fitz.open(self.pdf_path)
        first_page = self.pdf_doc[0]
        self.page_width = first_page.rect.width
        self.page_height = first_page.rect.height

    def close(self):
        if self.pdf_doc:
            self.pdf_doc.close()

    def convert(self) -> bool:
        self.open_pdf()

        for page_num in range(len(self.pdf_doc)):
            page = self.pdf_doc[page_num]
            self._convert_page(page)

        self.doc.save(self.docx_path)
        self.close()
        return True

    def _convert_page(self, page):
        text_dict = page.get_text("dict")
        image_list = page.get_images(full=True)
        tables = self._extract_tables_with_pdfplumber(page.number)

        elements = []

        # Tekst
        for block in text_dict.get("blocks", []):
            if block["type"] == 0:
                elements.append({"type": "text", "y": block["bbox"][1], "data": block})

        # Tabele
        for table in tables:
            elements.append({"type": "table", "y": table["bbox"][1], "data": table})

        # Obrazy
        for img_info in image_list:
            xref = img_info[0]
            rect = self._get_image_rect(page, xref)
            if rect:
                elements.append({"type": "image", "y": rect[1], "data": {"xref": xref}})

        elements.sort(key=lambda e: e["y"])

        for element in elements:
            if element["type"] == "text":
                self._add_text_block(element["data"])
            elif element["type"] == "table":
                self._add_table(element["data"])
            elif element["type"] == "image":
                self._add_image_from_page(page, element["data"]["xref"])

        if page.number < len(self.pdf_doc) - 1:
            self.doc.add_page_break()

    def _add_text_block(self, block):
        for line in block.get("lines", []):
            paragraph = self.doc.add_paragraph()

            for span in line.get("spans", []):
                text = span["text"].strip()
                if not text:
                    continue

                run = paragraph.add_run(text)

                # Czcionka
                font = span.get("font", "").lower()
                run.bold = "bold" in font
                run.italic = "italic" in font

                # Rozmiar
                size = span.get("size", 12)
                run.font.size = Pt(size)

                # Kolor
                color = span.get("color", (0, 0, 0))
                if color and len(color) >= 3:
                    r, g, b = [int(c * 255) for c in color[:3]]
                    run.font.color.rgb = (r, g, b)  # RGBColor(r,g,b)

            paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE

    def _extract_tables_with_pdfplumber(self, page_num: int) -> List[dict]:
        tables = []
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                page = pdf.pages[page_num]
                table_objs = page.find_tables()
                for table_obj in table_objs:
                    table_data = table_obj.extract()
                    if table_data:
                        tables.append({
                            "data": table_data,
                            "bbox": table_obj.bbox
                        })
        except Exception as e:
            print(f"Błąd pdfplumber strona {page_num}: {e}")
        return tables

    def _add_table(self, table_data: List[List[str]]):
        if not table_data:
            return

        rows = len(table_data)
        cols = max(len(r) for r in table_data)

        table = self.doc.add_table(rows=rows, cols=cols)
        table.style = 'Table Grid'

        for r_idx, row in enumerate(table_data):
            for c_idx, cell_text in enumerate(row):
                cell = table.cell(r_idx, c_idx)
                cell.text = str(cell_text) if cell_text else ""
                if r_idx == 0:  # nagłówek
                    for p in cell.paragraphs:
                        for run in p.runs:
                            run.bold = True

    def _add_image_from_page(self, page, xref: int):
        try:
            base = self.pdf_doc.extract_image(xref)
            image_stream = io.BytesIO(base["image"])
            self.doc.add_picture(image_stream, width=Inches(2.0))
        except Exception as e:
            print(f"Błąd obrazu: {e}")

    def _get_image_rect(self, page, xref: int) -> Optional[tuple]:
        try:
            rects = page.get_image_rects(xref)
            return rects[0] if rects else None
        except Exception:
            return None


def convert_pdf_to_docx(pdf_path: str, docx_path: str) -> bool:
    try:
        c = PDFtoDOCXConverter(pdf_path, docx_path)
        c.convert()
        return True
    except Exception as e:
        print(f"Błąd: {e}")
        return False
