# Model Evaluation Report

Generated 2026-08-27 06:32 UTC — build-order step 9 ("Testing & QA against legal-domain review").

**Caveat:** both validation splits below are the same splits each training notebook used for best-checkpoint selection (`load_best_model_at_end=True`). These are best-checkpoint validation scores, not held-out generalization estimates — see the full caveat in `scripts/eval_models.py`.

## Clause Extraction

Validation rows are the same split used for best-checkpoint selection during training (see caveat in the script docstring) — read as best-checkpoint validation performance, not a held-out generalization estimate.

| Category | N | EM | F1 | No-Answer Accuracy | Has-Answer Recall |
|---|---|---|---|---|---|
| Governing Law | 20 | 0.95 | 0.95 | 1.00 (10) | 1.00 (10) |
| Termination For Convenience | 20 | 0.75 | 0.78 | 0.90 (10) | 0.80 (10) |
| Uncapped Liability | 20 | 0.60 | 0.72 | 1.00 (10) | 0.60 (10) |
| Non-Compete | 20 | 0.70 | 0.72 | 1.00 (10) | 0.50 (10) |
| **Overall** | 80 | 0.75 | 0.79 | — | — |

## Document Classification

Validation rows are the same split used for best-checkpoint selection during training (`metric_for_best_model="f1"`) — see caveat in the script docstring.

| Class | N | Precision | Recall | F1 |
|---|---|---|---|---|
| Contract | 80 | 0.98 | 1.00 | 0.99 |
| Email | 72 | 0.99 | 0.97 | 0.98 |
| Other | 73 | 1.00 | 0.99 | 0.99 |
| **Overall** | 225 | — | — | accuracy=0.99, macro-F1=0.99 |

Confusion matrix (rows = actual, columns = predicted):

| Actual \ Predicted | Contract | Email | Other |
|---|---|---|---|
| Contract | 80 | 0 | 0 |
| Email | 2 | 70 | 0 |
| Other | 0 | 1 | 72 |
