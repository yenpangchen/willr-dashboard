from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from urllib import request

from config.settings import settings


def get_logger(name: str) -> logging.Logger:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    return logging.getLogger(name)


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    logger.log(level, json.dumps(payload, ensure_ascii=True, default=str))


def emit_alert(event: str, **fields: Any) -> None:
    # Keep alert path best-effort. Never fail business flow.
    if not settings.alert_webhook_url:
        return
    body = json.dumps({"event": event, **fields}, ensure_ascii=True, default=str).encode("utf-8")
    req = request.Request(
        settings.alert_webhook_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=3) as resp:
            resp.read()
    except Exception:
        return
