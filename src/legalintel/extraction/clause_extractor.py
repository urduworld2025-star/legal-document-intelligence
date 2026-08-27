import re
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

# The null-vs-span decision is `best_margin > threshold` (default 0.0 = trust the model's
# own calibration). scripts/eval_models.py's step-9 QA pass found Uncapped Liability and
# Non-Compete have strong no-answer accuracy (~100%) but weak has-answer recall (20-30%) -
# i.e. the model is too conservative and defaults to "no clause found" on real positives far
# too often for these two categories specifically. Lowering their threshold (accepting a
# span even when it scores somewhat below the null answer) trades some precision for a lot
# of recall - tuned empirically via `python -m scripts.eval_models --calibrate` (results in
# docs/threshold-calibration-report.md), not guessed:
#   - Uncapped Liability -8.0: recall 27%->73% with EM/F1 *improving* (0.60/0.62->0.63/0.74)
#     and no-answer accuracy staying at 1.00 - a clean win, no real tradeoff at this point.
#   - Non-Compete -6.0: recall 29%->64%, EM 0.62->0.69, F1 0.63->0.73, no-answer accuracy
#     dips slightly 1.00->0.93 (a real but small precision cost, worth it for the recall gain).
# Governing Law and Termination For Convenience are not in this dict (threshold stays 0.0,
# unchanged) since their recall was already good.
NULL_MARGIN_THRESHOLD: dict[str, float] = {
    "Uncapped Liability": -8.0,
    "Non-Compete": -6.0,
}

# Heuristic, not a model - flags when a matched span is immediately preceded by negation
# language (e.g. "Neither Party may terminate ... for convenience") so a reviewer knows to
# double-check the clause isn't the inverse of what the category name suggests. This catches
# a real failure mode found during step-9 QA (see docs/model-eval-report.md): the model can
# match on surface phrasing alone without registering the negation. Imperfect by design -
# a false negative here just means no warning shown (same as today); a false positive just
# means an extra "double-check this" note on a clause that was fine. Never used to suppress
# a match outright, since suppressing on a heuristic could hide a genuine clause.
_NEGATION_CUES = re.compile(
    r"\b(shall not|may not|will not|is not permitted|are not permitted|"
    r"not (?:be )?(?:permitted|entitled|allowed) to|prohibited from|"
    r"no party (?:shall|may|will)|neither party (?:shall|may|will))\b",
    re.IGNORECASE,
)
_NEGATION_LOOKBACK_CHARS = 120


def _looks_negated(context: str, char_start: int | None, char_end: int | None = None) -> bool:
    """Checks both the text immediately before the span (negation governing a span that
    starts after it, e.g. "...shall not [terminate...]") and the start of the span itself
    (negation the model swept into its own answer, e.g. "[Neither Party may terminate...]"
    - the actual shape of the real false positive this heuristic was added for)."""
    if char_start is None:
        return False
    window_start = max(0, char_start - _NEGATION_LOOKBACK_CHARS)
    span_head_end = char_start + 40 if char_end is None else min(char_end, char_start + 40)
    return bool(_NEGATION_CUES.search(context[window_start:span_head_end]))


class ModelNotFoundError(RuntimeError):
    pass


_HUB_REPO_ID_RE = re.compile(r"^[\w.-]+/[\w.-]+$")


def _looks_like_hub_repo_id(model_dir: str) -> bool:
    """True for strings shaped like 'namespace/repo-name' - deliberately excludes anything
    with a backslash or drive letter (Windows local paths) so a missing local folder still
    fails fast offline in tests/dev instead of attempting a real Hub network call."""
    return bool(_HUB_REPO_ID_RE.match(model_dir)) and "\\" not in model_dir


@lru_cache(maxsize=1)
def _load_model(model_dir: str):
    # A local folder (dev machine, unzipped from Colab) is checked first so the existing
    # fail-fast behavior/message is unchanged for local use. If it's not a local folder but
    # looks like a Hugging Face Hub repo id, fall through and let from_pretrained try
    # fetching it from the Hub (e.g. CLAUSE_MODEL_DIR=yourname/clause-extraction-baseline in
    # production, where the 250MB+ checkpoint can't be committed to git) - any failure there
    # is wrapped in the same ModelNotFoundError so callers don't need to know which case
    # applies.
    if not Path(model_dir).exists():
        if not _looks_like_hub_repo_id(model_dir):
            raise ModelNotFoundError(
                f"No trained model found at '{model_dir}'. Train it in "
                "notebooks/02_baseline_clause_extraction_colab.ipynb (Google Colab) and "
                "unzip the downloaded clause_extraction_model.zip into that folder, or set "
                "CLAUSE_MODEL_DIR to a Hugging Face Hub repo id "
                "(e.g. 'yourname/clause-extraction-baseline')."
            )
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_dir)
            model = AutoModelForQuestionAnswering.from_pretrained(model_dir)
            model.eval()
            return tokenizer, model
        except Exception as exc:
            raise ModelNotFoundError(
                f"Could not load a model from the Hugging Face Hub repo '{model_dir}'. "
                f"Underlying error: {exc}"
            ) from exc

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


def _score_span(question: str, context: str, tokenizer, model) -> tuple[float, int | None, int | None, float]:
    """Run sliding-window QA inference and return the best (margin, char_start, char_end,
    confidence) found across all windows, regardless of whether that margin clears any
    null-vs-span threshold - that decision is the caller's (`_predict_answer`), kept
    separate so a threshold can be swept post-hoc without re-running inference (see
    `scripts/eval_models.py --calibrate`)."""
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

    if best_margin is None:
        return float("-inf"), None, None, 0.0

    confidence = torch.sigmoid(torch.tensor(best_margin)).item()
    return best_margin, best_char_start, best_char_end, confidence


def _predict_answer(
    question: str, context: str, tokenizer, model, *, margin_threshold: float = 0.0
) -> ClauseMatch | None:
    """Score `question` against `context` and return the best answer span, or None if it
    doesn't clear `margin_threshold` above the model's own null-answer score (SQuAD
    2.0-style null-vs-span comparison; see `NULL_MARGIN_THRESHOLD` for why this is
    per-category rather than a single global 0.0)."""
    margin, char_start, char_end, confidence = _score_span(question, context, tokenizer, model)
    if char_start is None or margin <= margin_threshold:
        return None

    return ClauseMatch(
        category="",
        text=context[char_start:char_end],
        confidence=confidence,
        char_start=char_start,
        char_end=char_end,
    )


def extract_clauses(text: str, model_dir: str = "models/clause-extraction-baseline") -> list[ClauseMatch]:
    """Run the trained model against `text` for each of the 4 clause categories.
    Only returns categories where the model found a clause (skips "no answer" cases)."""
    tokenizer, model = _load_model(model_dir)

    matches = []
    for category, question in QUESTIONS.items():
        threshold = NULL_MARGIN_THRESHOLD.get(category, 0.0)
        match = _predict_answer(question, text, tokenizer, model, margin_threshold=threshold)
        if match is not None:
            match.category = category
            match.possible_negation = _looks_negated(text, match.char_start, match.char_end)
            matches.append(match)

    return matches
