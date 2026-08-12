# Legal Document Intelligence

AI tools to accelerate contract review, eDiscovery classification, and court
docket monitoring for legal teams. See [CLAUDE.md](CLAUDE.md) for the full
project brief, build order, and conventions.

## Status

Build order step 1 (document ingestion) and step 2 (baseline clause-extraction
model, trained in Colab and wired up for local inference) are done. Everything
after that (risk scoring, classification, docket monitoring, UI, RBAC) is not
built yet.

## Setup

```
python -m venv venv
venv\Scripts\activate      # Windows
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-dev.txt
```

`torch` is installed separately from the CPU-only index first — this avoids
pulling in large CUDA packages this machine doesn't need (see hardware
constraint below).

### Clause-extraction model

Train the baseline model in `notebooks/02_baseline_clause_extraction_colab.ipynb`
(runs on Google Colab's free GPU — see that notebook for instructions). Once
it downloads `clause_extraction_model.zip`, unzip it into:

```
models/clause-extraction-baseline/
```

`POST /documents/extract-clauses` will not work without this — it fails fast
with a clear error if the model folder is missing.

## Run the API

```
uvicorn app.main:app --reload
```

Then `POST` a `.pdf` or `.docx` file to `http://127.0.0.1:8000/documents/parse`
to extract text, or to `http://127.0.0.1:8000/documents/extract-clauses` to
also run the trained clause-extraction model against it (requires the model
to be downloaded and unzipped locally — see "Clause-extraction model" above).

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
