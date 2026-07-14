"""Janela de atividade: define em quais dias da semana e faixa de horario o bot
pode checar o Drive. Fora da janela, ele nao faz nada."""
from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

# Nomes de dias aceitos -> weekday() do Python (segunda = 0 ... domingo = 6)
_WEEKDAYS = {
    "seg": 0, "segunda": 0, "mon": 0, "monday": 0,
    "ter": 1, "terca": 1, "terça": 1, "tue": 1, "tuesday": 1,
    "qua": 2, "quarta": 2, "wed": 2, "wednesday": 2,
    "qui": 3, "quinta": 3, "thu": 3, "thursday": 3,
    "sex": 4, "sexta": 4, "fri": 4, "friday": 4,
    "sab": 5, "sabado": 5, "sábado": 5, "sat": 5, "saturday": 5,
    "dom": 6, "domingo": 6, "sun": 6, "sunday": 6,
}
_NAMES_PT = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]


def _parse_days(raw: str) -> set[int]:
    """Ex.: 'ter' -> {1}; 'seg,qua,sex' -> {0,2,4}. Vazio = todos os dias."""
    if not raw or not raw.strip():
        return set(range(7))
    days = set()
    for part in raw.split(","):
        key = part.strip().lower()
        if not key:
            continue
        if key in _WEEKDAYS:
            days.add(_WEEKDAYS[key])
        elif key.isdigit() and 0 <= int(key) <= 6:
            days.add(int(key))  # 0 = segunda
        else:
            raise SystemExit(f"[window] Dia invalido em ACTIVE_DAYS: '{part}'")
    return days or set(range(7))


def _parse_time(raw: str, default: time) -> time:
    if not raw or not raw.strip():
        return default
    try:
        h, m = raw.strip().split(":")
        return time(int(h), int(m))
    except ValueError:
        raise SystemExit(f"[window] Horario invalido (use HH:MM): '{raw}'")


class ActiveWindow:
    def __init__(self, timezone: str, days: str, start: str, end: str):
        self.tz = ZoneInfo(timezone)
        self.days = _parse_days(days)
        self.start = _parse_time(start, time(0, 0))
        self.end = _parse_time(end, time(23, 59))

    def _now(self) -> datetime:
        return datetime.now(self.tz)

    def is_active(self, now: datetime | None = None) -> bool:
        now = now or self._now()
        if now.weekday() not in self.days:
            return False
        t = now.time()
        if self.start <= self.end:
            return self.start <= t <= self.end
        # Janela que "vira a meia-noite" (ex.: 22:00 -> 02:00)
        return t >= self.start or t <= self.end

    def describe(self) -> str:
        dias = ", ".join(_NAMES_PT[d] for d in sorted(self.days))
        return f"{dias} das {self.start.strftime('%H:%M')} as {self.end.strftime('%H:%M')} ({self.tz.key})"
