from pathlib import Path

import pytest

from legalintel.extraction.clause_extractor import QUESTIONS, ModelNotFoundError, extract_clauses

SHORT_CONTEXT = (
    "This Agreement shall be governed by and construed in accordance with the laws "
    "of the State of Delaware, without regard to its conflict of laws principles. "
    "Either party may terminate this Agreement for convenience upon 30 days notice. "
    "Neither party shall be liable for any indirect damages under any circumstances. "
    "Employee agrees not to compete with the Company for a period of 12 months."
)


def test_missing_model_dir_raises_clear_error(tmp_path: Path) -> None:
    missing_dir = tmp_path / "does-not-exist"

    with pytest.raises(ModelNotFoundError):
        extract_clauses(SHORT_CONTEXT, model_dir=str(missing_dir))


def test_extract_clauses_returns_well_formed_matches(stub_model_dir: Path) -> None:
    matches = extract_clauses(SHORT_CONTEXT, model_dir=str(stub_model_dir))

    assert isinstance(matches, list)
    for match in matches:
        assert match.category in QUESTIONS
        assert isinstance(match.text, str)
        assert 0.0 <= match.confidence <= 1.0
        if match.char_start is not None and match.char_end is not None:
            assert 0 <= match.char_start <= match.char_end <= len(SHORT_CONTEXT)


def test_extract_clauses_handles_long_multi_window_text(stub_model_dir: Path) -> None:
    long_context = (SHORT_CONTEXT + " ") * 60  # forces multiple sliding-window chunks

    matches = extract_clauses(long_context, model_dir=str(stub_model_dir))

    assert isinstance(matches, list)
    for match in matches:
        assert 0.0 <= match.confidence <= 1.0
