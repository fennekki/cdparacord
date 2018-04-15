"""Tests for the main module."""

import pytest
import click.testing
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
        def __init__(self, deps, config):
            self.track_count = 1
            self.ripdir = '/\0'
    monkeypatch.setattr('cdparacord.main.Albumdata', Albumdata)

    class Rip:
        def __init__(self, albumdata, deps, config, begin_track, end_track, continue_rip):
            pass

        def rip_pipeline(self):
            pass
    monkeypatch.setattr('cdparacord.main.Rip', Rip)

    monkeypatch.setattr('shutil.rmtree', lambda x: True)


def test_main(mock_dependencies):
    from cdparacord import main
    # Test several valid inputs
    click.testing.CliRunner().invoke(main.main, catch_exceptions=False)
    click.testing.CliRunner().invoke(main.main, args=['1', '1'], catch_exceptions=False)
    click.testing.CliRunner().invoke(main.main, args=['--keep-ripdir'], catch_exceptions=False)


def test_main_begin_track_out_of_range(mock_dependencies):
    from cdparacord import main, error

    # Test several invalid inputs
    with pytest.raises(cdparacord.error.CdparacordError):
        click.testing.CliRunner().invoke(main.main, args=['100'], catch_exceptions=False)

    with pytest.raises(cdparacord.error.CdparacordError):
        click.testing.CliRunner().invoke(main.main, args=['1', '2'], catch_exceptions=False)

    with pytest.raises(cdparacord.error.CdparacordError):
        click.testing.CliRunner().invoke(main.main, args=['1', '0'], catch_exceptions=False)
