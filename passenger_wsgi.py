"""Entry point for cPanel's "Setup Python App" (Phusion Passenger). Passenger looks for a
WSGI `application` callable in this exact file at the app's root - FastAPI is ASGI-only, so
a2wsgi bridges the two. Not used by any other deployment path (Docker/Render run app.main:app
directly via uvicorn, which speaks ASGI natively)."""

from a2wsgi import ASGIMiddleware

from app.main import app as _asgi_app

application = ASGIMiddleware(_asgi_app)
