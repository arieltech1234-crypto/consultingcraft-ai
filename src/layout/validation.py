"""Optional rendered page validation with a deterministic estimate fallback."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

def validate_docx_pages(docx_bytes: bytes, estimate: dict) -> dict:
    """Return rendered page count when LibreOffice exists, otherwise an estimate.

    The method is surfaced to the user so a portfolio prototype never presents an
    estimate as a physical-layout guarantee.
    """
    executable = shutil.which("soffice") or shutil.which("libreoffice")
    if not executable:
        return {
            **estimate,
            "verification": "estimated",
            "note": "Rendered validation is unavailable in this environment.",
        }

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
                "method": "rendered PDF",
                "verification": "rendered",
                "note": "Validated by rendering the DOCX to PDF.",
            }
    except Exception as error:
        return {
            **estimate,
            "verification": "estimated",
            "note": f"Rendered validation failed; using estimate ({type(error).__name__}).",
        }
