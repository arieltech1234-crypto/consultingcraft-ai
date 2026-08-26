import re
import zipfile

from scripts.build_portfolio_bundle import build_bundle


def test_portfolio_bundle_excludes_private_material_and_secrets(tmp_path):
    output = build_bundle(tmp_path / "portfolio.zip")
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        assert ".env" not in names
        assert ".streamlit/secrets.toml" not in names
        assert "run_app.ps1" in names
        assert not any(name.startswith("data/master_cv/") for name in names)
        assert not any(name.startswith("data/references/") for name in names)
        assert not any(name.startswith("temp/") for name in names)

        source_text = "\n".join(
            archive.read(name).decode("utf-8", errors="ignore")
            for name in names
            if name.endswith((".py", ".md", ".toml", ".txt", ".example"))
        )
        assert re.search(r"gsk_[A-Za-z0-9]{20,}", source_text) is None
