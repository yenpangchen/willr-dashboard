"""Vercel FastAPI entrypoint.

Vercel looks for a FastAPI instance named `app` at `app.py`/`index.py`/`server.py`.
"""

from api.main import app  # re-export

__all__ = ["app"]

