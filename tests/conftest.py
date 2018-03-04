"""Global test fixtures and the like."""
import pytest
import tempfile
import os

@pytest.fixture
def _monkeypatch_environment(monkeypatch):
    """Monkeypatch environment variables for tests.

    Some of these are necessary for the proper functioning of the code.
    Especially either HOME or XDG_CONFIG_HOME has to exist.
    """
    with tempfile.TemporaryDirectory() as d:
        monkeypatch.setitem(os.environ, 'HOME', d)
        yield d
