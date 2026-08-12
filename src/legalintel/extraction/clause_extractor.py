from functools import lru_cache
from pathlib import Path

import torch
from transformers import AutoModelForQuestionAnswering, AutoTokenizer

from legalintel.models.document import ClauseMatch

# Must match the values used in notebooks/02_baseline_clause_extraction_colab.ipynb
# so inference windowing matches how the model was trained.
MAX_LENGTH = 384
STRIDE = 128
MAX_ANSWER_TOKENS = 100

# Exact question wording used for each category during training (pulled directly
# from CUAD_v1.json) - QA models are sensitive to question phrasing, so inference
# must ask the same question the model was trained on.
QUESTIONS: dict[str, str] = {
    "Governing Law": (
        'Highlight the parts (if any) of this contract related to "Governing Law" '
        "that should be reviewed by a lawyer. Details: Which state/country's law "
        "governs the interpretation of the contract?"
    ),
    "Termination For Convenience": (
        'Highlight the parts (if any) of this contract related to "Termination For '
        'Convenience" that should be reviewed by a lawyer. Details: Can a party '
        "terminate this  contract without cause (solely by giving a notice and "
        "allowing a waiting  period to expire)?"
    ),
    "Uncapped Liability": (
        'Highlight the parts (if any) of this contract related to "Uncapped '
        'Liability" that should be reviewed by a lawyer. Details: Is a party’s '
        "liability uncapped upon the breach of its obligation in the contract? "
        "This also includes uncap liability for a particular type of breach such "
        "as IP infringement or breach of confidentiality obligation."
    ),
    "Non-Compete": (
        'Highlight the parts (if any) of this contract related to "Non-Compete" '
        "that should be reviewed by a lawyer. Details: Is there a restriction on "
        "the ability of a party to compete with the counterparty or operate in a "
        "certain geography or business or technology sector? "
    ),
}


class ModelNotFoundError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _load_model(model_dir: str):
    path = Path(model_dir)
    if not path.exists():
        raise ModelNotFoundError(
            f"No trained model found at '{model_dir}'. Train it in "
            "notebooks/02_baseline_clause_extraction_colab.ipynb (Google Colab) "
            "and unzip the downloaded clause_extraction_model.zip into that folder."
        )
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForQuestionAnswering.from_pretrained(model_dir)
    model.eval()
    return tokenizer, model


def _best_span_in_window(start_logits: torch.Tensor, end_logits: torch.Tensor, ctx_start: int, ctx_end: int):
    """Find the highest-scoring valid (start, end) span within [ctx_start, ctx_end], vectorized."""
    start_ctx = start_logits[ctx_start : ctx_end + 1]
    end_ctx = end_logits[ctx_start : ctx_end + 1]
    length = start_ctx.shape[0]

    scores = start_ctx.unsqueeze(1) + end_ctx.unsqueeze(0)  # scores[i, j] = start_i + end_j

    idx = torch.arange(length)
    start_grid = idx.unsqueeze(1).expand(length, length)
    end_grid = idx.unsqueeze(0).expand(length, length)
    valid = (end_grid >= start_grid) & (end_grid - start_grid < MAX_ANSWER_TOKENS)
    scores = scores.masked_fill(~valid, float("-inf"))

    best_flat = torch.argmax(scores)
    best_start_rel = (best_flat // length).item()
    best_end_rel = (best_flat % length).item()
    best_score = scores[best_start_rel, best_end_rel].item()

    return ctx_start + best_start_rel, ctx_start + best_end_rel, best_score


def _predict_answer(question: str, context: str, tokenizer, model) -> ClauseMatch | None:
    """Run sliding-window QA inference and return the best answer span, or None if the
    model is more confident there's no answer (SQuAD 2.0-style null-vs-span comparison)."""
    inputs = tokenizer(
        question,
        context,
        max_length=MAX_LENGTH,
        truncation="only_second",
        stride=STRIDE,
        return_overflowing_tokens=True,
        return_offsets_mapping=True,
        padding="max_length",
        return_tensors="pt",
    )
    offset_mapping = inputs.pop("offset_mapping")
    inputs.pop("overflow_to_sample_mapping")

    with torch.no_grad():
        outputs = model(**inputs)

    best_margin = None
    best_char_start = None
    best_char_end = None

    num_windows = inputs["input_ids"].shape[0]
    for window_idx in range(num_windows):
        sequence_ids = inputs.sequence_ids(window_idx)
        start_logits = outputs.start_logits[window_idx]
        end_logits = outputs.end_logits[window_idx]
        offsets = offset_mapping[window_idx]

        null_score = (start_logits[0] + end_logits[0]).item()

        context_token_indices = [i for i, seq_id in enumerate(sequence_ids) if seq_id == 1]
        if not context_token_indices:
            continue
        ctx_start, ctx_end = context_token_indices[0], context_token_indices[-1]

        start_idx, end_idx, span_score = _best_span_in_window(start_logits, end_logits, ctx_start, ctx_end)
        margin = span_score - null_score

        if best_margin is None or margin > best_margin:
            best_margin = margin
            best_char_start = offsets[start_idx][0].item()
            best_char_end = offsets[end_idx][1].item()

    if best_margin is None or best_margin <= 0:
        return None

    confidence = torch.sigmoid(torch.tensor(best_margin)).item()
    answer_text = context[best_char_start:best_char_end]

    return ClauseMatch(
        category="",
        text=answer_text,
        confidence=confidence,
        char_start=best_char_start,
        char_end=best_char_end,
    )


def extract_clauses(text: str, model_dir: str = "models/clause-extraction-baseline") -> list[ClauseMatch]:
    """Run the trained model against `text` for each of the 4 clause categories.
    Only returns categories where the model found a clause (skips "no answer" cases)."""
    tokenizer, model = _load_model(model_dir)

    matches = []
    for category, question in QUESTIONS.items():
        match = _predict_answer(question, text, tokenizer, model)
        if match is not None:
            match.category = category
            matches.append(match)

    return matches
