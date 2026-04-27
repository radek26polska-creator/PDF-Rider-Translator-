"""
Backend API dla PDF Rider - FastAPI
 Endpointy:
 - POST /api/convert-pdf-to-docx  - konwersja PDF → DOCX
 - GET  /health                   - status serwera
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import shutil
import uuid
from typing import Optional

from converter import PDFtoDOCXConverter
from translate import router as translate_router  # nowy moduł tłumaczenia

app = FastAPI(title="PDF Rider Translator API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(translate_router)

# Katalogi tymczasowe
UPLOAD_DIR = Path("/tmp/pdf_rider_uploads")
CONVERTED_DIR = Path("/tmp/pdf_rider_converted")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CONVERTED_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "PDF Rider Backend"}


@app.post("/api/convert-pdf-to-docx")
async def convert_pdf_to_docx(file: UploadFile = File(...)):
    """
    Konwertuj plik PDF do DOCX z zachowaniem formatowania.
    Wysyłaj plik PDF jako multipart/form-data.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Tylko pliki PDF są obsługiwane")

    # Generuj unikalne nazwy plików
    job_id = str(uuid.uuid4())[:8]
    pdf_path = UPLOAD_DIR / f"{job_id}_input.pdf"
    docx_path = CONVERTED_DIR / f"{job_id}_output.docx"

    try:
        # Zapisz przesłany PDF
        with pdf_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Konwertuj
        converter = PDFtoDOCXConverter(str(pdf_path), str(docx_path))
        success = converter.convert()

        if not success or not docx_path.exists():
            raise HTTPException(status_code=500, detail="Błąd konwersji PDF → DOCX")

        # Zwróć plik DOCX
        return FileResponse(
            path=str(docx_path),
            filename=f"{Path(file.filename).stem}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd: {str(e)}")

    finally:
        # Sprzątaj stare pliki (opcjonalnie)
        try:
            if pdf_path.exists():
                pdf_path.unlink()
            if docx_path.exists():
                docx_path.unlink()
        except Exception:
            pass


@app.post("/api/convert-pdf-to-docx/save")
async def convert_and_save(
    file: UploadFile = File(...),
    output_filename: Optional[str] = None
):
    """
    Konwertuj PDF → DOCX i zapisz na serwerze (nie usuwaj po konwersji).
    Użyteczne do wielu operacji.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Tylko pliki PDF")

    job_id = str(uuid.uuid4())[:8]
    pdf_path = UPLOAD_DIR / f"{job_id}_input.pdf"
    docx_filename = output_filename or f"{job_id}_output.docx"
    docx_path = CONVERTED_DIR / docx_filename

    try:
        with pdf_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        converter = PDFtoDOCXConverter(str(pdf_path), str(docx_path))
        converter.convert()

        if not docx_path.exists():
            raise HTTPException(status_code=500, detail="Konwersja nieudana")

        return JSONResponse({
            "success": True,
            "docx_path": str(docx_path),
            "filename": docx_filename,
            "download_url": f"/download/{docx_filename}"
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint do pobierania skonwertowanych plików (jeśli zapisane)
@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = CONVERTED_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Plik nie istnieje")
    return FileResponse(path=str(file_path), filename=filename)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
