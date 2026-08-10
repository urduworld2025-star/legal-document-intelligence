# Legal Document Intelligence

AI tools to accelerate contract review, eDiscovery classification, and court
docket monitoring for legal teams. See [CLAUDE.md](CLAUDE.md) for the full
project brief, build order, and conventions.

## Status

Build order step 1: document ingestion pipeline (PDF/DOCX parsing + text
extraction). Everything after that (model training, risk scoring,
classification, docket monitoring, UI, RBAC) is not built yet.

## Setup

```
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements-dev.txt
```

## Run the API

```
uvicorn app.main:app --reload
```

Then `POST` a `.pdf` or `.docx` file to `http://127.0.0.1:8000/documents/parse`.

## Run tests

```
pytest
```

## Notes

- All model fine-tuning happens in Google Colab, not locally (see
  hardware-constraint section of CLAUDE.md). Locally we only run inference
  and non-ML pipeline code such as document parsing.
- Uploaded documents are parsed from a temporary file and deleted immediately
  after — nothing is persisted to disk yet. Full encrypted-at-rest storage
  and RBAC land at build-order step 8.
