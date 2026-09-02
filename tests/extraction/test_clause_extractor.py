from pathlib import Path

import pytest

from legalintel.extraction.clause_extractor import (
    QUESTIONS,
    ModelNotFoundError,
    _looks_like_hub_repo_id,
    _looks_negated,
    extract_clauses,
)

SHORT_CONTEXT = (
    "This Agreement shall be governed by and construed in accordance with the laws "
    "of the State of Delaware, without regard to its conflict of laws principles. "
    "Either party may terminate this Agreement for convenience upon 30 days notice. "
    "Neither party shall be liable for any indirect damages under any circumstances. "
    "Employee agrees not to compete with the Company for a period of 12 months."
)


def test_looks_like_hub_repo_id_accepts_namespace_slash_name() -> None:
    assert _looks_like_hub_repo_id("yourname/clause-extraction-baseline") is True


def test_looks_like_hub_repo_id_rejects_windows_local_paths() -> None:
    assert _looks_like_hub_repo_id(r"C:\Users\pcs\models\clause-extraction-baseline") is False
    assert _looks_like_hub_repo_id("models/clause-extraction-baseline") is True  # unix-style relative path


def test_missing_model_dir_with_windows_path_fails_fast_without_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A Windows absolute path that doesn't exist must never fall through to a Hub lookup -
    # regression test for the fix that made the local-vs-Hub Path.exists() check offline-safe.
    def _fail_if_called(*args, **kwargs):
        raise AssertionError("from_pretrained should not be called for a local-looking path")

    # clause_extractor imports transformers locally (inside _load_model), not at module
    # level - see the module docstring note on why - so patch the source classes directly;
    # the local `from transformers import ...` inside _load_model resolves to the same
    # (now-patched) class objects.
    import transformers

    monkeypatch.setattr(transformers.AutoTokenizer, "from_pretrained", _fail_if_called)
    monkeypatch.setattr(transformers.AutoModelForQuestionAnswering, "from_pretrained", _fail_if_called)

    with pytest.raises(ModelNotFoundError):
        extract_clauses(SHORT_CONTEXT, model_dir=str(tmp_path / "does-not-exist"))


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
        assert isinstance(match.possible_negation, bool)
        if match.char_start is not None and match.char_end is not None:
            assert 0 <= match.char_start <= match.char_end <= len(SHORT_CONTEXT)


def test_extract_clauses_handles_long_multi_window_text(stub_model_dir: Path) -> None:
    long_context = (SHORT_CONTEXT + " ") * 60  # forces multiple sliding-window chunks

    matches = extract_clauses(long_context, model_dir=str(stub_model_dir))

    assert isinstance(matches, list)
    for match in matches:
        assert 0.0 <= match.confidence <= 1.0


def test_looks_negated_true_for_prohibition_immediately_before_span() -> None:
    context = (
        "Neither Party may terminate this Agreement for convenience prior to the "
        "expiration of the Term."
    )
    char_start = context.index("prior to")

    assert _looks_negated(context, char_start) is True


def test_looks_negated_false_for_affirmative_clause() -> None:
    context = "Either Party may terminate this Agreement for convenience upon 30 days notice."
    char_start = context.index("for convenience")

    assert _looks_negated(context, char_start) is False


def test_looks_negated_true_when_negation_is_inside_the_matched_span() -> None:
    # Regression test: the model can sweep the negation word itself into the extracted
    # span (e.g. "[Neither Party may terminate...]" as one answer) rather than always
    # leaving it in the preceding text - the lookback-only version of this heuristic
    # missed this exact shape of false positive.
    context = (
        "Some preamble text. Neither Party may terminate this Agreement for convenience "
        "prior to expiration."
    )
    char_start = context.index("Neither Party may")
    char_end = char_start + len("Neither Party may terminate this Agreement for convenience")

    assert _looks_negated(context, char_start, char_end) is True


def test_looks_negated_false_when_char_start_is_none() -> None:
    assert _looks_negated("Neither Party shall terminate this Agreement.", None) is False


def test_looks_negated_ignores_negation_outside_lookback_window() -> None:
    filler = "x" * 200
    context = f"Neither Party shall be bound by that. {filler} for convenience"
    char_start = context.index("for convenience")

    assert _looks_negated(context, char_start) is False
