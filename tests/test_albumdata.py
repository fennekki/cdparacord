"""Tests for the albumdata module."""

import pytest
import copy
import io
import yaml
from cdparacord import albumdata


testdata = {
        'discid': 'test',
        'source': 'Test data',
        'ripdir': '/tmp/cdparacord/1000-test',
        'title': 'Test album',
        'albumartist': 'Test Artist',
        'date': '2018-01',
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


testdata_cdstub_result = {
    'cdstub': {
        'track-list': [
            {
                'track_or_recording_length': '1000',
                'length': '1000',
                'title': 'Test track'
            }
        ],
        'barcode': '123456789',
        'artist': 'Test Artist',
        'track-count': 1,
        'id': 'test',
        'title': 'Test album'
    }
}

testdata_disc_result = {
    'disc':{
        'offset-list':[
            150,
        ],
        'release-count':1,
        'release-list':[
            {
                'medium-count':1,
                'artist-credit':[
                    {
                        'artist':{
                            'name':'Test Artist',
                            'id':'invalid id',
                            'sort-name':'Test Artist'
                        }
                    }
                ],
                'barcode':'123456789',
                'date':'2018-01',
                'country':'FI',
                'release-event-list':[
                    {
                        'date':'2018-01',
                        'area':{
                            'name':'Finland',
                            'id':'invalid id',
                            'iso-3166-1-code-list':[
                                'FI'
                            ],
                            'sort-name':'Finland'
                        }
                    }
                ],
                'artist-credit-phrase':'Test Artist',
                'title':'Test album',
                'status':'Official',
                'medium-list':[
                    {
                        'track-list':[
                            {
                                'artist-credit':[
                                    {
                                        'artist':{
                                            'name':'Test Artist',
                                            'id':'invalid id',
                                            'sort-name':'Test Artist'
                                        }
                                    }
                                ],
                                'number':'1',
                                'recording':{
                                    'length':'1000',
                                    'id':'invalid id',
                                    'artist-credit-phrase':'Test Artist',
                                    'title':'Test track',
                                    'artist-credit':[
                                        {
                                            'artist':{
                                                'name':'Test Artist',
                                                'id':'invalid id',
                                                'sort-name':'Test Artist'
                                            }
                                        }
                                    ]
                                },
                                'length':'1000',
                                'id':'invalid id',
                                'track_or_recording_length':'1000',
                                'position':'1',
                                'artist-credit-phrase':'Test Artist'
                            }
                        ],
                        'track-count':1,
                        'format':'CD',
                        'disc-list':[
                            {
                                'id':'test',
                                'offset-list':[
                                    150,
                                ],
                                'sectors':'1150',
                                'offset-count':1
                            }
                        ],
                        'disc-count':1,
                        'position':'1'
                    }
                ],
                'id':'invalid id',
                'text-representation':{
                    'language':'fin',
                    'script':'Latn'
                },
                'cover-art-archive':{
                    'artwork':'false',
                    'count':'0',
                    'front':'false',
                    'back':'false'
                },
                'release-event-count':1,
                'quality':'normal'
            }
        ],
        'id':'invalid id',
        'sectors':'1150',
        'offset-count':1
    }
}


def test_cdstub_result(monkeypatch):
    """Test that cdstub result is processed correctly."""
    # Exercise both paths
    monkeypatch.setattr('musicbrainzngs.get_releases_by_discid',
        lambda x, includes: testdata_cdstub_result)

    a = albumdata.Albumdata._albumdata_from_musicbrainz('test')[0]
    assert a['title'] == 'Test album'
    assert a['albumartist'] == 'Test Artist'
    assert a['tracks'][0]['title'] == 'Test track'
    assert a['tracks'][0]['artist'] == 'Test Artist'

    monkeypatch.setitem(testdata_cdstub_result['cdstub'], 'date', '2018-02')
    a = albumdata.Albumdata._albumdata_from_musicbrainz('test')[0]

    assert a['title'] == 'Test album'
    assert a['albumartist'] == 'Test Artist'
    assert a['date'] == '2018-02'
    assert a['tracks'][0]['title'] == 'Test track'
    assert a['tracks'][0]['artist'] == 'Test Artist'


def test_disc_result(monkeypatch):
    """Test that disc result is processed correctly."""
    monkeypatch.setattr('musicbrainzngs.get_releases_by_discid',
        lambda x, includes: testdata_disc_result)

    a = albumdata.Albumdata._albumdata_from_musicbrainz('test')[0]

    assert a['title'] == 'Test album'
    assert a['albumartist'] == 'Test Artist'
    assert a['date'] == '2018-01'
    assert a['tracks'][0]['title'] == 'Test track'
    assert a['tracks'][0]['artist'] == 'Test Artist'


def test_initialise_track():
    """Test that track is correctly initialised."""
    t = albumdata.Track(testdata['tracks'][0])
    assert t.title == 'Test track'
    assert t.artist == 'Test Artist'
    assert t.filename == '/home/user/Music/Test Artist/Test album/01 - Test track.mp3'


def test_albumdata_tracks():
    """Test that tracks are correctly added to albumdata."""
    a = albumdata.Albumdata(testdata)
    assert a.tracks[0].title == 'Test track'


def test_initialise_albumdata():
    """Try to initialise albumdata correctly."""
    a = albumdata.Albumdata(testdata)
    assert a.ripdir == '/tmp/cdparacord/1000-test'
    assert a.track_count == 1


def test_print_albumdata_80(capsys, monkeypatch):
    """Try to print albumdata to width 80 correctly."""
    expected = """\
================================================================================
Test Artist         Test album           test                                   
================================================================================
Track               Track Artist         Suggested filename                     
--------------------------------------------------------------------------------
Test track          Test Artist          /home/user/Music/Test Artist/Test [...]
--------------------------------------------------------------------------------
"""

    monkeypatch.setattr('shutil.get_terminal_size',
        lambda: (80, 24))

    albumdata.Albumdata._print_albumdata(testdata)
    out, err = capsys.readouterr()

    assert out == expected


def test_print_albumdata_60(capsys, monkeypatch):
    """Try to print albumdata to width 60 correctly."""
    expected = """\
============================================================
Test Artist                    Test album                   
============================================================
Track                          Track Artist                 
------------------------------------------------------------
Test track                     Test Artist                  
------------------------------------------------------------
"""

    monkeypatch.setattr('shutil.get_terminal_size',
        lambda: (60, 24))

    albumdata.Albumdata._print_albumdata(testdata)
    out, err = capsys.readouterr()

    assert out == expected

def test_get_track_count(monkeypatch):
    """Test track count getting with a fake cdparanoia output."""
    testdata = """\
cdparanoia III release 10.2 (September 11, 2008)


Table of contents (audio tracks only):
track        length               begin        copy pre ch
===========================================================
  1.    1000 [00:10.00]        150 [00:01.50]    no   no  2
TOTAL   1150 [00:11.50]        (audio only)
"""
    class FakeProcess:
        def check_returncode(self):
            pass
        
        @property
        def stdout(self):
            return testdata

    obj = FakeProcess()
    monkeypatch.setattr('subprocess.run', lambda *x, **y: obj)
    assert albumdata.Albumdata._get_track_count('') == 1

def test_select_albumdata(capsys, monkeypatch):
    """Test that the albumdata selection works as expected.

    The expected data is rather massive and needs to be updated
    regularly but this works as effectively a regression test in that
    regard. Maybe.
    """
    input_sequence = []
    expected = []
    input_sequence.append(('n\n', 'n\n', '0\n', 'c\n', 'n\n', 'c\n'))
    expected.append("""\
============================================================
Albumdata sources available:
1) Test data
============================================================
0: return to listing
1-1: select source
n: show next source:
c: choose current source
a: abort

> Source 1: Test data
============================================================
Test Artist                    Test album                   
============================================================
Track                          Track Artist                 
------------------------------------------------------------
Test track                     Test Artist                  
------------------------------------------------------------
0: return to listing
1-1: select source
n: show next source:
c: choose current source
a: abort

> All sources viewed, returning to listing
============================================================
Albumdata sources available:
1) Test data
============================================================
0: return to listing
1-1: select source
n: show next source:
c: choose current source
a: abort

> ============================================================
Albumdata sources available:
1) Test data
============================================================
0: return to listing
1-1: select source
n: show next source:
c: choose current source
a: abort

> You can only choose current source when looking at a source
============================================================
Albumdata sources available:
1) Test data
============================================================
0: return to listing
1-1: select source
n: show next source:
c: choose current source
a: abort

> Source 1: Test data
============================================================
Test Artist                    Test album                   
============================================================
Track                          Track Artist                 
------------------------------------------------------------
Test track                     Test Artist                  
------------------------------------------------------------
0: return to listing
1-1: select source
n: show next source:
c: choose current source
a: abort

> """)
    input_sequence.append(('11\n', '1\n'))
    expected.append("""\
============================================================
Albumdata sources available:
1) Test data
============================================================
0: return to listing
1-1: select source
n: show next source:
c: choose current source
a: abort

> Source number must be between 1 and 1
============================================================
Albumdata sources available:
1) Test data
============================================================
0: return to listing
1-1: select source
n: show next source:
c: choose current source
a: abort

> """)
    input_sequence.append(('tööt\n', 'a\n'))
    expected.append("""\
============================================================
Albumdata sources available:
1) Test data
============================================================
0: return to listing
1-1: select source
n: show next source:
c: choose current source
a: abort

> Invalid command: tööt
============================================================
Albumdata sources available:
1) Test data
============================================================
0: return to listing
1-1: select source
n: show next source:
c: choose current source
a: abort

> """)

    monkeypatch.setattr('shutil.get_terminal_size',
        lambda: (60, 24))

    for test_index in range(len(input_sequence)):
        fake_input_generator = (i for i in input_sequence[test_index])
        def fake_input(prompt):
            print(prompt, end='')
            try:
                return next(fake_input_generator)
            except StopIteration:
                return 
        monkeypatch.setattr('builtins.input', fake_input)
        albumdata.Albumdata._select_albumdata([testdata], 1)
        out, err = capsys.readouterr()

        assert out == expected[test_index]


def test_previous_result(monkeypatch):
    monkeypatch.setattr('os.path.isfile', lambda *x: True)
    monkeypatch.setattr('builtins.open', lambda *x: io.StringIO(yaml.safe_dump(testdata)))

    a = albumdata.Albumdata._albumdata_from_previous_rip('')
    assert a['source'] == 'Previous rip'
    assert a['title'] == testdata['title']
    assert a['albumartist'] == testdata['albumartist']
    assert a['tracks'][0]['title'] == testdata['tracks'][0]['title']


def test_invalid_previous_result(monkeypatch):
    monkeypatch.setattr('os.path.isfile', lambda *x: True)
    monkeypatch.setattr('builtins.open', lambda *x: io.StringIO('[]'))

    with pytest.raises(albumdata.AlbumdataError):
        a = albumdata.Albumdata._albumdata_from_previous_rip('')
