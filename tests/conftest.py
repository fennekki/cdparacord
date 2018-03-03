import pytest
import tempfile


@pytest.fixture
def mock_config_dir(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        import os
        # Monkeypatch XDG_CONFIG_HOME inside these tests
        # This way we don't need to have a $HOME
        monkeypatch.setitem(os.environ, 'XDG_CONFIG_HOME', d)
        yield d
