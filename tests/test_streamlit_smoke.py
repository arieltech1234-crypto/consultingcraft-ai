from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_app_loads_without_api_key():
    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "streamlit_app.py"),
        default_timeout=20,
    )
    app.run()
    assert not app.exception
    assert any("ConsultingCraft AI" in title.value for title in app.title)


def test_demo_mode_generates_editable_draft():
    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "streamlit_app.py"),
        default_timeout=20,
    )
    app.run()
    generate = next(
        button for button in app.button if button.label == "Generate tailored draft"
    )
    generate.click().run()
    assert not app.exception
    assert len(app.text_area) >= 8
