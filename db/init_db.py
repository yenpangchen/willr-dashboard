from __future__ import annotations

from db.engine import engine
from db.models import Base


def init_db() -> bool:
    try:
        Base.metadata.create_all(bind=engine)
        return True
    except Exception:
        # Keep API available by allowing service layer fallback.
        return False

