"""Tests for the albumdata module."""

import pytest
import copy
from cdparacord import albumdata


testdata = {
        'discid': 'test',
        'title': 'Test album',
        'albumartist': 'Test Artist',
        'date': 2018,
        'tracks': [
                {
                    'title': 'Test track',
                    'artist': 'Test Artist',
                    'filename': '/home/user/Music/Test Artist/Test album/01 - Test track.mp3'
                }
            ]
    }

testdata_wrong = copy.deepcopy(testdata)
testdata_wrong['track_count'] = 2


def test_initialise_track():
    t = albumdata.Track(testdata['tracks'][0])
    assert t.title == 'Test track'
    assert t.artist == 'Test Artist'


def test_initialise_albumdata(monkeypatch):
    """Try to initialise albumdata correctly."""
    monkeypatch.setattr('os.getuid', lambda: 1000)
    a = albumdata.Albumdata(testdata)
    assert a.ripdir == '/tmp/cdparacord/1000-test'
    assert a.track_count == 1


def test_print_albumdata_80(capsys):
    """Try to print albumdata to width 80 correctly."""
    expected = """\
================================================================================
Test Artist                              Test album                             
================================================================================
Track               Track Artist         Suggested filename                     
--------------------------------------------------------------------------------
Test track          Test Artist          /home/user/Music/Test Artist/Test [...]
--------------------------------------------------------------------------------
"""

    albumdata.Albumdata._print_albumdata(testdata, 80)
    out, err = capsys.readouterr()

    assert out == expected


def test_print_albumdata_60(capsys):
    """Try to print albumdata to width 60 correctly."""
    expected = """\
============================================================
Test Artist                    Test album                   
============================================================
Track          Track Artist    Suggested filename           
------------------------------------------------------------
Test track     Test Artist     /home/user/Music/Test [...]  
------------------------------------------------------------
"""

    albumdata.Albumdata._print_albumdata(testdata, 60)
    out, err = capsys.readouterr()

    assert out == expected
