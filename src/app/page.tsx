"use client";

import { useState, ChangeEvent, FormEvent } from "react";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [converting, setConverting] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState("");

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] || null;
    setFile(selected);
    setFileName(selected ? selected.name : "");
    setError(null);
    setDownloadUrl(null);
  };

  const handleConvert = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Wybierz plik PDF");
      return;
    }

    setConverting(true);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/api/convert-pdf-to-docx", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Błąd konwersji");
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      setDownloadUrl(url);
    } catch (err: any) {
      setError(err.message || "Nieznany błąd");
    } finally {
      setConverting(false);
    }
  };

  const handleDownload = () => {
    if (!downloadUrl) return;
    const a = document.createElement("a");
    a.href = downloadUrl;
    a.download = `${fileName.replace(/\.pdf$/i, "")}.docx`;
    a.click();
  };

  return (
    <main className="min-h-screen bg-neutral-900 text-white flex flex-col items-center justify-center p-8">
      <div className="max-w-xl w-full space-y-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold mb-2">PDF Rider Translator</h1>
          <p className="text-gray-400">
            Konwertuj PDF do edytowalnego DOCX z zachowaniem formatowania, tabel i obrazów.
          </p>
        </div>

        <form onSubmit={handleConvert} className="space-y-6">
          <div className="border-2 border-dashed border-gray-600 rounded-lg p-8 text-center hover:border-blue-500 transition">
            <input
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileChange}
              className="w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700 cursor-pointer"
            />
            {file && (
              <p className="mt-4 text-sm text-green-400">
                Wybrany plik: <span className="font-mono">{fileName}</span>
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={!file || converting}
            className="w-full py-3 px-6 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:from-gray-600 disabled:to-gray-700 disabled:cursor-not-allowed rounded-lg font-semibold text-white transition-all"
          >
            {converting ? "Konwertuję..." : "Konwertuj PDF → DOCX"}
          </button>
        </form>

        {error && (
          <div className="p-4 bg-red-900/50 border border-red-500 rounded-lg text-red-200 text-sm">
            {error}
          </div>
        )}

        {downloadUrl && (
          <div className="p-6 bg-green-900/30 border border-green-500 rounded-lg text-center">
            <p className="text-green-300 mb-4">Konwersja zakończona! Pobierz plik DOCX:</p>
            <button
              onClick={handleDownload}
              className="inline-flex items-center gap-2 px-6 py-3 bg-green-600 hover:bg-green-700 rounded-lg font-semibold transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Pobierz DOCX
            </button>
          </div>
        )}

        <div className="text-xs text-gray-500 text-center space-y-2">
          <p>
            <strong className="text-gray-400">Uwaga:</strong> Upewnij się, że backend Python działa na{" "}
            <code className="bg-gray-800 px-1 rounded">localhost:8000</code>
          </p>
          <p>
            Uruchom backend: <code className="bg-gray-800 px-1 rounded">cd backend && pip install -r requirements.txt && python main.py</code>
          </p>
        </div>
      </div>
    </main>
  );
}
