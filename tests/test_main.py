"""Tests for the main module."""

import pytest
import click.testing
import io
import cdparacord

@pytest.fixture
def mock_dependencies(monkeypatch):
    class Config:
        def update(self, d):
            pass
    monkeypatch.setattr('cdparacord.main.Config', Config)

    class Dependency:
        def __init__(self, c):
            pass
    monkeypatch.setattr('cdparacord.main.Dependency', Dependency)

    class Albumdata:
        def __init__(self):
            self.track_count = 1
            self.ripdir = '/tmp/oispa-kaljaa'

        @classmethod
        def from_user_input(cls, deps, config):
            return cls()

        @property
        def dict(self):
            return {}
    monkeypatch.setattr('cdparacord.main.Albumdata', Albumdata)

    class Rip:
        def __init__(self, albumdata, deps, config, begin_track, end_track, continue_rip):
            pass

        def rip_pipeline(self):
            pass
    monkeypatch.setattr('cdparacord.main.Rip', Rip)

    monkeypatch.setattr('shutil.rmtree', lambda x: True)
    monkeypatch.setattr('os.makedirs', lambda x, y, exist_ok: True)
    monkeypatch.setattr('builtins.open', lambda *x: io.StringIO('{}'))

    class FakeDisc:
        @property
        def submission_url(self):
            return "fake_url:"

    monkeypatch.setattr('discid.read', lambda *x: FakeDisc())
    monkeypatch.setattr('webbrowser.open', lambda x: True)


def test_main(mock_dependencies):
    """Test several valid inputs to main."""
    from cdparacord import main

    click.testing.CliRunner().invoke(main.main, catch_exceptions=False)
    click.testing.CliRunner().invoke(main.main, args=['1', '1'], catch_exceptions=False)
    click.testing.CliRunner().invoke(main.main, args=['--keep-ripdir'], catch_exceptions=False)


def test_main_submit(mock_dependencies):
    """Test that the submission code path isn't wonky."""
    from cdparacord import main

    click.testing.CliRunner().invoke(
        main.main, args=['--submit'],
        catch_exceptions=False)


def test_main_begin_track_out_of_range(mock_dependencies):
    """Test that several invalid inputs to main raise."""
    from cdparacord import main, error

    # Test several invalid inputs
    with pytest.raises(cdparacord.error.CdparacordError):
        click.testing.CliRunner().invoke(main.main, args=['100'], catch_exceptions=False)

    with pytest.raises(cdparacord.error.CdparacordError):
        click.testing.CliRunner().invoke(main.main, args=['1', '2'], catch_exceptions=False)

    with pytest.raises(cdparacord.error.CdparacordError):
        click.testing.CliRunner().invoke(main.main, args=['1', '0'], catch_exceptions=False)


def test_main_albumdata_none(mock_dependencies, monkeypatch):
    """Test that main completes succesfully when albumdata is None."""
    from cdparacord import main

    monkeypatch.setattr('cdparacord.main.Albumdata.from_user_input', lambda y, z: None)

    res = click.testing.CliRunner().invoke(main.main, catch_exceptions=False)

    assert res.output == 'User aborted albumdata selection.\n'
