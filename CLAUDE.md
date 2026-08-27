# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Legal Document Intelligence — Project Brief

## What this project is
AI tools to accelerate contract review, eDiscovery classification, and court
docket monitoring for legal teams. The platform ingests contracts, discovery
documents, and docket data, applies NLP to extract risk-relevant clauses,
classify documents, and alert legal teams to relevant docket activity.

## Target users
Corporate counsel, paralegals, litigation support teams, law firms doing
high-volume contract review, compliance/risk departments.

## Tech stack
- **Backend:** Python, FastAPI
- **Frontend:** React
- **Database:** SQLite for now — step 8 (RBAC) shipped on it too; multiple
  users hitting the same file concurrently works fine at this app's current
  scale. PostgreSQL remains a possible future target if real write
  concurrency ever becomes a bottleneck, but that's not auto-triggered by
  RBAC existing — it's a separate decision if/when it comes up.
- **NLP/ML:** Hugging Face `transformers` + `datasets`, PyTorch
- **Document parsing:** `pdfplumber` (PDF), `python-docx` (Word)
- **Docket monitoring:** custom scraping/integration + diff-based change detection (not ML)

## Hardware constraint — IMPORTANT
This machine (Intel i7-8550U, 4C/8T, 16GB RAM, no dedicated GPU) is not
suitable for local model training. Rules to follow:
- Do NOT install or run heavy training workloads locally (no `torch` training
  loops, no local fine-tuning jobs).
- All model fine-tuning happens in **Google Colab** (free GPU tier). Write
  training scripts so they can be copy-pasted into a Colab notebook with
  minimal changes (avoid local-only file paths, keep dependencies minimal).
- Locally, only run **inference** on already-trained/downloaded model
  checkpoints — this is light enough for CPU.
- Keep local RAM usage in mind: prefer streaming/batched data loading over
  loading full datasets into memory at once.

## Core dataset
- **CUAD (Contract Understanding Atticus Dataset)** — 510 contracts, 13,000+
  expert annotations across 41 clause categories. Source of truth for clause
  extraction and risk-flagging model training.
  - https://huggingface.co/datasets/theatticusproject/cuad
  - Paper: https://arxiv.org/abs/2103.06268

## Clause categories to start with (narrow scope first)
Start with these 4 before expanding to all 41 CUAD categories:
1. Governing Law
2. Termination for Convenience
3. Uncapped Liability
4. Non-Compete

## Build order (do not skip ahead)
1. Document ingestion pipeline — PDF/DOCX parsing, text extraction
2. Baseline clause-extraction model (Colab) — fine-tune a small model
   (e.g. `distilbert-base-uncased`) on the 4 clause categories above, framed
   as extractive QA (same approach as the original CUAD paper)
3. Risk-flagging logic + confidence scoring on top of extraction output
4. eDiscovery document classification model (Colab)
5. Docket monitoring integration + change-detection + alerting (backend only, no ML)
6. Review interface — highlighted clauses, risk scores, case/matter organization
7. Reporting/export for stakeholders
8. Role-based access control (attorneys / paralegals / support staff) + audit trail
9. Testing & QA against legal-domain review
10. UAT, refinement, deployment

## Conventions
- Keep experimentation (`notebooks/`, one-off scripts) separate from
  production code (`src/`, `app/`). Only promote validated pipelines into
  production folders.
- Use Plan mode for any milestone before letting Claude Code write files —
  review the plan, then approve.
- Every clause-extraction/classification output should be reviewable by a
  human (this is a human-in-the-loop tool, not full automation) — reflect
  this in UI and API design.
- Sensitive legal documents: RBAC is implemented (build-order step 8 —
  JWT auth, 3 roles, route-level enforcement, audit trail). Encrypted
  storage at rest is a deliberate, tracked follow-up, not forgotten — see
  README's "Authentication / RBAC" section.

## Non-goals for now
- Do not attempt full 41-category CUAD coverage until the 4-category
  baseline is working end-to-end.
- Do not build custom legal-taxonomy definitions without validating against
  CUAD's existing categories first.

## Setup

```
python -m venv venv
venv\Scripts\activate      # Windows
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-dev.txt
```

`torch` is installed separately from the CPU-only index first to avoid
pulling in CUDA packages this machine doesn't need.

## Commands

```
uvicorn app.main:app --reload   # run the API (http://127.0.0.1:8000)
pytest                          # run the full test suite
pytest tests/extraction         # run one test package
pytest tests/ingestion/test_pdf_parser.py::test_parse_pdf_extracts_text  # single test
```

There is no configured lint/format command yet.

```
python -m scripts.eval_models              # build-order step 9: model accuracy QA (see below)
python -m scripts.upload_models_to_hub     # build-order step 10: push trained checkpoints to
                                            # Hugging Face Hub for deployment (see README's
                                            # Deployment section) - render.yaml's
                                            # CLAUSE_MODEL_DIR/DOCUMENT_CLASSIFICATION_MODEL_DIR
                                            # point at the repo ids it creates
```

The clause-extraction model itself is trained in
`notebooks/02_baseline_clause_extraction_colab.ipynb` on Google Colab, not
locally (see hardware constraint above). Once trained, download
`clause_extraction_model.zip` and unzip it into `models/clause-extraction-baseline/`
— `POST /documents/extract-clauses` fails fast with a clear error if that
folder is missing. Tests don't need the real trained model: they build a
throwaway model with an untrained QA head from the base `distilbert-base-uncased`
checkpoint (`tests/extraction/conftest.py::stub_model_dir`) to exercise the
extraction code path without asserting on prediction quality.

## Model evaluation (build-order step 9)

`scripts/eval_models.py` evaluates both trained checkpoints against validation data
reconstructed with the *exact* filtering/sampling/split logic (same seed=42) as their
training notebooks — this is what the unit test suite deliberately doesn't check (tests
use an untrained-head stub model to exercise code paths, not assert on prediction
quality). Requires `datasets` (`requirements-dev.txt`, not a runtime dependency of the
app itself). Clause extraction is CPU-slow (sliding-window QA over full contract text,
10-30s/example on this hardware) so it's capped to a stratified per-category sample by
default (`--sample-per-category`, default 20); document classification is a fast single
forward pass per example and always runs the full validation split. Results are printed
to stdout and written to `docs/model-eval-report.md`.

`--calibrate` (with `--calibrate-categories`, default the two weak ones, and
`--calibrate-sample-per-category`) switches modes: it scores each row *once* via
`clause_extractor._score_span` (cached margin, independent of any threshold), then sweeps
a threshold grid cheaply against those cached margins — this is how
`clause_extractor.NULL_MARGIN_THRESHOLD`'s values were picked (data-driven, not guessed).
Writes `docs/threshold-calibration-report.md`.

**Important caveat carried through both the script and its output**: the validation
split evaluated is the *same* split each notebook passed as `eval_dataset` to its
`Trainer` for best-checkpoint selection (`load_best_model_at_end=True`) — so these are
best-checkpoint validation numbers, not a held-out generalization estimate. A true
held-out test set would need the notebooks re-run with a 3-way split before training,
which hasn't happened.

## Architecture

Two layers: `app/` is a thin FastAPI layer, `src/legalintel/` is the
importable core library the API calls into. `pyproject.toml` puts both
`src` and the repo root on `pythonpath` for pytest, so tests import
`legalintel.*` the same way `app/` does.

- `app/api/routes/documents.py` — `POST /documents/parse` writes the upload
  to a temp file, calls `legalintel.ingestion.pipeline.parse_document`, then
  deletes the temp file (nothing is persisted to disk yet — see README
  notes). `POST /documents/extract-clauses` does the same parse, then runs
  extraction + risk-flagging. `POST /documents/classify` does the same parse,
  then runs the document-type classifier — kept as its own endpoint (not
  folded into `/extract-clauses`) since it's a separate, independent model
  and shouldn't require loading the (larger) clause-extraction model. All
  three require `attorney` or `paralegal` (`dependencies=[Depends(require_role(...))]`)
  — support staff is read-only across this whole app.
- `app/api/routes/dockets.py` — separate router, no relation to `documents.py`.
  `POST /dockets/track`, `POST /dockets/{id}/check` require attorney/paralegal;
  `GET /dockets`, `GET /dockets/{id}/alerts`, `GET /dockets/{id}/entries` require
  any authenticated user — thin HTTP-status mapping (503/404/409/502) over
  `legalintel.docket`'s exceptions; all persistence/business logic lives in
  `src/legalintel/docket/`, not here. `/track` validates a given `matter_id`
  exists (404 if not) before contacting CourtListener.
- `app/api/routes/matters.py` — `POST /matters` (attorney/paralegal, sets
  `created_by` from the current user, logs `"matter_created"`), `GET /matters`
  and `GET /matters/{id}` (any authenticated user; composed `MatterDetail`:
  the matter plus its `legalintel.matters.db.list_matter_documents` and
  `legalintel.docket.db.list_tracked_dockets_for_matter`), `DELETE /matters/{id}`
  (attorney-only, cascades child rows via `matters_db.delete_matter` before
  deleting the matter itself, logs `"matter_deleted"`). Also nests the
  clause-review endpoints here (matter-document-scoped, not a separate
  router): `GET .../review` (any authenticated user), `POST`/`DELETE
  .../review/{clause_index}` (attorney/paralegal; POST logs
  `"clause_reviewed"` and resolves the reviewer's name via `auth_db.get_user_by_id`
  for the response, since `legalintel.auth.db` only stores `reviewed_by` as
  an id).
- `app/api/routes/auth.py` — `POST /auth/login` (401 on bad email OR bad
  password, always the same generic message — never reveal which one was
  wrong; logs `"login"`), `POST /auth/logout` (204, stateless JWT so there's
  nothing to invalidate server-side — exists purely so a `"logout"` audit
  event has somewhere to fire from), `GET /auth/me`, `POST /auth/users`
  (attorney-only, 201, 409 on duplicate email), `GET /auth/audit-log`
  (attorney-only).
- `app/core/security.py` — `get_current_user` (FastAPI dependency; decodes
  the bearer token, then re-fetches the user from the DB and checks
  `is_active` on *every* request rather than trusting a role embedded in the
  token, so deactivating a user takes effect immediately with no blacklist
  needed) and `require_role(*roles)` (returns a `Depends()`-able that 403s
  otherwise). Status mapping: no/bad/expired token or a deactivated user →
  401 (never distinguish which, same principle as login); missing
  `JWT_SECRET_KEY` (server misconfig) → 503; authenticated but wrong role →
  403.
- `src/legalintel/auth/` — `security.py` holds pure functions with no DB/
  Settings access (`hash_password`/`verify_password` via `bcrypt`,
  `create_access_token`/`decode_access_token` via `PyJWT`, HS256, 8h expiry,
  `sub` = user id only, no refresh token). `db.py` mirrors `docket/db.py`'s/
  `matters/db.py`'s conventions (`db_path` first arg) for `users`,
  `audit_log`, and `clause_reviews` — `set_clause_reviewed` is an upsert on
  `clause_reviews`' `(matter_document_id, clause_index)` UNIQUE constraint,
  so re-reviewing overwrites who/when (it's current-state, not a log; the
  `audit_log` `"clause_reviewed"` entry is what preserves history).
  `clause_reviews` has no FK to a clauses table since clauses aren't
  normalized (`matter_documents.result_json` is an opaque blob, existing
  convention) — `clause_index` is positional into that document's `clauses`
  array.
- `app/core/config.py` — single `Settings` object (pydantic-settings, reads
  `.env`) with upload limits, allowed extensions, `clause_model_dir`,
  `document_classification_model_dir`, `cors_allow_origins`,
  `courtlistener_api_token`/`courtlistener_base_url`, `jwt_secret_key`, and
  `db_path` (shared SQLite file for dockets + matters + auth — see
  `storage.py` below).
- `src/legalintel/ingestion/` — `pdf_parser.py` (pdfplumber) and
  `docx_parser.py` (python-docx) each return a list of `ParsedPage`;
  `pipeline.py` dispatches by file extension and joins pages into a
  `ParsedDocument`. Add a new file type by adding a parser function and
  registering it in `pipeline.py`'s `_PARSERS` dict.
- `src/legalintel/extraction/clause_extractor.py` — loads the fine-tuned QA
  model as a process-wide singleton (`@lru_cache`), one hardcoded question
  per clause category in `QUESTIONS` (must exactly match the question
  phrasing used during training in the Colab notebook — QA models are
  sensitive to this). Inference runs CUAD/SQuAD2.0-style: sliding-window
  tokenization (`MAX_LENGTH`/`STRIDE` must match the notebook's training
  config), best-span decoding per window, and a null-vs-span score
  comparison so the model can report "no clause of this type found" instead
  of forcing a low-quality match. `_score_span` (pure scoring) is split from
  `_predict_answer` (applies the null-vs-span decision) specifically so
  `scripts/eval_models.py --calibrate` can sweep decision thresholds without
  re-running inference per threshold. `NULL_MARGIN_THRESHOLD` lowers that
  decision bar per-category — Uncapped Liability and Non-Compete had strong
  no-answer accuracy but weak has-answer recall in step-9 QA (see
  docs/model-eval-report.md), so their threshold trades some precision for
  recall; Governing Law/Termination For Convenience keep the model's default
  (0.0) since their recall was already fine. `_looks_negated` is a separate
  regex heuristic (not a model) that sets `ClauseMatch.possible_negation`
  when a match is preceded by or begins with negation language (e.g.
  "Neither Party may terminate...for convenience") — a real false-positive
  shape found during step-9 QA where the model matches on surface phrasing
  without registering the negation. It only adds a reviewer-facing warning,
  never suppresses a match, since suppressing on a heuristic could hide a
  genuine clause. `_load_model` checks for a local folder first (unchanged
  dev behavior/error message); if that's not there and the string looks
  like a Hugging Face Hub repo id (`_looks_like_hub_repo_id` — deliberately
  excludes Windows paths so a missing local folder still fails fast offline
  in tests, rather than attempting a real Hub network call), it falls
  through to `from_pretrained` fetching from the Hub — see "Deployment" in
  README for why (the 250MB+ checkpoint can't be committed to git).
- `src/legalintel/risk/flagging.py` — pure rule-based Python (no model), run
  after extraction in `app/api/routes/documents.py`. A static
  `SEVERITY_BY_CATEGORY` dict assigns each clause category a fixed
  `RiskLevel`, and `band_for_confidence` buckets the extractor's raw
  confidence float into HIGH/MEDIUM/LOW for reviewer legibility.
  `apply_risk_flags`/`summarize_risk` enrich `ClauseMatch`es and build the
  document-level `RiskSummary`.
- `src/legalintel/classification/document_classifier.py` — mirrors
  `clause_extractor.py`'s lazy-singleton (`@lru_cache`) + `ModelNotFoundError`
  pattern, but for 3-class sequence classification (Contract/Email/Other,
  trained in `notebooks/03_document_classification_colab.ipynb`) via
  `POST /documents/classify`. Returns the full softmax probability
  distribution, not just the top label, for human-in-the-loop transparency.
  The "Other" class is a placeholder proxy (news-article text) — see README.
  `_load_model` has the same local-folder-then-Hub-repo-id fallback as
  `clause_extractor.py`, for the same reason.
- `src/legalintel/storage.py` — the single source of schema truth for every
  SQLite table in the app (`users`, `matters` — including its
  `created_by REFERENCES users(id)` column — `matter_documents`,
  `tracked_dockets`, `seen_docket_entries`, `docket_alerts`, `audit_log`,
  `clause_reviews`), plus the shared `connect(db_path)` context manager
  (`PRAGMA foreign_keys = ON`, `sqlite3.Row` row factory, `CREATE TABLE IF
  NOT EXISTS` re-run cheaply on every connect). `docket/db.py`,
  `matters/db.py`, and `auth/db.py` all import `connect` from here rather
  than defining their own — each still only queries the tables it "owns."
- `src/legalintel/docket/` — no ML, unlike everything above. `db.py` stores
  `tracked_dockets` (`matter_id` is a real `INTEGER REFERENCES matters(id)`,
  nullable), `seen_docket_entries`, `docket_alerts`; it's the only place raw
  SQL rows get converted to/from `legalintel.models.docket` pydantic types.
  `courtlistener_client.py` wraps the free CourtListener/RECAP API
  (`Authorization: Token <key>` header; 5/min-50/hr-125/day rate limit, so
  this is on-demand only, no background polling — its `_get` retries on 429
  with a backoff parsed from CourtListener's own "expected available in N
  seconds" message, since a single large docket's pagination can exhaust the
  budget on its own) with a `transport=` seam for test doubles
  (`httpx.MockTransport`) and a `ModelNotFoundError`-style
  `CourtListenerConfigError` when the token is missing. `monitor.py`'s
  `check_docket_for_updates` is the diff: fetch current entries, compare
  against `db.get_seen_entry_ids`, persist + alert only on what's new.
- `src/legalintel/matters/db.py` — mirrors `docket/db.py`'s conventions
  exactly (`db_path` first arg, rows → pydantic models inside `db.py`).
  `matter_documents` is one generic row per persisted analysis
  (`analysis_type` discriminant + `result_json` blob of the corresponding
  `ParsedDocument`/`ClauseExtractionResult`/`DocumentClassificationResult`),
  not three normalized tables — nothing yet needs cross-document clause
  querying. `app/api/routes/documents.py`'s three endpoints persist into
  this only when a caller supplies `matter_id`; omitting it keeps today's
  fully-ephemeral behavior (parse, analyze, discard).
- `src/legalintel/reporting/report_generator.py` — `generate_matter_report`
  is a pure function (no DB access, mirroring `risk/flagging.py`'s
  already-fetched-data convention) that takes a composed `MatterDetail` plus
  a `tracked_docket_id -> alerts` dict (alerts aren't included in
  `MatterDetail` itself) and returns PDF bytes via
  `reportlab.platypus.SimpleDocTemplate` — the first use of the higher-level
  flowables API in this repo (vs. `tests/conftest.py`'s low-level
  `canvas.drawString`, fine for one fixed line but unworkable for this
  report's variable-length, multi-section content). Branches on each
  `MatterDocument.analysis_type` exactly like
  `frontend/src/components/MatterDocumentCard.tsx` does, re-hydrating the raw
  `result` dict into `ParsedDocument`/`ClauseExtractionResult`/
  `DocumentClassificationResult` via `.model_validate(...)` rather than
  indexing the dict by hand. `GET /matters/{id}/report` in
  `app/api/routes/matters.py` does all the querying (via a shared
  `_load_matter_detail` helper also used by `GET /matters/{id}`) and returns
  a raw `fastapi.responses.Response` with `Content-Disposition: attachment`.
  Carries the same human-in-the-loop disclaimer this codebase already
  surfaces in the UI (e.g. `DocumentClassificationCard`'s "First-pass triage
  only" notice) since the report hands AI-derived analysis to someone
  without app access to see those in-app caveats.
- `src/legalintel/models/document.py` — the pydantic models
  (`ParsedPage`, `ParsedDocument`, `ClauseMatch`, `ClauseExtractionResult`,
  `RiskSummary`, `DocumentClassification`, `DocumentClassificationResult`)
  shared across ingestion, extraction, risk-flagging, classification, and
  API responses/schemas. `src/legalintel/models/docket.py` holds the
  docket-monitoring models (`TrackedDocket`, `DocketEntry`, `DocketAlert`,
  `DocketCheckResult`) separately, since it's an unrelated domain.
  `src/legalintel/models/matter.py` holds `Matter`/`MatterDocument`/
  `MatterDetail` — `MatterDocument.result` is typed as a plain `dict` here
  (it's an opaque JSON blob on the backend); the frontend re-adds precision
  via a discriminated union on `analysis_type`.
- `tests/` mirrors `src/legalintel/`'s package layout. Fixtures generate
  sample PDF/DOCX files on the fly (`tests/conftest.py`, via `reportlab`/
  `python-docx`) rather than checking in binary fixture files. Model-backed
  test packages (`tests/extraction/`, `tests/classification/`) each have a
  `conftest.py` that builds a throwaway untrained-head model from the base
  checkpoint, so tests exercise the code path without needing real trained
  weights or asserting on prediction quality. `tests/docket/` never hits the
  real CourtListener API — every test uses an `httpx.MockTransport` double
  (`tests/docket/conftest.py`) and a `tmp_path`-based SQLite file. It also
  has this repo's first `TestClient` (route-level) tests. `tests/matters/`
  mirrors that style (no external API, so no mocking needed) and includes a
  regression test that `matter_documents`' FK constraint is actually
  enforced (`PRAGMA foreign_keys = ON` in `storage.py`).
- `frontend/` — a Vite + React + TypeScript app with `react-router-dom`
  (`frontend/src/types/api.ts`/`docket.ts`/`matter.ts`/`user.ts` mirror the
  backend pydantic models). Routes: `/login` (`LoginPage`); everything else
  is wrapped in `<RequireAuth>` (redirects to `/login` if no session) —
  `/` (`MattersListPage` — create/list, create-form hidden for support
  staff), `/matters/:matterId` (`MatterDetailPage` — the review interface:
  upload form scoped to the matter, persisted `MatterDocument`s rendered via
  `MatterDocumentCard` reusing the same `ClauseList`/`DocumentTextViewer`/
  `DocumentClassificationCard` components as live results, plus tracked
  dockets/alerts, plus an attorney-only delete-matter button), `/quick-analyze`
  (`QuickAnalyzePage` — today's original ephemeral flow, kept but relocated,
  always analyzes with `matterId: null` so nothing persists), `/admin`
  (`AdminPage` — attorney-only, create-user form + audit-log table).
  `auth/AuthContext.tsx` holds `{user, loading, login, logout}` (backed by
  `auth/tokenStore.ts`'s plain `localStorage` get/set/clear, not React
  state, so `api/client.ts` can read the token without importing React);
  `api/client.ts` attaches `Authorization: Bearer <token>` to every request
  and exposes a tiny `onUnauthorized` pub-sub so a 401 from *any* call
  clears the session immediately, not just the one currently in flight.
  Clause-review persistence is split by call site: `QuickAnalyzePage` still
  uses `hooks/useReviewedClauses.ts` (client-only `Set<number>`, resets on
  reload — it carries no audit meaning), while `MatterDocumentCard` uses the
  new `hooks/usePersistedClauseReviews.ts` (hits
  `GET/POST/DELETE /matters/{id}/documents/{id}/review...`, exposes a
  `reviewerFor(index)` resolver so `ClauseListItem` can render a "Reviewed
  by X" byline). No state library, no UI kit — still deliberately minimal
  beyond the router and this one auth context.
