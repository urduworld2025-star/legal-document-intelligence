import re
from functools import lru_cache
from pathlib import Path

from legalintel.models.document import DocumentClassification

# torch/transformers are deliberately NOT imported at module level - see the same note in
# clause_extractor.py. Each function that needs them imports locally instead, so merely
# importing this module (e.g. transitively via app.main at process startup) doesn't pay
# torch's slow import cost.

# Must match the values used in notebooks/03_document_classification_colab.ipynb
# so inference matches how the model was trained.
MAX_LENGTH = 512

_HUB_REPO_ID_RE = re.compile(r"^[\w.-]+/[\w.-]+$")


def _looks_like_hub_repo_id(model_dir: str) -> bool:
    """True for strings shaped like 'namespace/repo-name' - deliberately excludes anything
    with a backslash or drive letter (Windows local paths) so a missing local folder still
    fails fast offline in tests/dev instead of attempting a real Hub network call."""
    return bool(_HUB_REPO_ID_RE.match(model_dir)) and "\\" not in model_dir


class ModelNotFoundError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _load_model(model_dir: str):
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    # A local folder (dev machine, unzipped from Colab) is checked first so the existing
    # fail-fast behavior/message is unchanged for local use. If it's not a local folder but
    # looks like a Hugging Face Hub repo id, fall through and let from_pretrained try
    # fetching it from the Hub (e.g. DOCUMENT_CLASSIFICATION_MODEL_DIR=yourname/document-
    # classification-baseline in production, where the 250MB+ checkpoint can't be committed
    # to git) - any failure there is wrapped in the same ModelNotFoundError.
    if not Path(model_dir).exists():
        if not _looks_like_hub_repo_id(model_dir):
            raise ModelNotFoundError(
                f"No trained model found at '{model_dir}'. Train it in "
                "notebooks/03_document_classification_colab.ipynb (Google Colab) and unzip "
                "the downloaded document_classification_model.zip into that folder, or set "
                "DOCUMENT_CLASSIFICATION_MODEL_DIR to a Hugging Face Hub repo id "
                "(e.g. 'yourname/document-classification-baseline')."
            )
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_dir)
            model = AutoModelForSequenceClassification.from_pretrained(model_dir)
            model.eval()
            return tokenizer, model
        except Exception as exc:
            raise ModelNotFoundError(
                f"Could not load a model from the Hugging Face Hub repo '{model_dir}'. "
                f"Underlying error: {exc}"
            ) from exc

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
    import torch

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
