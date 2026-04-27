from fastapi import APIRouter, HTTPException, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
import shutil
import uuid
import subprocess

# Użyjemy bezpośrednio modułu pdf2zh przez subprocess (bo to osobna aplikacja PyQt5)
# Lub – zintegrujemy jako bibliotekę Python

router = APIRouter(prefix="/api/translate", tags=["translate"])

# Katalogi (te same co w main.py)
UPLOAD_DIR = Path("/tmp/pdf_rider_uploads")
CONVERTED_DIR = Path("/tmp/pdf_rider_converted")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CONVERTED_DIR.mkdir(parents=True, exist_ok=True)

class TranslateRequest(BaseModel):
    """Żądanie tłumaczenia PDF"""
    source_lang: str = "en"      # Język źródłowy
    target_lang: str = "pl"      # Język docelowy
    translator: str = "openai"   # Silnik tłumaczenia
    model: Optional[str] = None  # Model (np. "gpt-4o-mini")
    output_format: str = "pdf"   # "pdf" lub "docx"

class TranslateResponse(BaseModel):
    """Odpowiedź z wynikiem tłumaczenia"""
    success: bool
    message: str
    output_url: Optional[str] = None
    output_path: Optional[str] = None


@router.post("/pdf")
async def translate_pdf_endpoint(
    file: UploadFile = File(...),
    source_lang: str = "en",
    target_lang: str = "pl",
    translator: str = "openai",
    model: Optional[str] = None
):
    """
    Tłumaczy cały plik PDF na inny język.
    
    **Działanie:**
    1. Otwiera PDF
    2. Wyodrębnia tekst ze wszystkich stron
    3. Tłumaczy za pomocą wybranego silnika
    4. Generuje nowy PDF z przetłumaczonym tekstem (lub DOCX)
    
    **Uwaga:** Do tłumaczenia Google/DeepL/OpenAI potrzebne są klucze API w zmiennych środowiskowych.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Tylko pliki PDF są obsługiwane")

    job_id = str(uuid.uuid4())[:8]
    input_pdf = UPLOAD_DIR / f"{job_id}_input.pdf"
    output_pdf = CONVERTED_DIR / f"{job_id}_translated.pdf"

    try:
        # Zapisz PDF
        with input_pdf.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Tłumacz – używając istniejącego silnika pdf2zh
        # Komenda: python -m pdf2zh --input input.pdf --output output.pdf --lang_in en --lang_out pl --translator openai
        cmd = [
            "python", "-m", "pdf2zh",
            "--input", str(input_pdf),
            "--output", str(output_pdf),
            "--lang_in", source_lang,
            "--lang_out", target_lang,
            "--translator", translator
        ]
        if model:
            cmd.extend(["--model", model])

        # Uruchom tłumaczenie
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(Path(__file__).parent.parent.parent))
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Tłumaczenie nieudane: {result.stderr}")

        if not output_pdf.exists():
            raise HTTPException(status_code=500, detail="Plik wyjściowy nie został utworzony")

        return FileResponse(
            path=str(output_pdf),
            filename=f"{Path(file.filename).stem}_translated.pdf",
            media_type="application/pdf"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Sprzątaj
        try:
            if input_pdf.exists():
                input_pdf.unlink()
            # output_pdf zostanie usunięty po pobraniu przez FileResponse
        except Exception:
            pass


@router.post("/text")
async def translate_text_endpoint(
    text: str,
    source_lang: str = "en",
    target_lang: str = "pl",
    translator: str = "openai",
    model: Optional[str] = None
):
    """
    Tłumaczy pojedynczy fragment tekstu.
    Używa tych samych silników co tłumaczenie PDF.
    """
    try:
        # Load translator config
        from app.tools.pdf2zh.translator import BaseTranslator, ConfigManager
        
        # Pobierz klasę tłumacza
        translator_class = ConfigManager.get_translator_by_name(translator)
        if not translator_class:
            raise HTTPException(status_code=400, detail=f"Nieznany silnik: {translator}")

        # Stwórz instancję (potrzebne env variables)
        translator_instance = translator_class(
            lang_in=source_lang,
            lang_out=target_lang,
            model=model or "",
            ignore_cache=False
        )
        
        # Tłumacz
        translated = translator_instance.translate(text)
        
        return {
            "success": True,
            "source_text": text,
            "translated_text": translated,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "translator": translator
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/engines")
async def list_translation_engines():
    """
    Zwraca listę dostępnych silników tłumaczenia.
    """
    from app.tools.pdf2zh.translator import __dict__ as translator_dict
    
    # Wszystkie klasy dziedziczące z BaseTranslator
    engines = []
    for name, obj in translator_dict.items():
        if isinstance(obj, type) and hasattr(obj, 'name') and obj.__base__.__name__ == 'BaseTranslator':
            engines.append({
                "name": obj.name,
                "class": name,
                "envs": obj.envs if hasattr(obj, 'envs') else {}
            })
    
    return {"engines": engines}


@router.post("/extract-text")
async def extract_text_from_pdf(file: UploadFile = File(...)):
    """
    Wyodrębnij tekst z PDF (przed tłumaczeniem).
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Tylko pliki PDF")

    job_id = str(uuid.uuid4())[:8]
    pdf_path = UPLOAD_DIR / f"{job_id}_temp.pdf"

    try:
        with pdf_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Wyodrębnij tekst za pomocą PyMuPDF
        import fitz
        doc = fitz.open(str(pdf_path))
        all_text = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            all_text.append({
                "page": page_num + 1,
                "text": text,
                "char_count": len(text)
            })
        doc.close()

        return {
            "success": True,
            "filename": file.filename,
            "total_pages": len(all_text),
            "pages": all_text,
            "full_text": "\n\n".join([p["text"] for p in all_text])
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        try:
            if pdf_path.exists():
                pdf_path.unlink()
        except Exception:
            pass
