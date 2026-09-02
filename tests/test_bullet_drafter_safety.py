from ai.bullet_drafter import BulletDrafter, _has_fabricated_currency


def test_flags_currency_invented_from_nothing():
    raw = "Performed live for audiences of 200+ for over a decade."
    drafted = "Orchestrated $200M in brand value through 20+ live performances."
    assert _has_fabricated_currency(raw, drafted) is True


def test_allows_currency_present_in_source():
    raw = "Prevented a mandatory $240K/year licensing upgrade by redesigning the data model."
    drafted = "Averted a $240K/year licensing upgrade by redesigning the reporting data model."
    assert _has_fabricated_currency(raw, drafted) is False


def test_allows_no_currency_either_side():
    raw = "Selected 1 of 2 from 200+ students for regional representation."
    drafted = "Earned regional selection as 1 of 2 among 200+ student athletes."
    assert _has_fabricated_currency(raw, drafted) is False


def test_api_failure_falls_back_to_raw_evidence_not_an_error_string(monkeypatch):
    # Confirmed regression: a transient connection error previously produced
    # a literal "Failed to draft bullet. Error: ..." string that was stored
    # as if it were real bullet content -- and then fed into the optimizer
    # as "content" to shorten, whose refusal ALSO ended up in the resume.
    drafter = BulletDrafter(api_key="fake-key-for-test")

    def boom(self, prompt):
        raise RuntimeError("Connection error.")

    monkeypatch.setattr(BulletDrafter, "_call_with_retry", boom)

    raw = ["Led a 20+ member team delivering campus-wide health initiatives."]
    result = drafter.draft_bullets_batch(raw, {}, 10, 20)

    assert result == raw
    assert "error" not in result[0].lower()
    assert "cannot" not in result[0].lower()
