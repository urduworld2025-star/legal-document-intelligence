"""Entry point for cPanel's "Setup Python App" (Phusion Passenger). Passenger looks for a
WSGI `application` callable in this exact file at the app's root - FastAPI is ASGI-only, so
a2wsgi bridges the two. Not used by any other deployment path (Docker/Render run app.main:app
directly via uvicorn, which speaks ASGI natively)."""

import os

# Must be set before numpy/torch are imported (they read these at C-extension init time,
# via app.main -> ... -> transformers). OpenBLAS otherwise auto-detects the *host machine's*
# full core count (e.g. 32) and tries to spawn a matching thread pool, which segfaults on
# shared hosting where the account's actual thread/process limit (RLIMIT_NPROC) is far lower
# than the host's real capacity - hit during deployment. Single-threaded BLAS is fine for
# this app's workload (small CPU inference, not heavy parallel linear algebra).
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

from a2wsgi import ASGIMiddleware

from app.main import app as _asgi_app

application = ASGIMiddleware(_asgi_app)
