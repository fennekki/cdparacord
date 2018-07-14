"""Tests for the dependency module."""

import pytest
import stat
import os
import os.path
from tempfile import NamedTemporaryFile
from cdparacord.dependency import Dependency, DependencyError


@pytest.fixture
def mock_config_external():
    """Mock the Config class such that it returns self.param.

    In addition, querying for  encoder results in a dict that contains
    an empty list in the key self.param.
    """
    class MockConfig:
        def __init__(self, param):
            self.param = param
            self.encoder = {self.param: []}
            self.post = [{self.param: []}]

        def get(self, name):
            # Maybe we should write a fake config file but there are
            # Huge issues with mocking the config module...
            if name == 'encoder':
                return self.encoder
            if name in ('post_rip', 'post_encode', 'post_finished'):
                return self.post
            return self.param
    return MockConfig


@pytest.fixture
def mock_external_encoder(mock_config_external):
    """Mock an external dependency binary.

    Create a file, set it to be executable and return it as an
    ostensible external binary via configuration.
    """
    with NamedTemporaryFile(prefix='cdparacord-unittest-') as f:
        os.chmod(f.name, stat.S_IXUSR)

        conf = mock_config_external(f.name)
        yield conf


def test_find_valid_absolute_dependencies(mock_external_encoder):
    """Finds fake dependencies that exist by absolute path."""
    Dependency(mock_external_encoder)


def test_find_valid_dependencies_in_path(mock_external_encoder, monkeypatch):
    """Finds fake dependencies that exist in $PATH."""

    dirname, basename = os.path.split(mock_external_encoder.param)
    # Set PATH to only contain the directory our things are in
    monkeypatch.setenv("PATH", dirname)
    conf = mock_external_encoder
    conf.param = basename
    Dependency(conf)


def test_fail_to_find_dependencies(mock_config_external):
    with NamedTemporaryFile(prefix='cdparacord-unittest-') as f:
        # This file should not be executable by default so the finding
        # should fail
        with pytest.raises(DependencyError):
            conf = mock_config_external(f.name)
            Dependency(conf)


def test_get_encoder(mock_external_encoder):
    """Get the 'encoder' property."""

    deps = Dependency(mock_external_encoder)
    # It's an absolute path so the value should be the same
    assert deps.encoder == mock_external_encoder.param


def test_get_editor(mock_external_encoder):
    """Get the 'editor' property."""

    deps = Dependency(mock_external_encoder)
    # It's an absolute path so the value should be the same
    assert deps.editor == mock_external_encoder.param


def test_get_cdparanoia(mock_external_encoder):
    """Get the 'cdparanoia' property."""

    deps = Dependency(mock_external_encoder)
    # It's an absolute path so the value should be the same
    assert deps.cdparanoia == mock_external_encoder.param

def test_verify_action_params(mock_external_encoder):
    """Ensure encoder and post-action parameter verification works."""

    conf = mock_external_encoder
    deps = Dependency(conf)

    # Dict can only have one key
    invalid_input = {'a': [], 'b': []}
    with pytest.raises(DependencyError):
        deps._verify_action_params(invalid_input)

    # Dict mustn't be empty
    invalid_input = {}
    with pytest.raises(DependencyError):
        deps._verify_action_params(invalid_input)

    # Type of encoder param container should be list
    invalid_input = {conf.param: {'ah', 'beh'}}
    with pytest.raises(DependencyError):
        deps._verify_action_params(invalid_input)

    # Type of encoder param items should be str
    invalid_input = {conf.param: [1]}
    with pytest.raises(DependencyError):
        deps._verify_action_params(invalid_input)

    # Test valid
    deps._verify_action_params({'valid': ['totally', 'valid']})

