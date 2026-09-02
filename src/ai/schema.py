from pydantic import BaseModel, Field

class Group(BaseModel):
    group_name: str = Field(default="", description="Optional sub-header, e.g., 'Key Engagements', 'Project X'. Leave empty if just standard bullets.")
    group_summary: str = Field(default="", description="Optional one-line summary of the group/project.")
    bullets: list[str] = Field(default_factory=list, description="The actual bullet points for this group.")

class Entry(BaseModel):
    header_left: str = Field(..., description="The main left header, e.g., 'Thorogood Associates | Consultant' or 'BITS Pilani | B.E. Hons'")
    header_right: str = Field(default="", description="The right-aligned text, typically the date, e.g., 'Aug 16 - Apr 21'")
    summary: str = Field(default="", description="Optional italicized one-line summary directly below the main header.")
    groups: list[Group] = Field(default_factory=list, description="Sub-groups of projects or bullets. If no sub-groups exist, put all bullets in a single default group.")

class Section(BaseModel):
    section_name: str = Field(..., description="The template section name, e.g., 'WORK EXPERIENCE' or 'EDUCATION'")
    entries: list[Entry] = Field(default_factory=list, description="The list of companies, schools, or major entries in this section.")

class ResumeSchema(BaseModel):
    sections: list[Section] = Field(default_factory=list, description="The list of sections making up the resume.")


def prune_empty(schema: ResumeSchema) -> ResumeSchema:
    """Drop groups/entries/sections left with zero bullets after selection.

    Bullet selection operates on a section's total bullet budget, so an
    individual entry or sub-group can legitimately end up with none. Left
    in, those render as orphan headers with no content underneath.
    """
    for section in schema.sections:
        for entry in section.entries:
            entry.groups = [group for group in entry.groups if group.bullets]
        section.entries = [entry for entry in section.entries if entry.groups]
    schema.sections = [section for section in schema.sections if section.entries]
    return schema

