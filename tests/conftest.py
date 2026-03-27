from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_home(monkeypatch, tmp_path):
    # Prevent tests from reading any real user `~/.planhub/config.yaml`.
    monkeypatch.setenv("HOME", str(tmp_path))
    yield
