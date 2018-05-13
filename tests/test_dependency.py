"""Tests for the dependency module."""

import pytest
import stat
import os
import os.path
from tempfile import NamedTemporaryFile
from cdparacord.dependency import Dependency, DependencyError


@pytest.fixture
def mock_external_binary():
    """Mock an external dependency binary.
    
    Create a file, set it to be executable and return it as an
    ostensible external binary.
    """
    with NamedTemporaryFile(prefix='cdparacord-unittest-') as f:
        os.chmod(f.name, stat.S_IXUSR)
        yield f.name


@pytest.fixture
def mock_config_external():
    """Mock the Config class such that it always returns given name."""
    def get_config(mockbin):
        class MockConfig:
            def get(self, name):
                # Maybe we should write a fake config file but there are
                # Huge issues with mocking the config module...
                if name == 'encoder':
                    return {mockbin: []}
                return mockbin
        return MockConfig()
    return get_config


def test_find_valid_absolute_dependencies(mock_external_binary, mock_config_external):
    """Finds fake dependencies that exist by absolute path."""
    
    Dependency(mock_config_external(mock_external_binary))


def test_find_valid_dependencies_in_path(mock_external_binary, mock_config_external, monkeypatch):
    """Finds fake dependencies that exist in $PATH."""

    dirname, basename = os.path.split(mock_external_binary)
    # Set PATH to only contain the directory our things are in
    monkeypatch.setenv("PATH", dirname)
    Dependency(mock_config_external(basename))


def test_fail_to_find_dependencies(mock_config_external):
    with NamedTemporaryFile(prefix='cdparacord-unittest-') as f:
        # This file should not be executable by default so the finding
        # should fail
        with pytest.raises(DependencyError):
            Dependency(mock_config_external(f.name))


def test_get_encoder(mock_config_external, mock_external_binary):
    """Get the 'encoder' property."""

    deps = Dependency(mock_config_external(mock_external_binary))
    # It's an absolute path so the value should be the same
    assert deps.encoder == mock_external_binary


def test_get_editor(mock_config_external, mock_external_binary):
    """Get the 'editor' property."""

    deps = Dependency(mock_config_external(mock_external_binary))
    # It's an absolute path so the value should be the same
    assert deps.editor == mock_external_binary


def test_get_cdparanoia(mock_config_external, mock_external_binary):
    """Get the 'cdparanoia' property."""

    deps = Dependency(mock_config_external(mock_external_binary))
    # It's an absolute path so the value should be the same
    assert deps.cdparanoia == mock_external_binary
