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
        # The real export uses "at least" line spacing (CVGenerator.
        # _apply_layout), so a configured value below what Arial actually
        # needs for a line (confirmed empirically: single-spaced Arial needs
        # roughly 1.15x its point size) is never really used -- Word fills
        # in the natural height regardless of how low line_spacing_pt is
        # set. This estimate is used both as a fallback when no real
        # renderer is available AND to size how much content gets selected
        # in the first place (PageBudgetCalculator.calculate_budget) -- an
        # optimistic assumption here doesn't just mis-predict a page count,
        # it causes more bullets to be selected than can ever actually fit,
        # which no amount of later spacing tightening can undo. So this
        # floors at the safe (not the tightest-looking) natural minimum.
        self.estimation_line_spacing_pt = max(self.line_spacing_pt, self.font_size * 1.15)

    def calculate_budget(self, section_names: list[str]) -> dict:
        usable_height_pt = (
            A4_HEIGHT_INCHES - self.top_margin - self.bottom_margin
        ) * PTS_PER_INCH
        header_overhead_pt = 48
        section_overhead_pt = len(section_names) * (
            self.section_spacing_pt + self.font_size + 5
        )
        bullet_height_pt = self.estimation_line_spacing_pt + self.sub_section_spacing_pt
        remaining_pt = max(0, usable_height_pt - header_overhead_pt - section_overhead_pt)
        # A ~5% safety margin: this budget feeds bullet selection before the
        # document is ever rendered, so it's working from an approximation.
        # Landing a little under one page from a slight under-selection is
        # recoverable (nothing to fix); landing over from a slight
        # over-selection means real overflow the user has to manually trim.
        total_bullet_lines = max(1, int(0.95 * remaining_pt / bullet_height_pt))
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
                used_height_pt += self.estimation_line_spacing_pt + 2

                for group in entry.get("groups", []):
                    # Sub-header overhead
                    if group.get("group_name") or group.get("group_summary"):
                        used_height_pt += self.estimation_line_spacing_pt + 1

                    for bullet in group.get("bullets", []):
                        if not str(bullet).strip():
                            continue
                        lines = self._wrapped_line_count(str(bullet))
                        wrapped_lines += lines
                        used_height_pt += (
                            lines * self.estimation_line_spacing_pt + self.sub_section_spacing_pt
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

    def _characters_per_line(self) -> int:
        # 0.1in accounts for the bullet glyph + hanging indent that a real
        # "List Bullet" paragraph reserves on every line (including wrapped
        # continuation lines) -- omitting it understates real usable width.
        usable_width_pt = (
            A4_WIDTH_INCHES - (2 * self.side_margin) - 0.1
        ) * PTS_PER_INCH
        # 0.48 (not a wider guess like 0.56): measured directly against the
        # user's real reference resume -- genuine one-line Arial bullets
        # there run 116-127 characters at 9pt/0.4in margins, which only
        # backs out to ~0.47-0.48x the font's point size per character.
        average_character_width = max(4.0, self.font_size * 0.48)
        return max(20, int(usable_width_pt / average_character_width))

    def characters_per_line(self) -> int:
        """Usable character width of one line at the current font size and
        margins -- the real target for "reaches the right margin", since
        word count is only an approximation of it (word length varies)."""
        return self._characters_per_line()

    def target_character_band(self) -> tuple[int, int]:
        """(min, max) character-count target for a bullet to read as
        filling the line close to the right margin without wrapping.
        Max is the hard wrap ceiling; min allows some natural slack rather
        than demanding every bullet hit the ceiling exactly."""
        max_chars = self._characters_per_line()
        min_chars = max(20, int(max_chars * 0.85))
        return min_chars, max_chars

    def wrapped_line_count(self, text: str) -> int:
        """How many visual lines `text` wraps to at the current font size
        and margins -- e.g. to check a bullet actually fits one line."""
        return self._wrapped_line_count(text)

    def _wrapped_line_count(self, text: str) -> int:
        characters_per_line = self._characters_per_line()

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

    def max_words_for_one_line(self) -> int:
        """A safe (not exact) word-count ceiling for a bullet to fit on a
        single visual line at the current font size and margins, assuming a
        typical business-English average word length. Word count is an
        approximation of true rendered width -- it can't guarantee every
        bullet fits one line (a few long words could still wrap), but gives
        the drafting/optimization steps a realistic target instead of a
        fixed number unrelated to the actual page width."""
        characters_per_line = self._characters_per_line()
        # Measured directly against the user's real reference resume's own
        # one-line bullets (~5.8 chars/word including the space) rather than
        # this tool's own drafted output (which measured ~7.35 -- AI-style
        # bullets lean on longer jargon/compound words). Hitting this target
        # word count with real content requires drafting in concise,
        # common-word style, not just any words that add up to the count
        # (see the drafter/optimizer prompts).
        average_word_length_with_space = 5.8
        return max(6, int(characters_per_line / average_word_length_with_space))

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


# Floors for a maximally dense, tight one-pager, matching the user's own
# reference resume: it uses "at least" line spacing pinned near zero (Word
# fills in whatever the font actually needs) and effectively zero paragraph
# spacing everywhere -- sections are separated by their header's background
# color, not whitespace.
MIN_LINE_SPACING_PT = 1.0
MIN_SECTION_SPACING_PT = 0.0
MIN_SUB_SECTION_SPACING_PT = 0.0


def fit_to_one_page(schema_dict: dict, layout_preferences: dict, has_contact: bool = True) -> tuple[dict, dict]:
    """Strictly enforce a one-page layout by tightening spacing.

    Reduces line spacing first, then section spacing, then bullet spacing --
    each down to its floor -- re-checking the fast layout estimate after each
    step until it reports a single page or every spacing knob is at its
    floor. Font size and margins are left untouched; the caller (content
    selection, manual trimming) is responsible for cases too long to fit
    even at the tightest spacing.
    """
    prefs = dict(layout_preferences)
    prefs.setdefault("font_size", 10)
    prefs.setdefault("line_spacing_pt", float(prefs["font_size"]) + 1)
    prefs.setdefault("section_spacing_pt", 6)
    prefs.setdefault("sub_section_spacing_pt", 2.5)

    estimate = PageBudgetCalculator(prefs).estimate_fit(schema_dict, has_contact=has_contact)
    while not estimate["fits_one_page"]:
        if prefs["line_spacing_pt"] > MIN_LINE_SPACING_PT:
            prefs["line_spacing_pt"] = round(max(MIN_LINE_SPACING_PT, prefs["line_spacing_pt"] - 0.5), 2)
        elif prefs["section_spacing_pt"] > MIN_SECTION_SPACING_PT:
            prefs["section_spacing_pt"] = round(max(MIN_SECTION_SPACING_PT, prefs["section_spacing_pt"] - 0.5), 2)
        elif prefs["sub_section_spacing_pt"] > MIN_SUB_SECTION_SPACING_PT:
            prefs["sub_section_spacing_pt"] = round(max(MIN_SUB_SECTION_SPACING_PT, prefs["sub_section_spacing_pt"] - 0.25), 2)
        else:
            break  # every spacing knob is at its floor; content must be trimmed instead

        estimate = PageBudgetCalculator(prefs).estimate_fit(schema_dict, has_contact=has_contact)

    return prefs, estimate
