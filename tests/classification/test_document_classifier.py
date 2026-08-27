from pathlib import Path

import pytest

from legalintel.classification.document_classifier import ModelNotFoundError, classify_document

SAMPLE_TEXT = (
    "This Agreement is entered into by and between the parties for the purposes "
    "set forth below, subject to the terms and conditions herein."
)


def test_missing_model_dir_raises_clear_error(tmp_path: Path) -> None:
    missing_dir = tmp_path / "does-not-exist"
    with pytest.raises(ModelNotFoundError):
        classify_document(SAMPLE_TEXT, model_dir=str(missing_dir))


def test_classify_document_returns_well_formed_result(stub_classifier_model_dir: Path) -> None:
    result = classify_document(SAMPLE_TEXT, model_dir=str(stub_classifier_model_dir))

    assert result.predicted_type in {"Contract", "Email", "Other"}
    assert 0.0 <= result.confidence <= 1.0
    assert set(result.probabilities.keys()) == {"Contract", "Email", "Other"}
    assert result.probabilities[result.predicted_type] == pytest.approx(result.confidence)
    assert sum(result.probabilities.values()) == pytest.approx(1.0, abs=1e-4)
