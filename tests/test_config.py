"""Tests for the config module.

NOTE: If you intend to import Config and monkeypatch the config dir (you
should, to make it work) you need to ensure that you only import Config
inside your test function. Otherwise xdg.XDG_CONFIG_HOME will, in the
automated environment, fail to be evaluated and the tests will crash.
"""
import pytest
import os
import importlib


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
    """Ensure a fake homedir exists.
    """
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


### Tests ###


def test_create_config(mock_temp_home):
    from cdparacord import config
    c = config.Config()


def test_get_lame(mock_temp_home):
    from cdparacord import config
    c = config.Config()
    # Would error if we couldn't find it
    c.get('lame')


def test_fail_to_get_anything(mock_temp_home):
    from cdparacord import config
    c = config.Config()
    with pytest.raises(KeyError):
        c.get('nonextant')


def test_fail_to_create_config_dir(mock_uncreatable_config_dir):
    from cdparacord import config
    with pytest.raises(config.ConfigError):
        c = config.Config()
