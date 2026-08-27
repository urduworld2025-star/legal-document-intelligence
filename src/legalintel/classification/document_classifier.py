from functools import lru_cache
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from legalintel.models.document import DocumentClassification

# Must match the values used in notebooks/03_document_classification_colab.ipynb
# so inference matches how the model was trained.
MAX_LENGTH = 512


class ModelNotFoundError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _load_model(model_dir: str):
    path = Path(model_dir)
    if not path.exists():
        raise ModelNotFoundError(
            f"No trained model found at '{model_dir}'. Train it in "
            "notebooks/03_document_classification_colab.ipynb (Google Colab) "
            "and unzip the downloaded document_classification_model.zip into that folder."
        )
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    model.eval()
    return tokenizer, model


def classify_document(
    text: str, model_dir: str = "models/document-classification-baseline"
) -> DocumentClassification:
    """Run the trained 3-class model against `text` and return the predicted type plus
    the full probability distribution (for human-in-the-loop transparency, not just
    the top guess)."""
    tokenizer, model = _load_model(model_dir)

    inputs = tokenizer(text, max_length=MAX_LENGTH, truncation=True, return_tensors="pt")

    with torch.no_grad():
        outputs = model(**inputs)

    probs = torch.softmax(outputs.logits, dim=-1)[0]
    predicted_id = int(torch.argmax(probs).item())
    predicted_label = model.config.id2label[predicted_id]
    probabilities = {model.config.id2label[i]: probs[i].item() for i in range(probs.shape[0])}

    return DocumentClassification(
        predicted_type=predicted_label,
        confidence=probabilities[predicted_label],
        probabilities=probabilities,
    )
