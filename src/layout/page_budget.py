"""A4 layout budgeting and transparent one-page fit estimation."""

from __future__ import annotations

import math


A4_HEIGHT_INCHES = 11.69
A4_WIDTH_INCHES = 8.27
PTS_PER_INCH = 72


class PageBudgetCalculator:
    def __init__(self, layout_prefs: dict):
        self.font_size = float(layout_prefs.get("font_size", 10))
        self.side_margin = float(layout_prefs.get("side_margin_inches", 0.55))
        self.top_margin = float(layout_prefs.get("top_margin_inches", 0.5))
        self.bottom_margin = float(
            layout_prefs.get("bottom_margin_inches", self.top_margin)
        )
        self.line_spacing_pt = float(
            layout_prefs.get("line_spacing_pt", self.font_size + 1)
        )
        self.section_spacing_pt = float(
            layout_prefs.get("section_spacing_pt", 6)
        )
        self.sub_section_spacing_pt = float(
            layout_prefs.get("sub_section_spacing_pt", 2.5)
        )

    def calculate_budget(self, section_names: list[str]) -> dict:
        usable_height_pt = (
            A4_HEIGHT_INCHES - self.top_margin - self.bottom_margin
        ) * PTS_PER_INCH
        header_overhead_pt = 48
        section_overhead_pt = len(section_names) * (
            self.section_spacing_pt + self.font_size + 5
        )
        bullet_height_pt = self.line_spacing_pt + self.sub_section_spacing_pt
        remaining_pt = max(0, usable_height_pt - header_overhead_pt - section_overhead_pt)
        total_bullet_lines = max(1, int(remaining_pt / bullet_height_pt))
        return {
            "usable_height_pt": round(usable_height_pt, 1),
            "total_overhead_pt": round(header_overhead_pt + section_overhead_pt, 1),
            "bullet_height_pt": round(bullet_height_pt, 1),
            "total_bullet_lines": total_bullet_lines,
            "per_section_budget": self._allocate_budget(
                section_names, total_bullet_lines
            ),
        }

    def estimate_fit(self, schema_dict: dict, has_contact: bool = True) -> dict:
        usable_height_pt = (
            A4_HEIGHT_INCHES - self.top_margin - self.bottom_margin
        ) * PTS_PER_INCH
        used_height_pt = 29 + (15 if has_contact else 0)
        wrapped_lines = 0

        for section in schema_dict.get("sections", []):
            if not section.get("entries"):
                continue
            used_height_pt += self.section_spacing_pt + self.font_size + 5
            
            for entry in section.get("entries", []):
                # Header overhead for an entry (Company Name line)
                used_height_pt += self.line_spacing_pt + 2
                
                for group in entry.get("groups", []):
                    # Sub-header overhead
                    if group.get("group_name") or group.get("group_summary"):
                        used_height_pt += self.line_spacing_pt + 1
                    
                    for bullet in group.get("bullets", []):
                        if not str(bullet).strip():
                            continue
                        lines = self._wrapped_line_count(str(bullet))
                        wrapped_lines += lines
                        used_height_pt += (
                            lines * self.line_spacing_pt + self.sub_section_spacing_pt
                        )

        estimated_pages = max(1, math.ceil(used_height_pt / usable_height_pt))
        return {
            "fits_one_page": estimated_pages == 1,
            "estimated_pages": estimated_pages,
            "used_height_pt": round(used_height_pt, 1),
            "usable_height_pt": round(usable_height_pt, 1),
            "utilization": round(used_height_pt / usable_height_pt, 3),
            "wrapped_lines": wrapped_lines,
            "method": "layout estimate",
        }

    def _wrapped_line_count(self, text: str) -> int:
        usable_width_pt = (
            A4_WIDTH_INCHES - (2 * self.side_margin) - 0.22
        ) * PTS_PER_INCH
        average_character_width = max(4.0, self.font_size * 0.52)
        characters_per_line = max(20, int(usable_width_pt / average_character_width))

        lines = 1
        current = 0
        for word in text.split():
            word_length = len(word) + (1 if current else 0)
            if current and current + word_length > characters_per_line:
                lines += 1
                current = len(word)
            else:
                current += word_length
        return lines

    @staticmethod
    def _allocate_budget(section_names: list[str], total_lines: int) -> dict[str, int]:
        if not section_names:
            return {}

        weights = []
        for name in section_names:
            lowered = name.lower()
            if any(token in lowered for token in ("work", "experience", "product")):
                weights.append(4)
            elif any(token in lowered for token in ("leadership", "project", "extra")):
                weights.append(2)
            else:
                weights.append(1)

        budgets = {name: 1 for name in section_names}
        remaining = max(0, total_lines - len(section_names))
        weight_total = sum(weights)
        fractional = []
        allocated = 0
        for name, weight in zip(section_names, weights):
            exact = remaining * weight / weight_total
            addition = int(exact)
            budgets[name] += addition
            allocated += addition
            fractional.append((exact - addition, name))

        for _, name in sorted(fractional, reverse=True)[: remaining - allocated]:
            budgets[name] += 1
        return budgets
