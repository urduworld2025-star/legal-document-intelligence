from legalintel.models.document import ClauseMatch
from legalintel.risk.flagging import (
    CONFIDENCE_BAND_HIGH,
    CONFIDENCE_BAND_MEDIUM,
    apply_risk_flags,
    band_for_confidence,
    risk_level_for_category,
    summarize_risk,
)


def test_uncapped_liability_is_high_risk() -> None:
    assert risk_level_for_category("Uncapped Liability") == "HIGH"


def test_non_compete_is_medium_risk() -> None:
    assert risk_level_for_category("Non-Compete") == "MEDIUM"


def test_termination_for_convenience_is_medium_risk() -> None:
    assert risk_level_for_category("Termination For Convenience") == "MEDIUM"


def test_governing_law_is_informational() -> None:
    assert risk_level_for_category("Governing Law") == "INFORMATIONAL"


def test_unknown_category_defaults_to_informational() -> None:
    assert risk_level_for_category("Some Future Category") == "INFORMATIONAL"


def test_confidence_at_high_threshold_is_high_band() -> None:
    assert band_for_confidence(CONFIDENCE_BAND_HIGH) == "HIGH"


def test_confidence_just_below_high_threshold_is_medium_band() -> None:
    assert band_for_confidence(CONFIDENCE_BAND_HIGH - 0.001) == "MEDIUM"


def test_confidence_at_medium_threshold_is_medium_band() -> None:
    assert band_for_confidence(CONFIDENCE_BAND_MEDIUM) == "MEDIUM"


def test_confidence_just_below_medium_threshold_is_low_band() -> None:
    assert band_for_confidence(CONFIDENCE_BAND_MEDIUM - 0.001) == "LOW"


def test_confidence_at_zero_is_low_band() -> None:
    assert band_for_confidence(0.0) == "LOW"


def test_confidence_at_one_is_high_band() -> None:
    assert band_for_confidence(1.0) == "HIGH"


def _make_match(category: str, confidence: float) -> ClauseMatch:
    return ClauseMatch(category=category, text="x", confidence=confidence, char_start=0, char_end=1)


def test_apply_risk_flags_sets_both_fields_without_mutating_input() -> None:
    original = _make_match("Uncapped Liability", 0.9)

    flagged = apply_risk_flags([original])

    assert original.risk_level is None
    assert flagged[0].risk_level == "HIGH"
    assert flagged[0].confidence_band == "HIGH"


def test_apply_risk_flags_preserves_clause_order_and_count() -> None:
    matches = [_make_match("Governing Law", 0.5), _make_match("Non-Compete", 0.9)]

    flagged = apply_risk_flags(matches)

    assert [m.category for m in flagged] == ["Governing Law", "Non-Compete"]


def test_summarize_risk_reports_highest_level_present() -> None:
    matches = apply_risk_flags([_make_match("Governing Law", 0.9), _make_match("Uncapped Liability", 0.9)])

    summary = summarize_risk(matches)

    assert summary.highest_risk_level == "HIGH"


def test_summarize_risk_counts_each_level() -> None:
    matches = apply_risk_flags(
        [
            _make_match("Uncapped Liability", 0.9),
            _make_match("Non-Compete", 0.9),
            _make_match("Governing Law", 0.9),
        ]
    )

    summary = summarize_risk(matches)

    assert summary.counts_by_level == {"HIGH": 1, "MEDIUM": 1, "INFORMATIONAL": 1}


def test_summarize_risk_handles_empty_clause_list() -> None:
    summary = summarize_risk([])

    assert summary.highest_risk_level is None
    assert summary.counts_by_level == {"HIGH": 0, "MEDIUM": 0, "INFORMATIONAL": 0}
