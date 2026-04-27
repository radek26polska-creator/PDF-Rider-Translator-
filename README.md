# PDF Rider Nex – Czytnik, Edytor i Tłumacz PDF

Pełny zestaw narzędzi do pracy z plikami PDF:
- ✏️ **Edycja PDF** – tekst, obrazy, kształty, adnotacje, formularze
- 🔄 **Konwersja PDF → DOCX** – idealne odwzorowanie layoutu, tabele, tekst edytowalny
- 🌐 **Tłumaczenie PDF** – wielojęzyczny silnik (Google, DeepL, OpenAI, itp.)

---

## 📁 Struktura projektu

```
PDF-Translator-Rider/
├── backend/                  # Python FastAPI backend
│   ├── converter.py          # Konwerter PDF → DOCX
│   ├── main.py               # API endpoints
│   └── requirements.txt      # Zależności Python
├── app/                      # Aplikacja desktopowa PyQt5
│   ├── gui/                  # Interfejs użytkownika
│   ├── tools/
│   │   ├── edit_tools.py     # Narzędzia edycji PDF
│   │   └── pdf2zh/           # Silnik tłumaczenia PDF
│   └── core/
├── src/app/                  # Frontend Next.js (web)
│   └── page.tsx              # Strona konwertera PDF → DOCX
├── package.json              # Next.js, React, Tailwind
└── README.md
```

---

## 🚀 Szybki start

### 1. Frontend (Next.js – web)

```bash
# Zainstaluj zależności
bun install

# Uruchom dev server (port 3000)
bun dev
```

Otwórz: `http://localhost:3000`

---

### 2. Backend Python (FastAPI – konwerter PDF → DOCX)

```bash
# Przejdź do backendu
cd backend

# Zainstaluj zależności Python (potrzebny Python 3.10+)
pip install -r requirements.txt

# Uruchom serwer API (port 8000)
python main.py
# lub: uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Backend działa na `http://localhost:8000`

---

### 3. Aplikacja desktopowa (PyQt5)

```bash
# Zainstaluj zależności
pip install PyQt5 PyMuPDF pdfplumber python-docx

# Uruchom aplikację
python main.py
```

---

## 🛠️ Funkcjonalności

### Edycja PDF (`app/tools/edit_tools.py`)
- **Tekst**: dodawanie, edycja, usuwanie, zmiana czcionki/rozmiaru/koloru
- **Adnotacje**: podświetlanie, przekreślenie, podkreślenie, notatki
- **Kształty**: prostokąt, okrąg, linia, strzałka
- **Obrazy**: dodawanie z pliku i ze schowka
- **Formularze**: pola tekstowe, checkboxy, radio buttons
- **Zarządzanie stronami**: dodawaj, usuwaj, obracaj, zmieniaj kolejność
- **Wyszukiwanie**: znajdź tekst na stronie

### Konwerter PDF → DOCX (`backend/converter.py`)
**Idealne odwzorowanie:**
- ✅ Tekst edytowalny (nie jako obraz!)
- ✅ Formatowanie (pogrubienie, kursywa, rozmiary czcionek)
- ✅ Tabele (zachowana struktura, edytowalne komórki)
- ✅ Obrazy
- ✅ Pozycjonowanie i marginesy
- ✅ Zachowanie układu stron

**API Endpoint:**
```
POST http://localhost:8000/api/convert-pdf-to-docx
Content-Type: multipart/form-data (plik PDF)

Response: plik DOCX (binary)
```

### Tłumaczenie PDF (`app/tools/pdf2zh/`)
Wiele silników tłumaczenia:
- OpenAI GPT-4, GPT-3.5
- DeepL (klucz API)
- Google Translate
- Azure, Tencent, Ollama, Groq, Silicon, Gemini
- I wiele innych

---

## 📦 Zależności

### Python (backend + desktop)
```txt
PyMuPDF>=1.24.0
python-docx>=1.1.0
pdfplumber>=0.10.0
Pillow>=10.0.0
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
python-multipart>=0.0.9
PyQt5 (desktop)
```

### Node.js / Next.js (frontend)
```json
"next": "^16.1.3",
"react": "^19.2.3",
"react-dom": "^19.2.3",
"tailwindcss": "^4.1.17"
```

---

## 🧪 Testowanie konwersji

1. Uruchom backend: `cd backend && python main.py`
2. Uruchom frontend: `bun dev`
3. Otwórz `http://localhost:3000`
4. Wybierz plik PDF
5. Kliknij "Konwertuj PDF → DOCX"
6. Pobierz wynikowy plik DOCX

---

## 📝 Uwagi

- Backend używa tymczasowych katalogów `/tmp/pdf_rider_uploads` i `/tmp/pdf_rider_converted`
- Pliki są usuwane po konwersji (opcja `save` pozwala zachować)
- Dla dużych PDFów konwersja może potrwać kilkadziesiąt sekund
- Tabele są wykrywane automatycznie przez `pdfplumber`
- Aplikacja desktopowa (PyQt5) oferuje pełną edycję offline

---

## 🎯 Co dalej?

- [ ] Dodać obsługę OCR (skanowane PDF → tekst)
- [ ] Wbudowany edytor DOCX w web
- [ ] Batch konwersja (wielokrotne pliki)
- [ ] Współpraca z chmurą (Google Drive, Dropbox)
- [ ] Tłumaczenie podczas konwersji (PDF → tłumaczenie → DOCX)

---

## 📄 Licencja

MIT – wolne użytkowanie.
