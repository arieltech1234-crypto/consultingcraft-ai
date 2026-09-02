from ai.bullet_selector import _trim_to_count
from ai.schema import Entry, Group, Section


def _section(bullets_per_group):
    return Section(
        section_name="Work Experience",
        entries=[
            Entry(
                header_left="Company",
                groups=[Group(bullets=list(bullets)) for bullets in bullets_per_group],
            )
        ],
    )


def test_trim_cuts_down_to_exact_count_across_groups():
    section = _section([["a", "b", "c"], ["d", "e"]])
    _trim_to_count(section, 4)
    total = sum(len(g.bullets) for e in section.entries for g in e.groups)
    assert total == 4
    assert section.entries[0].groups[0].bullets == ["a", "b", "c"]
    assert section.entries[0].groups[1].bullets == ["d"]


def test_trim_leaves_untouched_when_already_within_budget():
    section = _section([["a", "b"]])
    _trim_to_count(section, 5)
    total = sum(len(g.bullets) for e in section.entries for g in e.groups)
    assert total == 2


def test_trim_empties_later_groups_once_budget_exhausted():
    section = _section([["a", "b"], ["c", "d"], ["e"]])
    _trim_to_count(section, 2)
    assert section.entries[0].groups[0].bullets == ["a", "b"]
    assert section.entries[0].groups[1].bullets == []
    assert section.entries[0].groups[2].bullets == []
