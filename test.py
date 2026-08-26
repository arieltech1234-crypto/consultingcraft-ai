import os
import streamlit as st
api_key = st.secrets["GROQ_API_KEY"] if "GROQ_API_KEY" in st.secrets else ""

from src.ai.section_mapper import SectionMapper
mapper = SectionMapper(api_key=api_key)
res = mapper.map_lines_to_sections(["WORK EXPERIENCE", "EDUCATION"], "I worked at Google as a PM. I did a lot of stuff.")
print(res.model_dump_json(indent=2))
