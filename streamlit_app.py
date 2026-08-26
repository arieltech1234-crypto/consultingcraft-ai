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
from ai.reference_analyzer import HARVARD_ACTION_VERBS, ReferenceAnalyzer
from ai.section_mapper import SectionMapper
from ai.template_parser import TemplateParser
from app_helpers import (
    build_contact_line,
    meaningful_lines,
    safe_download_stem,
    validate_upload,
)
from demo_content import DEMO_META, DEMO_PROFILE, DEMO_SECTIONS
from layout.generator import CVGenerator
from layout.page_budget import PageBudgetCalculator
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
            
    vision_candidates = [
        model
        for model in available
        if any(token in model.lower() for token in ("vision", "vl", "scout"))
    ]
    return text_model, (sorted(vision_candidates)[0] if vision_candidates else None)


def clear_old_draft_widgets() -> None:
    for key in list(st.session_state):
        if str(key).startswith("draft_"):
            del st.session_state[key]


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

    reference_text_parts = []
    for uploaded_file in reference_uploads or []:
        content = uploaded_file.getvalue()
        validate_upload(uploaded_file.name, content)
        reference_text_parts.append(ingester.extract_bytes(content, uploaded_file.name))
    reference_text = "\n".join(reference_text_parts)

    mapper = SectionMapper(api_key=api_key, model_name=text_model)
    status.write("Extracting hierarchy and mapping evidence (processing chunks)...")
    mapped_schema = mapper.map_lines_to_sections(template_sections, master_text, status)
    status.write("✓ Mapped evidence to the target hierarchical resume structure.")

    if reference_text.strip():
        status.write("Analyzing job description and writing style...")
        patterns = ReferenceAnalyzer(api_key=api_key, model_name=text_model).analyze(
            reference_text, master_text
        )
        status.write("Analyzed the job description and reference writing style.")
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

    # Target budget per section (Fallback to 5 per section for now until budget calculator is rewritten)
    target_budget = 5 
    selector = BulletSelector(api_key=api_key, model_name=text_model)
    
    selected_schema = mapped_schema
    for i, section in enumerate(selected_schema.sections):
        status.write(f"Selecting best bullets for **{section.section_name}**...")
        selected_schema.sections[i] = selector.select_best_lines(section, target_budget)
        
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
    
    failing = 0
    status.write("Running constraint optimization passes...")
    for section in selected_schema.sections:
        for entry in section.entries:
            for group in entry.groups:
                if group.bullets:
                    group.bullets = optimizer.optimize_batch(group.bullets, min_words, max_words)
                    failing += sum(1 for b in group.bullets if not min_words <= len(b.split()) <= max_words)

    status.write(
        "✓ Completed three-pass constraint optimization."
        if failing
        else "All drafted bullets passed the configured word-count constraint."
    )
    return selected_schema, {
        "source_lines": len(raw_lines),
        "selected_lines": selected_count,
        "model": text_model,
        "reference_files": len(reference_uploads or []),
        "constraint_exceptions": failing,
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
    font_size = st.slider("Font size", 9.0, 11.0, 10.0, 0.5)
    side_margin = st.slider("Side margins (inches)", 0.4, 0.8, 0.55, 0.05)
    vertical_margin = st.slider("Top and bottom margins (inches)", 0.4, 0.8, 0.5, 0.05)
    max_words = int(24 - ((side_margin - 0.5) * 8))
    min_words = max(14, max_words - 5)
    st.caption(f"Target bullet length: {min_words}-{max_words} words")

layout_preferences = {
    "font_size": font_size,
    "side_margin_inches": side_margin,
    "top_margin_inches": vertical_margin,
    "bottom_margin_inches": vertical_margin,
    "line_spacing_pt": font_size + 1,
    "section_spacing_pt": 6,
    "sub_section_spacing_pt": 2.5,
}

st.subheader("1. Provide evidence and context")
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
                "Live AI mode requires a Groq API key. Demo mode works without one."
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
    metric_columns = st.columns(3)
    metric_columns[0].metric("Source evidence", meta.get("source_lines", 0))
    metric_columns[1].metric("Selected bullets", meta.get("selected_lines", 0))
    metric_columns[2].metric(
        "Constraint exceptions", meta.get("constraint_exceptions", 0)
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
            section_to_rewrite = st.session_state.draft_sections.sections[s_idx]
            
            for entry in section_to_rewrite.entries:
                for group in entry.groups:
                    if group.bullets:
                        group.bullets = drafter.draft_bullets_batch(
                            group.bullets, {}, min_words, max_words, section_context=section_to_rewrite.section_name
                        )
                        group.bullets = optimizer.optimize_batch(group.bullets, min_words, max_words)
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

    if st.button("+ Add New Section", key=f"add_sec_{generation_id}"):
        from src.ai.schema import Section
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
        document_bytes = CVGenerator().generate_docx_bytes(
            structured_data, layout_preferences
        )
        calculator = PageBudgetCalculator(layout_preferences)
        estimate = calculator.estimate_fit(
            edited_schema, has_contact=bool(contact_line)
        )
        st.session_state.output_bytes = document_bytes
        st.session_state.output_hash = current_hash
        st.session_state.fit_report = validate_docx_pages(document_bytes, estimate)

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
            st.warning(
                f"The current draft is likely {report['estimated_pages']} pages. "
                "Shorten bullets or reduce spacing before sharing.",
                icon=":material/warning:",
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
