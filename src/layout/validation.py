"""Optional rendered page validation with a deterministic estimate fallback."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def validate_docx_pages(docx_bytes: bytes, estimate: dict) -> dict:
    """Return a real rendered page count when a renderer is available,
    otherwise the layout estimate.

    The method is surfaced to the user so a portfolio prototype never presents an
    estimate as a physical-layout guarantee. Tries LibreOffice first (works
    cross-platform, including most deployment targets), then Microsoft Word
    via COM automation on Windows (common for local development where Word
    is installed but LibreOffice isn't) -- the fast layout estimate alone can
    understate real word-wrap behavior, so an actual renderer is preferred
    whenever one is available.
    """
    executable = shutil.which("soffice") or shutil.which("libreoffice")
    if executable:
        report = _validate_with_libreoffice(docx_bytes, estimate, executable)
        if report is not None:
            return report

    report = _validate_with_word(docx_bytes, estimate)
    if report is not None:
        return report

    return {
        **estimate,
        "verification": "estimated",
        "note": "Rendered validation is unavailable in this environment.",
    }


def _validate_with_libreoffice(docx_bytes: bytes, estimate: dict, executable: str) -> dict | None:
    try:
        # PDF parsing is only needed when a local office renderer is available.
        # Keeping this import lazy lets the rest of the app run in lightweight
        # environments and surfaces an honest estimate instead of crashing.
        from pypdf import PdfReader

        with tempfile.TemporaryDirectory(prefix="consultingcraft_") as directory:
            temp_dir = Path(directory)
            source = temp_dir / "candidate_cv.docx"
            source.write_bytes(docx_bytes)
            subprocess.run(
                [
                    executable,
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(temp_dir),
                    str(source),
                ],
                check=True,
                capture_output=True,
                timeout=30,
            )
            pdf_path = temp_dir / "candidate_cv.pdf"
            page_count = len(PdfReader(str(pdf_path)).pages)
            return {
                **estimate,
                "fits_one_page": page_count == 1,
                "estimated_pages": page_count,
                "method": "rendered PDF (LibreOffice)",
                "verification": "rendered",
                "note": "Validated by rendering the DOCX to PDF with LibreOffice.",
            }
    except Exception:
        return None  # fall through to another renderer, or the estimate


def _validate_with_word(docx_bytes: bytes, estimate: dict) -> dict | None:
    if sys.platform != "win32":
        return None
    try:
        import win32com.client
    except ImportError:
        return None

    try:
        with tempfile.TemporaryDirectory(prefix="consultingcraft_") as directory:
            source = Path(directory) / "candidate_cv.docx"
            source.write_bytes(docx_bytes)

            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            word.DisplayAlerts = 0
            try:
                document = word.Documents.Open(str(source), ReadOnly=True)
                try:
                    document.Repaginate()
                    page_count = int(document.ComputeStatistics(2))  # wdStatisticPages
                finally:
                    document.Close(False)
            finally:
                word.Quit()

        return {
            **estimate,
            "fits_one_page": page_count == 1,
            "estimated_pages": page_count,
            "method": "rendered DOCX (Word)",
            "verification": "rendered",
            "note": "Validated by opening the DOCX in Microsoft Word.",
        }
    except Exception:
        return None  # fall through to the estimate
