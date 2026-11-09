"""Senaryo v7 için standart ve JSON biçimli logging yapılandırması."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .exceptions import CiktiHatasi


class JsonLogFormatter(logging.Formatter):
    """Standart LogRecord alanlarını tek satırlı JSON'a dönüştürür."""

    def format(self, record: logging.LogRecord) -> str:
        """Bir log kaydını JSON metni olarak biçimlendirir."""
        payload: dict[str, Any] = {
            "zaman": datetime.now(UTC).isoformat(),
            "seviye": record.levelname,
            "logger": record.name,
            "mesaj": record.getMessage(),
        }
        if record.exc_info:
            payload["hata"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def kur_logger(
    ad: str = "bobi_tv.senaryo_v7",
    seviye: str | None = None,
    dosya: str | Path | None = None,
    json_format: bool | None = None,
) -> logging.Logger:
    """Console ve isteğe bağlı dosya handler'ı olan logger hazırlar."""
    logger = logging.getLogger(ad)
    logger.setLevel((seviye or os.getenv("BOBI_LOG_LEVEL") or "INFO").upper())
    logger.propagate = False
    if logger.handlers:
        return logger
    use_json = (
        json_format if json_format is not None else os.getenv("BOBI_LOG_FORMAT", "text").lower() == "json"
    )
    formatter: logging.Formatter = (
        JsonLogFormatter()
        if use_json
        else logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    logger.addHandler(stream)
    file_path = dosya or os.getenv("BOBI_LOG_FILE", "")
    if file_path:
        try:
            target = Path(file_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(target, encoding="utf-8")
        except OSError as exc:
            raise CiktiHatasi(f"Log dosyası açılamadı ({file_path}): {exc}") from exc
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
