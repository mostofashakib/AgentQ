# agentq/api/alerts/cooldown.py
from __future__ import annotations
from agentq.utils.time import ensure_utc, utc_now


class CooldownTracker:
    def __init__(self) -> None:
        self._state: dict[str, dict] = {}

    def can_fire(self, rule_id: str, frequency_limit: int, cooldown_minutes: int) -> bool:
        now = utc_now()
        state = self._state.get(rule_id, {
            "count": 0, "window_start": now, "last_fired": None,
        })

        # Reset hourly window
        if (now - ensure_utc(state["window_start"])).total_seconds() >= 3600:
            state = {"count": 0, "window_start": now, "last_fired": state.get("last_fired")}

        if frequency_limit > 0 and state["count"] >= frequency_limit:
            return False

        if cooldown_minutes > 0 and state["last_fired"] is not None:
            elapsed = (now - ensure_utc(state["last_fired"])).total_seconds()
            if elapsed < cooldown_minutes * 60:
                return False

        return True

    def record_fire(self, rule_id: str) -> None:
        now = utc_now()
        state = self._state.get(rule_id, {
            "count": 0, "window_start": now, "last_fired": None,
        })
        if (now - ensure_utc(state["window_start"])).total_seconds() >= 3600:
            state = {"count": 0, "window_start": now, "last_fired": None}
        state["count"] += 1
        state["last_fired"] = now
        self._state[rule_id] = state


# Module-level singleton used by alert_worker
cooldown_tracker = CooldownTracker()
