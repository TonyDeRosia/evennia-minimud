import pytest
import types

@pytest.fixture(autouse=True)
def mock_timers(monkeypatch):
    """Provide deterministic timers for spawn manager tests."""
    counter = {"t": 0}

    def fake_time():
        counter["t"] += 1
        return counter["t"]

    monkeypatch.setattr("scripts.spawn_manager.time.time", fake_time)
    monkeypatch.setattr("scripts.mob_respawn_manager.time.time", fake_time)
    yield

