from __future__ import annotations

from db.engine import engine
from db.models import Base


def init_db() -> None:
    Base.metadata.create_all(bind=engine)

