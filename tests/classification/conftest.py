from pathlib import Path

import pytest
from transformers import AutoModelForSequenceClassification, AutoTokenizer

BASE_CHECKPOINT = "distilbert-base-uncased"
ID2LABEL = {0: "Contract", 1: "Email", 2: "Other"}
LABEL2ID = {v: k for k, v in ID2LABEL.items()}


@pytest.fixture(scope="session")
def stub_classifier_model_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A sequence-classification model directory with an untrained head, used to test
    classification mechanics (tokenization, softmax, label mapping) without needing a
    real trained checkpoint. Predictions from this model are meaningless noise - only
    the code path is under test here, not classification accuracy."""
    path = tmp_path_factory.mktemp("stub_classifier_model")
    tokenizer = AutoTokenizer.from_pretrained(BASE_CHECKPOINT)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_CHECKPOINT, num_labels=3, id2label=ID2LABEL, label2id=LABEL2ID
    )
    tokenizer.save_pretrained(path)
    model.save_pretrained(path)
    return path
