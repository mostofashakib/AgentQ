from agentq.api.alerts.cooldown import CooldownTracker
from datetime import UTC, datetime, timedelta


def test_first_fire_is_always_allowed():
    t = CooldownTracker()
    assert t.can_fire("r1", frequency_limit=3, cooldown_minutes=5) is True


def test_frequency_limit_blocks_after_n_fires():
    t = CooldownTracker()
    t.record_fire("r1")
    t.record_fire("r1")
    t.record_fire("r1")
    assert t.can_fire("r1", frequency_limit=3, cooldown_minutes=0) is False


def test_frequency_limit_zero_means_unlimited():
    t = CooldownTracker()
    for _ in range(100):
        t.record_fire("r1")
    assert t.can_fire("r1", frequency_limit=0, cooldown_minutes=0) is True


def test_cooldown_blocks_within_window():
    t = CooldownTracker()
    t.record_fire("r1")
    assert t.can_fire("r1", frequency_limit=0, cooldown_minutes=60) is False


def test_cooldown_zero_means_no_cooldown():
    t = CooldownTracker()
    t.record_fire("r1")
    assert t.can_fire("r1", frequency_limit=0, cooldown_minutes=0) is True


def test_cooldown_allows_after_window_expires(monkeypatch):
    t = CooldownTracker()
    t.record_fire("r1")
    # Simulate last_fired being 2 hours ago
    past = datetime.now(UTC) - timedelta(hours=2)
    t._state["r1"]["last_fired"] = past
    assert t.can_fire("r1", frequency_limit=0, cooldown_minutes=60) is True


def test_different_rule_ids_are_independent():
    t = CooldownTracker()
    t.record_fire("r1")
    t.record_fire("r1")
    t.record_fire("r1")
    assert t.can_fire("r1", frequency_limit=3, cooldown_minutes=0) is False
    assert t.can_fire("r2", frequency_limit=3, cooldown_minutes=0) is True
