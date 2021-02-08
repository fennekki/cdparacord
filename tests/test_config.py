"""Tests for the config module.
"""
import pytest
import os
import importlib
import yaml
import tempfile

from cdparacord import config

### Fixtures ###

@pytest.fixture
def mock_home(monkeypatch):
    """Create a fake HOME and XDG_CONFIG_HOME."""
    with tempfile.TemporaryDirectory(prefix="cdparacord-test-config") as d:
        monkeypatch.setenv("HOME", d)
        monkeypatch.setenv("XDG_CONFIG_HOME", os.path.join(d, ".config"))
        os.makedirs(os.environ["XDG_CONFIG_HOME"], mode=0o700)
        yield os.environ["HOME"]

@pytest.fixture
def mock_config_dir(mock_home):
    """Create a fake config dir."""
    config_dir = os.path.join(os.environ["XDG_CONFIG_HOME"], "cdparacord")
    os.makedirs(config_dir, 0o700)
    yield config_dir

@pytest.fixture
def mock_config(mock_config_dir):
    """Create a fake config file."""
    config_file = os.path.join(mock_config_dir, "config.yaml")
    with open(config_file, "w"):
        pass
    # Make it self-readable only
    os.chmod(config_file, 0o600)
    yield config_file


@pytest.fixture
def mock_uncreatable_config_dir(mock_home):
    """Ensure a config dir cannot be created."""
    # Create unreadable dir
    os.chmod(os.environ["XDG_CONFIG_HOME"], 0o000)
    yield mock_home
    # Make it usable again so we don't error when the cleanup starts
    # deleting these directories
    os.chmod(os.environ["XDG_CONFIG_HOME"], 0o700)


@pytest.fixture
def mock_unreadable_config(mock_config):
    """Ensure the config file cannot be read."""
    # Make config file forbidden to read
    os.chmod(mock_config, 0o000)
    yield mock_config
    # Make the tempfile accessible again
    os.chmod(mock_config, 0o600)

### Tests ###

def test_create_config(mock_home):
    """Try creating configuration dir in an empty home directory."""
    c = config.Config()


def test_get_encoder(mock_home):
    """Try getting the value of 'encoder' from a default configuration."""
    c = config.Config()
    # Would error if we couldn't find it
    c.get('encoder')


def test_fail_to_get_variable(mock_home):
    """Try to fail getting a nonexistent value from defaults."""
    c = config.Config()
    with pytest.raises(KeyError):
        c.get('nonextant')


def test_fail_to_create_config_dir(mock_uncreatable_config_dir):
    """Try to fail to create a configuration directory.

    Specifically, the fixture sets up permissions so we're not allowed
    to create the directory.
    """
    with pytest.raises(config.ConfigError):
        c = config.Config()


def test_read_config_file(mock_config):
    """Try to read a configuration file."""

    config_file = mock_config

    # Setup our expectations
    var_name = 'editor'
    expected_value = 'probably-not-a-real-editor'

    # Write them to the file
    with open(config_file, 'w') as f:
        yaml.safe_dump({var_name: expected_value}, f)

    c = config.Config()
    # We should get the value in the file
    assert c.get(var_name) == expected_value


def test_read_invalid_config(mock_config):
    """Try to fail to read a valid configuration from file."""

    config_file = mock_config

    with open(config_file, 'w') as f:
        yaml.safe_dump(["wrong"], f)

    with pytest.raises(config.ConfigError):
        c = config.Config()


def test_fail_to_open_config_file(mock_unreadable_config):
    """Try to fail to open a configuration file.

    Specifically, the fixture sets up permission so we're not allowed to
    open the file, even though it exists.
    """
    with pytest.raises(config.ConfigError):
        c = config.Config()


def test_update_config_no_unknown_keys(mock_home, capsys):
    c = config.Config()
    c.update({'keep_ripdir': True}, quiet_ignore=False)

    out, err = capsys.readouterr()
    assert err == ""


def test_update_config_unknown_keys(mock_home, capsys):
    c = config.Config()
    c.update({'invalid_key': True}, quiet_ignore=False)

    out, err = capsys.readouterr()
    assert err == 'Warning: Unknown configuration key invalid_key\n'


def test_update_config_with_none(mock_home, capsys):
    c = config.Config()
    c.update({'keep_ripdir': None}, quiet_ignore=False)

    out, err = capsys.readouterr()
    assert err == ""


def test_update_config_quiet_ignore(mock_home, capsys):
    c = config.Config()
    c.update({'invalid_key': True}, quiet_ignore=True)

    out, err = capsys.readouterr()
    assert err == ''


def test_ensure_default_encoder_keys_are_strings(mock_home):
    """Test default encoder configuration."""
    c = config.Config()
    
    assert len(c.get('encoder')) == 1

    for encoder in c.get('encoder'):
        encoder_params = c.get('encoder')[encoder]
        # If it's not a list something's wrong
        assert type(encoder_params) is list

        for item in encoder_params:
            # And the params should be strings
            assert type(item) is str

def test_ensure_default_postaction_keys_are_strings(mock_home):
    """Test default encoder configuration."""
    c = config.Config()

    for post_action in ('post_rip', 'post_encode', 'post_finished'):
        for action in c.get(post_action):
            assert len(action) == 1

            for action_key in action:
                action_params = action[action_key]
                # If it's not a list something's wrong
                assert type(action_params) is list

                for item in action_params:
                    # And the params should be strings
                    assert type(item) is str
