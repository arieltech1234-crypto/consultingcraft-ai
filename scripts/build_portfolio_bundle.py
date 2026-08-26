"""Create a shareable ZIP using a strict source allow-list."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "dist" / "ConsultingCraft_AI_portfolio.zip"
TOP_LEVEL_FILES = {
    ".env.example",
    ".gitignore",
    "LICENSE",
    "README.md",
    "app.py",
    "pyproject.toml",
    "requirements-dev.txt",
    "requirements.txt",
    "run_app.ps1",
    "streamlit_app.py",
}
INCLUDED_ROOTS = (
    ROOT / ".github" / "workflows",
    ROOT / ".streamlit",
    ROOT / "data" / "demo",
    ROOT / "docs",
    ROOT / "scripts",
    ROOT / "src",
    ROOT / "tests",
)
FORBIDDEN_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "master_cv",
    "references",
    "temp",
}


def included_files() -> list[Path]:
    files = [ROOT / name for name in TOP_LEVEL_FILES]
    for source_root in INCLUDED_ROOTS:
        if source_root.exists():
            files.extend(path for path in source_root.rglob("*") if path.is_file())
    safe_files = []
    for path in files:
        relative = path.relative_to(ROOT)
        if any(part in FORBIDDEN_PARTS for part in relative.parts):
            continue
        if path.name in {"secrets.toml", ".env"} or path.suffix == ".pyc":
            continue
        safe_files.append(path)
    return sorted(set(safe_files))


def build_bundle(output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    files = included_files()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())
        manifest = "\n".join(
            [
                "ConsultingCraft AI sanitized portfolio bundle",
                "",
                "Excluded: local secrets, private CVs, reference resumes, temp files, and virtual environments.",
                "",
                "Included files:",
                *(f"- {path.relative_to(ROOT).as_posix()}" for path in files),
            ]
        )
        archive.writestr("PORTFOLIO_BUNDLE_MANIFEST.txt", manifest)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    result = build_bundle(arguments.output.resolve())
    print(f"Created {result} ({result.stat().st_size:,} bytes)")
