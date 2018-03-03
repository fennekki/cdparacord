import pytest
import tempfile


@pytest.fixture
def mock_config_dir(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        yield d
