from ai.constraint_optimizer import ConstraintOptimizer, _clamp_to_width


def test_clamp_prefers_dropping_a_trailing_clause():
    bullet = (
        "Served 660+ patients via a 220-unit blood drive at Goa Medical College, "
        "extending outreach to two additional rural districts nearby"
    )
    result = _clamp_to_width(bullet, 100)
    assert len(result) <= 100
    assert result.endswith(".")
    assert "extending" not in result
    assert result.startswith("Served 660+ patients")


def test_clamp_falls_back_to_word_boundary_when_no_late_clause_break():
    bullet = "Directed " + " ".join(["delivery"] * 40)
    result = _clamp_to_width(bullet, 80)
    assert len(result) <= 80
    # Never cuts mid-word.
    assert "deliver." not in result
    assert result.endswith(".")


def test_clamp_leaves_a_bullet_already_within_width_untouched():
    bullet = "Cut reporting runtime by 70% across 15 workflows."
    assert _clamp_to_width(bullet, 120) == bullet


def test_clamp_only_removes_text_never_rewrites_it():
    bullet = "Recovered 750+ hours annually by automating daily reconciliation across every regional feed"
    result = _clamp_to_width(bullet, 60)
    assert bullet.startswith(result.rstrip("."))


def test_optimize_for_width_leaves_bullets_already_in_band_untouched(monkeypatch):
    optimizer = ConstraintOptimizer(api_key="fake-key-for-test")

    def boom(self, prompt):
        raise AssertionError("should not call the model when nothing needs fixing")

    monkeypatch.setattr(ConstraintOptimizer, "_call_with_retry", boom)

    bullet = "x" * 90
    result = optimizer.optimize_for_width([bullet], min_chars=80, max_chars=100)
    assert result == [bullet]


def test_optimize_for_width_expands_a_short_bullet(monkeypatch):
    optimizer = ConstraintOptimizer(api_key="fake-key-for-test")

    def fake_call(self, prompt):
        assert "characters" in prompt
        return "x" * 95

    monkeypatch.setattr(ConstraintOptimizer, "_call_with_retry", fake_call)

    short_bullet = "x" * 40
    result = optimizer.optimize_for_width([short_bullet], min_chars=80, max_chars=100)
    assert len(result[0]) == 95


def test_optimize_for_width_shortens_an_overflowing_bullet(monkeypatch):
    optimizer = ConstraintOptimizer(api_key="fake-key-for-test")

    def fake_call(self, prompt):
        return "x" * 90

    monkeypatch.setattr(ConstraintOptimizer, "_call_with_retry", fake_call)

    long_bullet = "x" * 200
    result = optimizer.optimize_for_width([long_bullet], min_chars=80, max_chars=100)
    assert len(result[0]) == 90
