"""Tests for the config module.

NOTE: If you intend to import Config and monkeypatch the config dir (you
should, to make it work) you need to ensure that you only import Config
inside your test function. Otherwise xdg.XDG_CONFIG_HOME will, in the
automated environment, fail to be evaluated and the tests will crash.
"""
import pytest
import os
import importlib
import yaml


# TODO: Instead of this mess, try to mock the entire xdg module. Its
# problem is currently that all the code runs module-scope. Changing the
# xdg module could work too.

### Fixtures ###


@pytest.fixture
def _config_reload_yield_home(_monkeypatch_environment):
    """Reload the config module for testing and yield $HOME.

    This uses the _monkeypatch_environment fixture to ensure that $HOME
    is monkeypatched before we get into any of this.
    """
    # Important to reload xdg before config, so the changes in xdg
    # propagate
    import cdparacord.xdg
    import cdparacord.config
    importlib.reload(cdparacord.xdg)
    importlib.reload(cdparacord.config)
    yield _monkeypatch_environment


@pytest.fixture
def mock_temp_home(_config_reload_yield_home):
    """Ensure a fake homedir exists."""
    yield _config_reload_yield_home


@pytest.fixture
def mock_uncreatable_config_dir(_config_reload_yield_home):
    """Ensure a config dir cannot be created.

    This involves creating an XDG_CONFIG_HOME that cannot be written to.
    """
    from cdparacord import xdg
    # Create unreadable dir
    os.mkdir(xdg.XDG_CONFIG_HOME, 0o000)
    yield _config_reload_yield_home
    # Make it usable again so we don't error when the cleanup starts
    # deleting these directories
    os.chmod(xdg.XDG_CONFIG_HOME, 0o700)


@pytest.fixture
def _create_config_file_paths(_config_reload_yield_home):
    """Yield the configuration file path.

    TODO: Some way of keeping sync with the config filename in Config in
    case it changes?
    """
    from cdparacord import xdg
    config_dir = os.path.join(xdg.XDG_CONFIG_HOME, 'cdparacord')
    config_file = os.path.join(config_dir, 'config.yaml')
    os.makedirs(config_dir)
    # Open and close the file, creating it
    os.close(os.open(config_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL))
    yield (config_dir, config_file)


@pytest.fixture
def mock_config_file(_create_config_file_paths):
    """Ensure the config file can be read."""
    config_dir, config_file = _create_config_file_paths
    yield config_file


@pytest.fixture
def mock_unreadable_config_file(_create_config_file_paths):
    """Ensure the config file cannot be read."""
    config_dir, config_file = _create_config_file_paths
    # Make config file forbidden to read
    os.chmod(config_file, 0o000)
    yield config_file
    # Make the tempfile accessible again
    os.chmod(config_file, 0o600)


### Tests ###


def test_create_config(mock_temp_home):
    """Try creating configuration dir in an empty home directory."""
    from cdparacord import config
    c = config.Config()


def test_get_encoder(mock_temp_home):
    """Try getting the value of 'encoder' from a default configuration."""
    from cdparacord import config
    c = config.Config()
    # Would error if we couldn't find it
    c.get('encoder')


def test_fail_to_get_variable(mock_temp_home):
    """Try to fail getting a nonexistent value from defaults."""
    from cdparacord import config
    c = config.Config()
    with pytest.raises(KeyError):
        c.get('nonextant')


def test_fail_to_create_config_dir(mock_uncreatable_config_dir):
    """Try to fail to create a configuration directory.

    Specifically, the fixture sets up permissions so we're not allowed
    to create the directory.
    """
    from cdparacord import config
    with pytest.raises(config.ConfigError):
        c = config.Config()


def test_read_config_file(mock_config_file):
    """Try to read a configuration file."""
    from cdparacord import config

    config_file = mock_config_file

    # Setup our expectations
    var_name = 'editor'
    expected_value = 'probably-not-a-real-editor'

    # Write them to the file
    with open(config_file, 'w') as f:
        yaml.safe_dump({var_name: expected_value}, f)

    c = config.Config()
    # We should get the value in the file
    assert c.get(var_name) == expected_value


def test_read_invalid_config(mock_config_file):
    """Try to fail to read a valid configuration from file."""
    from cdparacord import config

    config_file = mock_config_file

    with open(config_file, 'w') as f:
        yaml.safe_dump(["wrong"], f)

    with pytest.raises(config.ConfigError):
        c = config.Config()


def test_fail_to_open_config_file(mock_unreadable_config_file):
    """Try to fail to open a configuration file.

    Specifically, the fixture sets up permission so we're not allowed to
    open the file, even though it exists.
    """
    from cdparacord import config
    with pytest.raises(config.ConfigError):
        c = config.Config()


def test_update_config_no_unknown_keys(mock_temp_home, capsys):
    from cdparacord import config

    c = config.Config()
    c.update({'keep_ripdir': True}, quiet_ignore=False)

    out, err = capsys.readouterr()
    assert err == ""


def test_update_config_unknown_keys(mock_temp_home, capsys):
    from cdparacord import config

    c = config.Config()
    c.update({'invalid_key': True}, quiet_ignore=False)

    out, err = capsys.readouterr()
    assert err == 'Warning: Unknown configuration key invalid_key\n'


def test_update_config_with_none(mock_temp_home, capsys):
    from cdparacord import config

    c = config.Config()
    c.update({'keep_ripdir': None}, quiet_ignore=False)

    out, err = capsys.readouterr()
    assert err == ""


def test_update_config_quiet_ignore(mock_temp_home, capsys):
    from cdparacord import config

    c = config.Config()
    c.update({'invalid_key': True}, quiet_ignore=True)

    out, err = capsys.readouterr()
    assert err == ''


def test_ensure_default_encoder_keys_are_strings(mock_temp_home):
    """Test default encoder configuration."""
    from cdparacord import config

    c = config.Config()
    
    assert len(c.get('encoder')) == 1

    for encoder in c.get('encoder'):
        encoder_params = c.get('encoder')[encoder]
        # If it's not a list something's wrong
        assert type(encoder_params) is list

        for item in encoder_params:
            # And the params should be strings
            assert type(item) is str

def test_ensure_default_postaction_keys_are_strings(mock_temp_home):
    """Test default encoder configuration."""
    from cdparacord import config

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
