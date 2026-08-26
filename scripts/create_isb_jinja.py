import docx
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER

doc = docx.Document()
style = doc.styles["Normal"]
style.font.name = "Arial"
style.font.size = Pt(10)

# Document margins to match ISB
sections = doc.sections
for section in sections:
    section.top_margin = Inches(0.5)
    section.bottom_margin = Inches(0.5)
    section.left_margin = Inches(0.5)
    section.right_margin = Inches(0.5)

# Header
head_p = doc.add_paragraph()
head_p.paragraph_format.tab_stops.add_tab_stop(Inches(7.27), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.SPACES)
head_r = head_p.add_run("{{ name }}\tLinkedIn URL")
head_r.bold = True
head_r.font.size = Pt(10)

doc.add_paragraph("{% for section in sections %}")

# Section Name
sec_p = doc.add_paragraph()
sec_r = sec_p.add_run("{{ section.section_name|upper }}")
sec_r.bold = True
sec_r.font.size = Pt(10)

doc.add_paragraph("{% for entry in section.entries %}")

# Entry Header
ent_p = doc.add_paragraph()
ent_p.paragraph_format.tab_stops.add_tab_stop(Inches(7.27), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.SPACES)
el = ent_p.add_run("{{ entry.header_left }}")
el.bold = True
er = ent_p.add_run("\t{{ entry.header_right }}")
er.bold = False

doc.add_paragraph("{% if entry.summary %}")
sum_p = doc.add_paragraph()
sum_r = sum_p.add_run("{{ entry.summary }}")
sum_r.italic = True
doc.add_paragraph("{% endif %}")

doc.add_paragraph("{% for group in entry.groups %}")
doc.add_paragraph("{% if group.group_name %}")
grp_p = doc.add_paragraph()
grp_r = grp_p.add_run("{{ group.group_name }}")
grp_r.underline = True
doc.add_paragraph("{% endif %}")

doc.add_paragraph("{% for bullet in group.bullets %}")
bul_p = doc.add_paragraph(style="List Bullet")
bul_r = bul_p.add_run("{{ bullet }}")
doc.add_paragraph("{% endfor %}")
doc.add_paragraph("{% endfor %}")
doc.add_paragraph("{% endfor %}")
doc.add_paragraph("{% endfor %}")

doc.save("data/templates/isb_jinja_template.docx")
print("Template created.")
