"""ConsultingCraft AI - recruiter-safe Streamlit portfolio application."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env")

from ai.bullet_drafter import BulletDrafter
from ai.bullet_selector import BulletSelector
from ai.constraint_optimizer import ConstraintOptimizer
from ai.ingestion import DocumentIngester
from ai.jd_analyzer import JDAnalyzer, classify_reference_text, compute_jd_coverage
from ai.reference_analyzer import HARVARD_ACTION_VERBS, ReferenceAnalyzer
from ai.section_mapper import SectionMapper
from app_helpers import (
    build_contact_line,
    meaningful_lines,
    safe_download_stem,
    validate_upload,
)
from ai.schema import ResumeSchema, prune_empty
from demo_content import DEMO_META, DEMO_PROFILE, DEMO_RESUME_SCHEMA
from layout.generator import CVGenerator
from layout.page_budget import (
    MIN_LINE_SPACING_PT,
    MIN_SECTION_SPACING_PT,
    MIN_SUB_SECTION_SPACING_PT,
    PageBudgetCalculator,
)
from layout.validation import validate_docx_pages


st.set_page_config(
    page_title="ConsultingCraft AI",
    page_icon=":material/description:",
    layout="wide",
)


def configured_api_key(user_key: str = "") -> str:
    if user_key.strip():
        return user_key.strip()
    try:
        secret_key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        secret_key = ""
    return secret_key or os.environ.get("GROQ_API_KEY", "")


def resolve_models(api_key: str) -> tuple[str, str | None]:
    from groq import Groq

    available = [model.id for model in Groq(api_key=api_key).models.list().data]
    text_candidates = [
        model
        for model in available
        if not any(token in model.lower() for token in ("whisper", "tts", "vision"))
    ]
    if not text_candidates:
        raise RuntimeError("No text-generation model is available for this API key.")
    
    # Try preferred models in order of capability/availability
    preferred_models = [
        "llama-3.3-70b-versatile",
        "llama3-8b-8192",
        "qwen/qwen3.8-27b",  # Extremely reliable if Llama is absent
        "qwen/qwen3.6-27b",
        "mixtral-8x7b-32768",
        "openai/gpt-oss-20b"
        # Avoid openai/gpt-oss-120b as it's currently bugged returning 0-length strings
    ]
    
    text_model = sorted(text_candidates)[0] # Fallback
    for pref in preferred_models:
        if pref in text_candidates:
            text_model = pref
            break
            
    from ai.ingestion import DocumentIngester

    vision_model = None
    for preferred in DocumentIngester.PREFERRED_VISION_MODELS:
        if preferred in available:
            vision_model = preferred
            break
    if vision_model is None:
        vision_candidates = [
            model
            for model in available
            if any(token in model.lower() for token in ("vision", "vl", "scout", "qwen"))
        ]
        vision_model = sorted(vision_candidates)[0] if vision_candidates else None

    return text_model, vision_model


def clear_old_draft_widgets() -> None:
    for key in list(st.session_state):
        if str(key).startswith("draft_"):
            del st.session_state[key]


def export_fitted_docx(
    structured_data: dict, layout_preferences: dict, has_contact: bool, max_iterations: int = 40
) -> tuple[bytes, dict, dict]:
    """Render the DOCX and strictly enforce one page, tightening line spacing
    first, then section spacing, then bullet spacing, down to a floor.

    The fast layout estimate is only an approximation of real word-wrap
    behavior (it doesn't know a real Word renderer's exact metrics), so
    whenever a real renderer is available (`validate_docx_pages` finds
    LibreOffice) each candidate spacing is checked against the REAL rendered
    page count -- the authority here, not the heuristic -- so "fits one
    page" means the exported file actually does.
    """
    prefs = dict(layout_preferences)
    prefs.setdefault("font_size", 10)
    prefs.setdefault("line_spacing_pt", float(prefs["font_size"]) + 1)
    prefs.setdefault("section_spacing_pt", 6)
    prefs.setdefault("sub_section_spacing_pt", 2.5)

    schema_dict = structured_data.get("resume_schema", {})
    generator = CVGenerator()
    content = b""
    report = {}

    for _ in range(max_iterations):
        content = generator.generate_docx_bytes(structured_data, prefs)
        estimate = PageBudgetCalculator(prefs).estimate_fit(schema_dict, has_contact=has_contact)
        report = validate_docx_pages(content, estimate)
        if report["fits_one_page"]:
            return content, prefs, report

        if prefs["line_spacing_pt"] > MIN_LINE_SPACING_PT:
            prefs["line_spacing_pt"] = round(max(MIN_LINE_SPACING_PT, prefs["line_spacing_pt"] - 0.5), 2)
        elif prefs["section_spacing_pt"] > MIN_SECTION_SPACING_PT:
            prefs["section_spacing_pt"] = round(max(MIN_SECTION_SPACING_PT, prefs["section_spacing_pt"] - 0.5), 2)
        elif prefs["sub_section_spacing_pt"] > MIN_SUB_SECTION_SPACING_PT:
            prefs["sub_section_spacing_pt"] = round(max(MIN_SUB_SECTION_SPACING_PT, prefs["sub_section_spacing_pt"] - 0.25), 2)
        else:
            break  # every spacing knob is at its floor; content must be trimmed instead

    return content, prefs, report


def run_live_pipeline(
    master_upload,
    reference_uploads,
    api_key: str,
    min_words: int,
    max_words: int,
    layout_preferences: dict,
    status,
) -> tuple[dict, dict]:
    text_model, vision_model = resolve_models(api_key)
    ingester = DocumentIngester(api_key=api_key, vision_model=vision_model)

    master_bytes = master_upload.getvalue()
    validate_upload(master_upload.name, master_bytes)
    master_text = ingester.extract_bytes(master_bytes, master_upload.name)
    raw_lines = meaningful_lines(master_text)
    if not raw_lines:
        raise ValueError("No usable experience lines were found in the master CV.")
    status.write(f"Extracted {len(raw_lines)} evidence lines from the master CV.")

    template_sections = ["Education", "Internship", "Work Experience", "Extracurriculars"]
    status.write(f"Using standard resume sections: {', '.join(template_sections)}.")

    reference_texts = []
    for uploaded_file in reference_uploads or []:
        content = uploaded_file.getvalue()
        validate_upload(uploaded_file.name, content)
        reference_texts.append(ingester.extract_bytes(content, uploaded_file.name))

    # Each upload is auto-classified so a JD drives requirement alignment
    # while a shortlisted reference resume drives writing-style modeling —
    # they are not the same task and were previously conflated.
    resume_texts = [t for t in reference_texts if t.strip() and classify_reference_text(t) == "resume"]
    jd_texts = [t for t in reference_texts if t.strip() and classify_reference_text(t) == "jd"]

    mapper = SectionMapper(api_key=api_key, model_name=text_model)
    status.write("Extracting hierarchy and mapping evidence (processing chunks)...")
    mapped_schema = mapper.map_lines_to_sections(template_sections, master_text, status)
    status.write("✓ Mapped evidence to the target hierarchical resume structure.")

    reference_text = "\n".join(resume_texts)
    if reference_text.strip():
        status.write(f"Analyzing writing style from {len(resume_texts)} shortlisted reference resume(s)...")
        patterns = ReferenceAnalyzer(api_key=api_key, model_name=text_model).analyze(
            reference_text, master_text
        )
        status.write("✓ Analyzed the reference writing style.")
    else:
        patterns = {
            "all_recommended_verbs": HARVARD_ACTION_VERBS[:15],
            "harvard_verbs": HARVARD_ACTION_VERBS,
            "structure_pattern": "Result-Action-Context",
            "tone_analysis": "Concise, quantified, outcome-oriented, and factual.",
            "example_bullets": [],
            "key_themes": [],
        }
        status.write("Applied the default evidence-led consulting style.")

    jd_text = "\n".join(jd_texts)
    jd_requirements = {}
    if jd_text.strip():
        status.write(f"Analyzing {len(jd_texts)} job description(s) for role requirements...")
        jd_requirements = JDAnalyzer(api_key=api_key, model_name=text_model).analyze(jd_text)
        status.write(
            f"✓ Extracted {len(jd_requirements.get('required_skills', []))} required skills and "
            f"{len(jd_requirements.get('keywords', []))} keywords from the job description."
        )
        patterns["jd_keywords"] = jd_requirements.get("keywords", [])

    # Weighted per-section line budget (Work Experience gets more room than
    # Extracurriculars, etc.) — converted to a bullet count. Each bullet is
    # exactly one line (min_words/max_words above are sized to the real
    # usable width), so 1 line per bullet, not an average-wraps guess --
    # using 2 here would under-select by roughly half, leaving the page
    # under-filled even though it isn't full.
    section_names = [section.section_name for section in mapped_schema.sections]
    budget_report = PageBudgetCalculator(layout_preferences).calculate_budget(section_names)
    lines_per_bullet_estimate = 1
    selector = BulletSelector(api_key=api_key, model_name=text_model)

    target_themes = list(dict.fromkeys(
        (patterns.get("key_themes") or [])
        + (jd_requirements.get("required_skills") or [])
        + (jd_requirements.get("keywords") or [])
    ))
    selected_schema = mapped_schema
    for i, section in enumerate(selected_schema.sections):
        line_budget = budget_report["per_section_budget"].get(section.section_name, 5)
        target_budget = max(3, round(line_budget / lines_per_bullet_estimate))
        # A budget below the entry count guarantees at least one entry gets
        # zero bullets and is pruned away entirely (e.g. a degree dropping
        # out of Education). Every entry keeps at least one bullet.
        target_budget = max(target_budget, len(section.entries))
        status.write(f"Selecting best bullets for **{section.section_name}** (budget: {target_budget})...")
        selected_schema.sections[i] = selector.select_best_lines(
            section, target_budget, target_themes=target_themes
        )

    selected_schema = prune_empty(selected_schema)
        
    selected_count = sum(len(g.bullets) for s in selected_schema.sections for e in s.entries for g in e.groups)
    status.write(f"✓ Selected {selected_count} high-signal evidence lines.")

    drafter = BulletDrafter(api_key=api_key, model_name=text_model)
    status.write("Drafting bullets into structured Result-Action-Context format...")
    for section in selected_schema.sections:
        for entry in section.entries:
            for group in entry.groups:
                if group.bullets:
                    group.bullets = drafter.draft_bullets_batch(
                        group.bullets,
                        patterns,
                        min_words,
                        max_words,
                        section_context=section.section_name,
                    )

    optimizer = ConstraintOptimizer(
        api_key=api_key, model_name=text_model, max_iterations=3
    )

    # The real goal is each bullet reaching close to the right margin with
    # no wrap -- word count is only an approximation of that (word length
    # varies a lot: "led" vs. "orchestrated"), so this targets rendered
    # character width directly, giving the model each bullet's precise
    # current length so it can add or trim a measured amount rather than
    # guess at a word-count proxy. One pass handles both "too short, leaves
    # a gap at the margin" and "too long, wraps to a second line."
    calculator = PageBudgetCalculator(layout_preferences)
    min_chars, max_chars = calculator.target_character_band()
    status.write(f"Fitting bullets to the printed line width ({min_chars}-{max_chars} characters)...")
    auto_trimmed = 0
    for section in selected_schema.sections:
        for entry in section.entries:
            for group in entry.groups:
                if group.bullets:
                    before = list(group.bullets)
                    group.bullets = optimizer.optimize_for_width(group.bullets, min_chars, max_chars)
                    # A bullet the model could not get under the ceiling is
                    # trimmed deterministically as a last resort. That trim
                    # only ever removes a tail, so the result is a prefix of
                    # what went in -- which is exactly how it's told apart
                    # from a normal model rewrite, and flagged for review
                    # rather than quietly shipping shortened text.
                    auto_trimmed += sum(
                        1
                        for old, new in zip(before, group.bullets)
                        if old != new and old.startswith(new.rstrip("."))
                    )

    multi_line_bullets = sum(
        1
        for section in selected_schema.sections
        for entry in section.entries
        for group in entry.groups
        for bullet in group.bullets
        if calculator.wrapped_line_count(bullet) > 1
    )
    failing = multi_line_bullets
    status.write(
        f"⚠ {multi_line_bullets} bullet(s) still wrap to more than one line "
        "-- shorten these manually in review for a strict one-liner layout."
        if multi_line_bullets
        else "✓ All bullets fit the line width without wrapping."
    )
    if auto_trimmed:
        status.write(
            f"ℹ {auto_trimmed} over-long bullet(s) were trimmed to fit one line "
            "-- check these read well in review."
        )

    return selected_schema, {
        "source_lines": len(raw_lines),
        "selected_lines": selected_count,
        "model": text_model,
        "reference_files": len(reference_uploads or []),
        "reference_resumes_used": len(resume_texts),
        "job_descriptions_used": len(jd_texts),
        "jd_requirements": jd_requirements,
        "constraint_exceptions": failing,
        "multi_line_bullets": multi_line_bullets,
        "pipeline": [
            "In-memory document ingestion",
            "Section mapping and evidence selection",
            "Reference-pattern analysis",
            "RAC bullet drafting",
            "Constraint optimization",
        ],
    }


for key, value in {
    "draft_sections": None,
    "generation_meta": None,
    "profile": copy.deepcopy(DEMO_PROFILE),
    "generation_id": 0,
    "output_bytes": None,
    "output_hash": None,
    "fit_report": None,
}.items():
    st.session_state.setdefault(key, value)


with st.container(horizontal=True, vertical_alignment="center", gap="small"):
    st.title("ConsultingCraft AI")
    st.badge("Student portfolio prototype", color="green")
st.markdown(
    "An AI-assisted workflow that turns a master CV and target role into a "
    "concise, evidence-led one-page draft."
)

value_columns = st.columns(3)
with value_columns[0].container(border=True, height="stretch"):
    st.markdown("**:material/lock: Private by default**")
    st.caption("Uploads remain in memory for the active browser session.")
with value_columns[1].container(border=True, height="stretch"):
    st.markdown("**:material/rate_review: Human in the loop**")
    st.caption("Every generated bullet is editable before export.")
with value_columns[2].container(border=True, height="stretch"):
    st.markdown("**:material/fit_page: Honest fit check**")
    st.caption("Rendered validation when available; a labeled estimate otherwise.")

with st.sidebar:
    st.header("Build settings")
    # Defaults match the user's own working reference resume: 9pt Arial,
    # 0.4in side margins, ~0.2in top/bottom margins.
    font_size = st.slider("Font size", 8.0, 11.0, 9.0, 0.5)
    side_margin = st.slider("Side margins (inches)", 0.3, 0.8, 0.4, 0.05)
    vertical_margin = st.slider("Top and bottom margins (inches)", 0.15, 0.8, 0.2, 0.05)

layout_preferences = {
    "font_size": font_size,
    "side_margin_inches": side_margin,
    "top_margin_inches": vertical_margin,
    "bottom_margin_inches": vertical_margin,
    # Dense, tight one-pager by default, matching the reference resume:
    # "at least" line spacing pinned near zero (Word fills in whatever the
    # font needs -- never clips, unlike a too-small "exactly" value) and
    # zero paragraph spacing, since sections are separated by their header's
    # background color, not whitespace.
    "line_spacing_pt": MIN_LINE_SPACING_PT,
    "section_spacing_pt": MIN_SECTION_SPACING_PT,
    "sub_section_spacing_pt": MIN_SUB_SECTION_SPACING_PT,
}

with st.sidebar:
    # Tied to the actual usable line width (not an arbitrary constant) so
    # bullets are drafted to realistically fit one visual line -- the
    # product wants strict one-liners, not bullets that wrap to two lines.
    # A narrow min/max gap (not a wide range) matters here too: a wide
    # range lets the model land anywhere in it, and shorter-word bullets
    # can end well short of the right margin even at a "valid" word count,
    # leaving visibly wasted trailing space on that line while neighboring
    # bullets reach much closer to it. Keeping the band tight pushes every
    # bullet toward the same width instead.
    max_words = PageBudgetCalculator(layout_preferences).max_words_for_one_line()
    min_words = max(6, max_words - 2)
    st.caption(f"Target bullet length: {min_words}-{max_words} words (fits one line)")

st.subheader("1. Provide evidence and context")
mode = st.radio(
    "Mode",
    ["Portfolio demo (no API key)", "Live AI mode"],
    horizontal=True,
    help=(
        "Portfolio demo loads a fictitious draft instantly with no API key. "
        "Live AI mode runs the staged LLM workflow on your uploaded CV."
    ),
)

if mode == "Portfolio demo (no API key)":
    st.caption(
        "Loads a fictitious candidate draft so the review, editing, and export "
        "steps below can be tried without an API key or real documents."
    )
    demo_clicked = st.button(
        "Load demo draft",
        type="primary",
        icon=":material/auto_awesome:",
        width="stretch",
    )
    if demo_clicked:
        clear_old_draft_widgets()
        st.session_state.profile = copy.deepcopy(DEMO_PROFILE)
        st.session_state.draft_sections = ResumeSchema(**copy.deepcopy(DEMO_RESUME_SCHEMA))
        st.session_state.generation_meta = copy.deepcopy(DEMO_META)
        st.session_state.generation_id += 1
        st.session_state.output_bytes = None
else:
    with st.form("build_inputs"):
        profile_columns = st.columns(2)
        with profile_columns[0]:
            name = st.text_input("Name", value=st.session_state.profile.get("name", ""))
            location = st.text_input(
                "Location", value=st.session_state.profile.get("location", "")
            )
        with profile_columns[1]:
            phone = st.text_input("Phone", value=st.session_state.profile.get("phone", ""))
            linkedin = st.text_input(
                "LinkedIn", value=st.session_state.profile.get("linkedin", "")
            )

        master_upload = None
        reference_uploads = []

        upload_columns = st.columns(2)
        with upload_columns[0]:
            master_upload = st.file_uploader(
                "Master CV",
                type=["docx", "pdf"],
                max_upload_size=8,
                help="Required. Processed in memory and not persisted by the app.",
            )
        with upload_columns[1]:
            reference_uploads = st.file_uploader(
                "Job description or reference resumes",
                type=["docx", "pdf", "png", "jpg", "jpeg"],
                accept_multiple_files=True,
                max_upload_size=8,
                help=(
                    "Mix freely. Each file is auto-classified: a job description drives "
                    "requirement alignment (see the coverage check after generation); a "
                    "shortlisted reference resume drives writing-style modeling."
                ),
            )

        submitted = st.form_submit_button(
            "Generate tailored draft",
            type="primary",
            icon=":material/auto_awesome:",
            width="stretch",
        )

    if submitted:
        profile = {
            "name": name.strip(),
            "phone": phone.strip(),
            "location": location.strip(),
            "linkedin": linkedin.strip(),
        }
        if not profile["name"]:
            st.error("Add a candidate name before generating a draft.")
        elif master_upload is None:
            st.error("Upload a master CV to run the live AI workflow.")
        else:
            api_key = configured_api_key()
            if not api_key:
                st.error(
                    "Live AI mode requires a Groq API key. Portfolio demo mode works without one."
                )
            else:
                with st.status("Running the evidence-to-draft workflow", expanded=True) as status:
                    try:
                        sections, meta = run_live_pipeline(
                            master_upload,
                            reference_uploads,
                            api_key,
                            min_words,
                            max_words,
                            layout_preferences,
                            status,
                        )
                        clear_old_draft_widgets()
                        st.session_state.profile = profile
                        st.session_state.draft_sections = sections
                        st.session_state.generation_meta = meta
                        st.session_state.generation_id += 1
                        st.session_state.output_bytes = None
                        status.update(
                            label="Draft ready for human review",
                            state="complete",
                            expanded=False,
                        )
                    except Exception as error:
                        status.update(
                            label="Generation stopped safely", state="error", expanded=True
                        )
                        st.error(str(error))

if st.session_state.draft_sections:
    st.subheader("2. Review the evidence-led draft")
    meta = st.session_state.generation_meta or {}
    metric_columns = st.columns(5)
    metric_columns[0].metric("Source evidence", meta.get("source_lines", 0))
    metric_columns[1].metric("Selected bullets", meta.get("selected_lines", 0))
    metric_columns[2].metric(
        "Constraint exceptions", meta.get("constraint_exceptions", 0)
    )
    metric_columns[3].metric(
        "Bullets wrapping to 2+ lines", meta.get("multi_line_bullets", 0)
    )
    metric_columns[4].metric(
        "Reference resumes / JDs used",
        f"{meta.get('reference_resumes_used', 0)} / {meta.get('job_descriptions_used', 0)}",
    )

    # Handle Rewrite Action
    if st.session_state.get("pending_rewrite") is not None:
        s_idx = st.session_state.pending_rewrite
        st.session_state.pending_rewrite = None
        api_key = configured_api_key()
        text_model, _ = resolve_models(api_key)
        
        with st.spinner("Rewriting section bullets..."):
            drafter = BulletDrafter(api_key=api_key, model_name=text_model)
            optimizer = ConstraintOptimizer(api_key=api_key, model_name=text_model, max_iterations=2)
            calculator = PageBudgetCalculator(layout_preferences)
            min_chars, max_chars = calculator.target_character_band()
            section_to_rewrite = st.session_state.draft_sections.sections[s_idx]
            jd_requirements = meta.get("jd_requirements") or {}
            rewrite_tone_rules = {"jd_keywords": jd_requirements.get("keywords", [])}

            for entry in section_to_rewrite.entries:
                for group in entry.groups:
                    if group.bullets:
                        group.bullets = drafter.draft_bullets_batch(
                            group.bullets, rewrite_tone_rules, min_words, max_words, section_context=section_to_rewrite.section_name
                        )
                        group.bullets = optimizer.optimize_for_width(group.bullets, min_chars, max_chars)
            st.session_state.generation_id += 1
        st.rerun()

    # Reconstruct the schema based on user edits
    edited_schema = {"sections": []}
    generation_id = st.session_state.generation_id
    
    for s_idx, section in enumerate(st.session_state.draft_sections.sections):
        with st.container(border=True):
            col_title, col_rew, col_del = st.columns([6, 1, 1])
            col_title.markdown(f"**{section.section_name}**")
            
            if col_rew.button("Rewrite", key=f"rew_{generation_id}_{s_idx}", use_container_width=True):
                st.session_state.pending_rewrite = s_idx
                st.rerun()
            if col_del.button("Remove", key=f"del_{generation_id}_{s_idx}", use_container_width=True):
                st.session_state.draft_sections.sections.pop(s_idx)
                st.session_state.generation_id += 1
                st.rerun()
                
            edited_sec = {"section_name": section.section_name, "entries": []}
            
            for e_idx, entry in enumerate(section.entries):
                st.markdown("---")
                col1, col2 = st.columns([3, 1])
                h_left = col1.text_input("Left Header", value=entry.header_left, key=f"hl_{generation_id}_{s_idx}_{e_idx}")
                h_right = col2.text_input("Right Header", value=entry.header_right, key=f"hr_{generation_id}_{s_idx}_{e_idx}")
                summary = st.text_input("Summary", value=entry.summary, key=f"sum_{generation_id}_{s_idx}_{e_idx}")
                
                edited_entry = {
                    "header_left": h_left.strip(),
                    "header_right": h_right.strip(),
                    "summary": summary.strip(),
                    "groups": []
                }
                
                for g_idx, group in enumerate(entry.groups):
                    st.caption(f"Group: {group.group_name}" if group.group_name else "Bullets")
                    edited_group = {
                        "group_name": group.group_name,
                        "group_summary": group.group_summary,
                        "bullets": []
                    }
                    for b_idx, bullet in enumerate(group.bullets):
                        edited_bullet = st.text_area(
                            f"Bullet {b_idx + 1}",
                            value=bullet,
                            height=82,
                            label_visibility="collapsed",
                            key=f"b_{generation_id}_{s_idx}_{e_idx}_{g_idx}_{b_idx}",
                        )
                        edited_group["bullets"].append(edited_bullet.strip())
                    edited_entry["groups"].append(edited_group)
                edited_sec["entries"].append(edited_entry)
            edited_schema["sections"].append(edited_sec)

    jd_requirements = meta.get("jd_requirements") or {}
    jd_terms = list(dict.fromkeys(
        (jd_requirements.get("required_skills") or []) + (jd_requirements.get("keywords") or [])
    ))
    if jd_terms:
        coverage = compute_jd_coverage(edited_schema, jd_requirements)
        with st.expander(
            f"Job description alignment — {len(coverage['covered'])}/{coverage['total']} terms reflected",
            icon=":material/checklist:",
            expanded=bool(coverage["missing"]),
        ):
            if jd_requirements.get("seniority"):
                st.caption(f"Detected seniority: {jd_requirements['seniority']}")
            cov_col, miss_col = st.columns(2)
            with cov_col:
                st.markdown("**Reflected in the draft**")
                for term in coverage["covered"]:
                    st.markdown(f":material/check_circle: {term}")
                if not coverage["covered"]:
                    st.caption("None yet.")
            with miss_col:
                st.markdown("**Not yet reflected**")
                for term in coverage["missing"]:
                    st.markdown(f":material/radio_button_unchecked: {term}")
                if not coverage["missing"]:
                    st.caption("All requirement terms are reflected.")
            st.caption(
                "Only add missing terms to bullets that are truthfully supported by your "
                "master CV — do not fabricate skills to match the job description."
            )

    if st.button("+ Add New Section", key=f"add_sec_{generation_id}"):
        from ai.schema import Section
        st.session_state.draft_sections.sections.append(Section(section_name="New Section"))
        st.session_state.generation_id += 1
        st.rerun()

    current_hash = hashlib.sha256(
        json.dumps(edited_schema, sort_keys=True).encode("utf-8")
    ).hexdigest()
    
    contact_line = build_contact_line(st.session_state.profile)
    # The new structured data is just the full schema dict + contact info
    structured_data = {
        "name": st.session_state.profile["name"],
        "contact_line": contact_line,
        "resume_schema": edited_schema,
    }

    with st.container(horizontal=True, horizontal_alignment="right"):
        export_clicked = st.button(
            "Build portfolio-ready DOCX",
            type="primary",
            icon=":material/download:",
        )

    if export_clicked:
        # Strictly enforce one page: tighten line spacing (then section, then
        # bullet spacing), re-rendering and checking the REAL page count
        # (LibreOffice, when available) after each step rather than trusting
        # the fast layout estimate alone.
        with st.spinner("Fitting to one page..."):
            document_bytes, tightened_preferences, report = export_fitted_docx(
                structured_data, layout_preferences, has_contact=bool(contact_line)
            )
        st.session_state.output_bytes = document_bytes
        st.session_state.output_hash = current_hash
        st.session_state.fit_report = report
        st.session_state.applied_layout_preferences = tightened_preferences

    if (
        st.session_state.output_bytes is not None
        and st.session_state.output_hash == current_hash
    ):
        report = st.session_state.fit_report
        if report["fits_one_page"]:
            st.success(
                f"One-page {report['method']} passed at "
                f"{report['utilization']:.0%} estimated page utilization.",
                icon=":material/check_circle:",
            )
        else:
            pages = report["estimated_pages"]
            cut_fraction = round(100 * (pages - 1) / pages / 5) * 5
            st.warning(
                f"Still {pages} pages ({report['method']}) even at the tightest spacing "
                f"this tool will apply automatically. Line/section/bullet spacing is already at "
                f"its floor -- the remaining content itself doesn't fit one page at this font "
                f"size. Try removing or merging roughly {cut_fraction}% of the bullets below, "
                "or reduce the font size in the sidebar.",
                icon=":material/warning:",
            )
        applied = st.session_state.get("applied_layout_preferences") or {}
        if applied and applied.get("line_spacing_pt") != layout_preferences.get("line_spacing_pt"):
            st.caption(
                f"Line spacing auto-tightened to {applied['line_spacing_pt']}pt "
                f"(from {layout_preferences['line_spacing_pt']}pt) to fit one page."
            )
        st.caption(report["note"])
        filename = f"{safe_download_stem(st.session_state.profile['name'])}_tailored_CV.docx"
        st.download_button(
            "Download DOCX",
            data=st.session_state.output_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            icon=":material/download:",
            width="stretch",
        )

with st.expander("Product case study", icon=":material/account_tree:"):
    st.markdown(
        """
        **Problem:** candidates repeatedly tailor dense CVs to role-specific signals
        while balancing evidence quality and physical page constraints.

        **Product decisions:** keep source documents private by default; separate
        evidence selection from rewriting; require human review; and label page-fit
        estimates instead of presenting them as guarantees.

        **Next experiment:** compare recruiter ratings and factual-error rates across
        manual tailoring, a single-prompt baseline, and this staged workflow.
        """
    )

st.caption(
    "Independent student project. Not affiliated with or endorsed by any consulting firm."
)
