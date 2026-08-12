from pathlib import Path

import pytest
from transformers import AutoModelForQuestionAnswering, AutoTokenizer

BASE_CHECKPOINT = "distilbert-base-uncased"


@pytest.fixture(scope="session")
def stub_model_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A QA model directory with an untrained head, used to test extraction
    mechanics (windowing, scoring, decoding) without needing a real trained
    checkpoint. Predictions from this model are meaningless noise - only the
    code path is under test here, not extraction accuracy."""
    path = tmp_path_factory.mktemp("stub_model")
    tokenizer = AutoTokenizer.from_pretrained(BASE_CHECKPOINT)
    model = AutoModelForQuestionAnswering.from_pretrained(BASE_CHECKPOINT)
    tokenizer.save_pretrained(path)
    model.save_pretrained(path)
    return path
