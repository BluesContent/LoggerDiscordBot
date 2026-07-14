"""Guarda em disco quais pastas ja foram avisadas (para nao repetir) + historico."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


class State:
    def __init__(self, path: Path, tz: str = "America/Sao_Paulo"):
        self.path = Path(path)
        self.tz = tz
        self._records: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self._records = data.get("notified", {})
            except (json.JSONDecodeError, OSError):
                self._records = {}

    def _save(self) -> None:
        self.path.write_text(
            json.dumps({"notified": self._records}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def already_notified(self, folder_id: str) -> bool:
        return folder_id in self._records

    def mark_notified(self, folder_id: str, meta: dict | None = None) -> None:
        rec = dict(meta or {})
        rec["sent_at"] = datetime.now(ZoneInfo(self.tz)).strftime("%Y-%m-%d %H:%M:%S")
        self._records[folder_id] = rec
        self._save()

    def forget(self, folder_id: str) -> bool:
        """Remove o registro (permite reenviar). Retorna True se existia."""
        if folder_id in self._records:
            del self._records[folder_id]
            self._save()
            return True
        return False

    def history(self) -> list[dict]:
        items = [dict(v, folder_id=k) for k, v in self._records.items()]
        items.sort(key=lambda x: x.get("sent_at", ""), reverse=True)
        return items
