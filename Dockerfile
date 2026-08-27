# Backend-only image, built for Hugging Face Spaces (Docker SDK) - listens on port 7860,
# the port Spaces expects. The frontend is deployed separately (Netlify), not part of this
# image. Model checkpoints aren't baked in either - they're fetched from Hugging Face Hub
# at runtime via CLAUSE_MODEL_DIR / DOCUMENT_CLASSIFICATION_MODEL_DIR (see
# src/legalintel/extraction/clause_extractor.py and .../classification/document_classifier.py).
FROM python:3.11-slim

WORKDIR /app

# CPU-only PyTorch wheel first, same reasoning as the local dev setup in README - avoids
# pulling in CUDA packages this deployment target doesn't have a GPU for either.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY src/ ./src/
RUN pip install --no-cache-dir -e .

# Ephemeral by design on Spaces' free tier (no persistent disk) - data resets on restart/
# redeploy. Fine for a demo deployment; see README's Deployment section for the tradeoff.
RUN mkdir -p /app/data
ENV DB_PATH=/app/data/legalintel.db

EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
