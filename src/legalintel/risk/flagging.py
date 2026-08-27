from legalintel.models.document import ClauseMatch, ConfidenceBand, RiskLevel, RiskSummary

# category strings must match legalintel.extraction.clause_extractor.QUESTIONS exactly.
SEVERITY_BY_CATEGORY: dict[str, RiskLevel] = {
    "Uncapped Liability": "HIGH",
    "Non-Compete": "MEDIUM",
    "Termination For Convenience": "MEDIUM",
    "Governing Law": "INFORMATIONAL",
}

_SEVERITY_ORDER: list[RiskLevel] = ["HIGH", "MEDIUM", "INFORMATIONAL"]

# `confidence` is a sigmoid of a span-vs-null-answer logit margin, not a
# calibrated probability, so these bands exist for reviewer legibility
# rather than any statistically "correct" cutoff.
CONFIDENCE_BAND_HIGH = 0.75
CONFIDENCE_BAND_MEDIUM = 0.40


def risk_level_for_category(category: str) -> RiskLevel:
    return SEVERITY_BY_CATEGORY.get(category, "INFORMATIONAL")


def band_for_confidence(confidence: float) -> ConfidenceBand:
    if confidence >= CONFIDENCE_BAND_HIGH:
        return "HIGH"
    if confidence >= CONFIDENCE_BAND_MEDIUM:
        return "MEDIUM"
    return "LOW"


def apply_risk_flags(clauses: list[ClauseMatch]) -> list[ClauseMatch]:
    return [
        clause.model_copy(
            update={
                "risk_level": risk_level_for_category(clause.category),
                "confidence_band": band_for_confidence(clause.confidence),
            }
        )
        for clause in clauses
    ]


def summarize_risk(clauses: list[ClauseMatch]) -> RiskSummary:
    counts_by_level: dict[RiskLevel, int] = {level: 0 for level in _SEVERITY_ORDER}
    for clause in clauses:
        level = clause.risk_level or risk_level_for_category(clause.category)
        counts_by_level[level] += 1

    highest_risk_level = next((level for level in _SEVERITY_ORDER if counts_by_level[level] > 0), None)

    return RiskSummary(highest_risk_level=highest_risk_level, counts_by_level=counts_by_level)
