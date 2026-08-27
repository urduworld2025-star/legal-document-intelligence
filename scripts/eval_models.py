"""Evaluates the two trained models (clause extraction, document classification)
against validation data reconstructed with the exact same filtering/sampling/split
logic as their training notebooks (notebooks/02_.../03_...). This is build-order step
9 ("Testing & QA against legal-domain review") — the thing the unit test suite
deliberately doesn't check, since tests use an untrained-head stub model to exercise
code paths without asserting on prediction quality.

IMPORTANT CAVEAT: the validation split reconstructed here is the SAME split each
notebook passed as `eval_dataset` to its Trainer (eval_strategy="epoch",
load_best_model_at_end=True / metric_for_best_model="f1") — i.e. the checkpoint that
got downloaded and deployed was already selected based on performance on these exact
rows. Read the numbers below as "best-checkpoint validation performance," not as an
unseen generalization estimate. A true held-out test set would require re-running the
notebooks with a 3-way split before training, which hasn't been done.

Runs entirely on CPU (this machine has no GPU) - inference only, consistent with the
hardware constraint in CLAUDE.md. Clause-extraction eval is the slow part (sliding-window
QA over full contract text, ~10-30s per example on this hardware) so it's capped to a
stratified sample per category by default; document classification is a single forward
pass per example and runs the full validation split.

Requires the `datasets` package (not a runtime dependency of the app itself - only
needed here and in the Colab notebooks): pip install datasets

Usage:
    python -m scripts.eval_models
    python -m scripts.eval_models --only clauses
    python -m scripts.eval_models --only classification
    python -m scripts.eval_models --sample-per-category 30
"""

import argparse
import json
import random
import re
import string
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from huggingface_hub import hf_hub_download

from legalintel.classification import document_classifier as dc
from legalintel.extraction import clause_extractor as ce

SEED = 42
CLAUSE_CATEGORIES = ["Governing Law", "Termination For Convenience", "Uncapped Liability", "Non-Compete"]
CLASSIFICATION_PER_CLASS_CAP = 500
REPORT_PATH = Path(__file__).resolve().parent.parent / "docs" / "model-eval-report.md"


# ---------------------------------------------------------------------------
# Shared SQuAD-style text normalization / F1, used for clause-extraction eval
# ---------------------------------------------------------------------------

def _normalize_answer(text: str) -> str:
    text = text.lower()
    text = "".join(ch for ch in text if ch not in set(string.punctuation))
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    return " ".join(text.split())


def _token_f1(prediction: str, ground_truth: str) -> float:
    pred_tokens = _normalize_answer(prediction).split()
    gold_tokens = _normalize_answer(ground_truth).split()
    if len(pred_tokens) == 0 or len(gold_tokens) == 0:
        return float(pred_tokens == gold_tokens)
    common = Counter(pred_tokens) & Counter(gold_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return 0.0
    precision = num_same / len(pred_tokens)
    recall = num_same / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


def _best_over_golds(prediction: str, gold_texts: list[str], metric_fn) -> float:
    return max((metric_fn(prediction, g) for g in gold_texts), default=0.0)


# ---------------------------------------------------------------------------
# Clause extraction eval
# ---------------------------------------------------------------------------

def _load_cuad_records() -> list[dict]:
    cuad_json_path = hf_hub_download(
        repo_id="theatticusproject/cuad", repo_type="dataset", filename="CUAD_v1/CUAD_v1.json"
    )
    with open(cuad_json_path, encoding="utf-8") as f:
        cuad_raw = json.load(f)

    all_records = []
    for document in cuad_raw["data"]:
        for paragraph in document["paragraphs"]:
            context = paragraph["context"]
            for qa in paragraph["qas"]:
                all_records.append({"question": qa["question"], "context": context, "answers": qa["answers"]})
    return all_records


def _matched_category(question: str) -> str | None:
    return next((c for c in CLAUSE_CATEGORIES if f'"{c}"' in question), None)


def _cuad_validation_split() -> list[dict]:
    from datasets import Dataset

    all_records = _load_cuad_records()
    filtered = []
    for record in all_records:
        category = _matched_category(record["question"])
        if category is not None:
            filtered.append({**record, "category": category})

    dataset = Dataset.from_list(filtered)
    split = dataset.train_test_split(test_size=0.15, seed=SEED)
    return list(split["test"])


def _stratified_sample(val_rows: list[dict], per_category: int) -> list[dict]:
    rng = random.Random(SEED)
    sampled = []
    for category in CLAUSE_CATEGORIES:
        rows = [r for r in val_rows if r["category"] == category]
        has_ans = [r for r in rows if len(r["answers"]) > 0]
        no_ans = [r for r in rows if len(r["answers"]) == 0]
        # Aim for a roughly even has-answer / no-answer mix so null-detection is tested too.
        half = per_category // 2
        picked = rng.sample(has_ans, min(half, len(has_ans))) + rng.sample(
            no_ans, min(per_category - half, len(no_ans))
        )
        sampled.extend(picked)
    return sampled


def eval_clause_extraction(sample_per_category: int) -> list[str]:
    lines = ["## Clause Extraction", ""]
    print("\n=== Clause Extraction ===")

    print("Loading CUAD and reconstructing the validation split (same filtering/seed as notebook 02)...")
    val_rows = _cuad_validation_split()
    sample = _stratified_sample(val_rows, sample_per_category)
    print(f"Evaluating {len(sample)} rows ({sample_per_category} target per category, has/no-answer mixed)...")

    tokenizer, model = ce._load_model("models/clause-extraction-baseline")

    by_category: dict[str, list[dict]] = {c: [] for c in CLAUSE_CATEGORIES}
    t_start = time.time()
    for i, row in enumerate(sample, 1):
        threshold = ce.NULL_MARGIN_THRESHOLD.get(row["category"], 0.0)
        prediction = ce._predict_answer(
            row["question"], row["context"], tokenizer, model, margin_threshold=threshold
        )
        gold_texts = [a["text"] for a in row["answers"]]
        is_no_answer_gold = len(gold_texts) == 0

        if prediction is None:
            em = f1 = 1.0 if is_no_answer_gold else 0.0
        elif is_no_answer_gold:
            em = f1 = 0.0
        else:
            em = 1.0 if any(_normalize_answer(prediction.text) == _normalize_answer(g) for g in gold_texts) else 0.0
            f1 = _best_over_golds(prediction.text, gold_texts, _token_f1)

        by_category[row["category"]].append(
            {"gold_no_answer": is_no_answer_gold, "predicted_no_answer": prediction is None, "em": em, "f1": f1}
        )
        elapsed = time.time() - t_start
        print(f"  [{i}/{len(sample)}] {row['category']:<28} elapsed={elapsed:6.1f}s", end="\r")

    print()
    lines.append(
        "Validation rows are the same split used for best-checkpoint selection during training "
        "(see caveat in the script docstring) — read as best-checkpoint validation performance, "
        "not a held-out generalization estimate.\n"
    )
    lines.append("| Category | N | EM | F1 | No-Answer Accuracy | Has-Answer Recall |")
    lines.append("|---|---|---|---|---|---|")

    all_em, all_f1 = [], []
    for category in CLAUSE_CATEGORIES:
        rows = by_category[category]
        if not rows:
            continue
        em_avg = sum(r["em"] for r in rows) / len(rows)
        f1_avg = sum(r["f1"] for r in rows) / len(rows)
        all_em += [r["em"] for r in rows]
        all_f1 += [r["f1"] for r in rows]

        no_ans_rows = [r for r in rows if r["gold_no_answer"]]
        no_ans_acc = (
            sum(1 for r in no_ans_rows if r["predicted_no_answer"]) / len(no_ans_rows) if no_ans_rows else float("nan")
        )
        has_ans_rows = [r for r in rows if not r["gold_no_answer"]]
        has_ans_recall = (
            sum(1 for r in has_ans_rows if not r["predicted_no_answer"]) / len(has_ans_rows)
            if has_ans_rows
            else float("nan")
        )

        row_line = (
            f"| {category} | {len(rows)} | {em_avg:.2f} | {f1_avg:.2f} | "
            f"{no_ans_acc:.2f} ({len(no_ans_rows)}) | {has_ans_recall:.2f} ({len(has_ans_rows)}) |"
        )
        lines.append(row_line)
        print(row_line.replace("|", " ").strip())

    overall_em = sum(all_em) / len(all_em) if all_em else float("nan")
    overall_f1 = sum(all_f1) / len(all_f1) if all_f1 else float("nan")
    lines.append(f"| **Overall** | {len(all_em)} | {overall_em:.2f} | {overall_f1:.2f} | — | — |")
    lines.append("")
    print(f"Overall: EM={overall_em:.2f} F1={overall_f1:.2f} over {len(all_em)} rows")
    return lines


# ---------------------------------------------------------------------------
# Threshold calibration - runs inference ONCE per row (via _score_span, which
# doesn't itself apply a null-vs-span decision), then sweeps a grid of
# candidate thresholds cheaply against the cached margins. Used to pick
# NULL_MARGIN_THRESHOLD values in clause_extractor.py data-driven rather than
# by guessing.
# ---------------------------------------------------------------------------

DEFAULT_CALIBRATE_GRID = [0.0, -1.0, -2.0, -3.0, -4.0, -5.0, -6.0, -8.0, -10.0]


def calibrate_thresholds(categories: list[str], sample_per_category: int, grid: list[float]) -> list[str]:
    lines = ["## Threshold Calibration", ""]
    print("\n=== Threshold Calibration ===")

    print("Loading CUAD and reconstructing the validation split...")
    val_rows = _cuad_validation_split()
    sample = _stratified_sample([r for r in val_rows if r["category"] in categories], sample_per_category)
    print(f"Scoring {len(sample)} rows once each (inference is threshold-independent)...")

    tokenizer, model = ce._load_model("models/clause-extraction-baseline")

    scored = []
    t_start = time.time()
    for i, row in enumerate(sample, 1):
        margin, char_start, char_end, _ = ce._score_span(row["question"], row["context"], tokenizer, model)
        gold_texts = [a["text"] for a in row["answers"]]
        scored.append(
            {
                "category": row["category"],
                "margin": margin,
                "char_start": char_start,
                "char_end": char_end,
                "context": row["context"],
                "gold_texts": gold_texts,
                "is_no_answer_gold": len(gold_texts) == 0,
            }
        )
        print(f"  [{i}/{len(sample)}] elapsed={time.time() - t_start:6.1f}s", end="\r")
    print()

    for category in categories:
        rows = [r for r in scored if r["category"] == category]
        if not rows:
            continue
        lines.append(f"### {category}")
        lines.append("")
        lines.append("| Threshold | EM | F1 | No-Answer Accuracy | Has-Answer Recall |")
        lines.append("|---|---|---|---|---|")
        for threshold in grid:
            ems, f1s = [], []
            no_ans_rows = [r for r in rows if r["is_no_answer_gold"]]
            has_ans_rows = [r for r in rows if not r["is_no_answer_gold"]]
            no_ans_correct = sum(1 for r in no_ans_rows if r["margin"] <= threshold)
            has_ans_correct = sum(1 for r in has_ans_rows if r["margin"] > threshold)

            for r in rows:
                accepted = r["margin"] > threshold
                if not accepted:
                    em = f1 = 1.0 if r["is_no_answer_gold"] else 0.0
                elif r["is_no_answer_gold"]:
                    em = f1 = 0.0
                else:
                    predicted_text = r["context"][r["char_start"] : r["char_end"]]
                    em = 1.0 if any(
                        _normalize_answer(predicted_text) == _normalize_answer(g) for g in r["gold_texts"]
                    ) else 0.0
                    f1 = _best_over_golds(predicted_text, r["gold_texts"], _token_f1)
                ems.append(em)
                f1s.append(f1)

            no_ans_acc = no_ans_correct / len(no_ans_rows) if no_ans_rows else float("nan")
            has_ans_recall = has_ans_correct / len(has_ans_rows) if has_ans_rows else float("nan")
            row_line = (
                f"| {threshold:+.1f} | {sum(ems) / len(ems):.2f} | {sum(f1s) / len(f1s):.2f} | "
                f"{no_ans_acc:.2f} | {has_ans_recall:.2f} |"
            )
            lines.append(row_line)
            print(f"{category:<24} threshold={threshold:+.1f}  " + row_line.split("|", 2)[-1].strip())
        lines.append("")

    return lines


# ---------------------------------------------------------------------------
# Document classification eval
# ---------------------------------------------------------------------------

def _classification_validation_split() -> list[dict]:
    from datasets import Dataset, load_dataset

    cuad_json_path = hf_hub_download(
        repo_id="theatticusproject/cuad", repo_type="dataset", filename="CUAD_v1/CUAD_v1.json"
    )
    with open(cuad_json_path, encoding="utf-8") as f:
        cuad_raw = json.load(f)

    seen_titles = set()
    contract_texts = []
    for document in cuad_raw["data"]:
        if document["title"] in seen_titles:
            continue
        seen_titles.add(document["title"])
        full_text = "\n".join(p["context"] for p in document["paragraphs"])
        if full_text.strip():
            contract_texts.append(full_text)

    enron = load_dataset("SetFit/enron_spam", split="train")
    email_texts = [t for t in enron["text"] if t and t.strip()]

    ag_news = load_dataset("fancyzhx/ag_news", split="train")
    other_texts = [t for t in ag_news["text"] if t and t.strip()]

    rng = random.Random(SEED)

    def sample(items, cap):
        items = list(items)
        rng.shuffle(items)
        return items[:cap]

    contract_sample = sample(contract_texts, CLASSIFICATION_PER_CLASS_CAP)
    email_sample = sample(email_texts, CLASSIFICATION_PER_CLASS_CAP)
    other_sample = sample(other_texts, CLASSIFICATION_PER_CLASS_CAP)

    records = (
        [{"text": t, "label": "Contract"} for t in contract_sample]
        + [{"text": t, "label": "Email"} for t in email_sample]
        + [{"text": t, "label": "Other"} for t in other_sample]
    )
    dataset = Dataset.from_list(records).shuffle(seed=SEED)
    split = dataset.train_test_split(test_size=0.15, seed=SEED)
    return list(split["test"])


def eval_document_classification() -> list[str]:
    lines = ["## Document Classification", ""]
    print("\n=== Document Classification ===")

    print("Rebuilding the 3-class dataset (CUAD contracts + Enron emails + AG News) and its validation split...")
    val_rows = _classification_validation_split()
    print(f"Evaluating all {len(val_rows)} validation rows...")

    labels = ["Contract", "Email", "Other"]
    confusion = {gold: {pred: 0 for pred in labels} for gold in labels}

    t_start = time.time()
    for i, row in enumerate(val_rows, 1):
        result = dc.classify_document(row["text"], model_dir="models/document-classification-baseline")
        confusion[row["label"]][result.predicted_type] += 1
        if i % 20 == 0 or i == len(val_rows):
            print(f"  [{i}/{len(val_rows)}] elapsed={time.time() - t_start:6.1f}s", end="\r")
    print()

    lines.append(
        "Validation rows are the same split used for best-checkpoint selection during training "
        "(`metric_for_best_model=\"f1\"`) — see caveat in the script docstring.\n"
    )

    total = sum(sum(row.values()) for row in confusion.values())
    correct = sum(confusion[label][label] for label in labels)
    accuracy = correct / total if total else float("nan")

    lines.append("| Class | N | Precision | Recall | F1 |")
    lines.append("|---|---|---|---|---|")
    f1s = []
    for label in labels:
        gold_total = sum(confusion[label].values())
        pred_total = sum(confusion[g][label] for g in labels)
        tp = confusion[label][label]
        precision = tp / pred_total if pred_total else float("nan")
        recall = tp / gold_total if gold_total else float("nan")
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else float("nan")
        f1s.append(f1)
        row_line = f"| {label} | {gold_total} | {precision:.2f} | {recall:.2f} | {f1:.2f} |"
        lines.append(row_line)
        print(row_line.replace("|", " ").strip())

    macro_f1 = sum(f1s) / len(f1s)
    lines.append(f"| **Overall** | {total} | — | — | accuracy={accuracy:.2f}, macro-F1={macro_f1:.2f} |")
    print(f"Overall: accuracy={accuracy:.2f} macro-F1={macro_f1:.2f} over {total} rows")

    lines.append("\nConfusion matrix (rows = actual, columns = predicted):\n")
    header = "| Actual \\ Predicted | " + " | ".join(labels) + " |"
    lines.append(header)
    lines.append("|" + "---|" * (len(labels) + 1))
    for gold in labels:
        lines.append(f"| {gold} | " + " | ".join(str(confusion[gold][pred]) for pred in labels) + " |")

    return lines


# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", choices=["clauses", "classification"], default=None)
    parser.add_argument(
        "--sample-per-category",
        type=int,
        default=20,
        help="Clause-extraction eval only: rows per category to sample (default 20, ~80 total). "
        "Full-dataset eval would take hours on CPU; see script docstring.",
    )
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Sweep null-vs-span decision thresholds (see clause_extractor.NULL_MARGIN_THRESHOLD) "
        "for --calibrate-categories instead of running the normal eval.",
    )
    parser.add_argument(
        "--calibrate-categories",
        nargs="+",
        default=["Uncapped Liability", "Non-Compete"],
        help="Categories to calibrate (default: the two with weak has-answer recall).",
    )
    parser.add_argument("--calibrate-sample-per-category", type=int, default=30)
    args = parser.parse_args()

    if args.calibrate:
        report_lines = calibrate_thresholds(
            args.calibrate_categories, args.calibrate_sample_per_category, DEFAULT_CALIBRATE_GRID
        )
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        calibration_path = REPORT_PATH.parent / "threshold-calibration-report.md"
        calibration_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
        print(f"\nWrote {calibration_path}")
        return

    report_lines = [
        "# Model Evaluation Report",
        "",
        f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} — "
        "build-order step 9 (\"Testing & QA against legal-domain review\").",
        "",
        "**Caveat:** both validation splits below are the same splits each training notebook used for "
        "best-checkpoint selection (`load_best_model_at_end=True`). These are best-checkpoint validation "
        "scores, not held-out generalization estimates — see the full caveat in `scripts/eval_models.py`.",
        "",
    ]

    if args.only in (None, "clauses"):
        report_lines += eval_clause_extraction(args.sample_per_category)
    if args.only in (None, "classification"):
        report_lines += eval_document_classification()

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(f"\nWrote {REPORT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except ModuleNotFoundError as exc:
        if exc.name == "datasets":
            print("This script needs the `datasets` package: pip install datasets", file=sys.stderr)
            raise SystemExit(1) from exc
        raise
