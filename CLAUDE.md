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
- **Database:** PostgreSQL (case/matter organization, audit trail)
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
- Sensitive legal documents: enforce encrypted storage and RBAC from the
  start, not as an afterthought.

## Non-goals for now
- Do not attempt full 41-category CUAD coverage until the 4-category
  baseline is working end-to-end.
- Do not build custom legal-taxonomy definitions without validating against
  CUAD's existing categories first.
