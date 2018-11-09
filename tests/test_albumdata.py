"""Tests for the albumdata module."""

import pytest
import contextlib
import copy
import io
import os
import yaml


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
                    'filename': '/home/user/Music/Test Artist/Test album/01 - Test track.mp3',
                    'tracknumber': 1
                }
            ]
    }

testdata_wrong = copy.deepcopy(testdata)
testdata_wrong['track_count'] = 3
testdata_wrong['tracks'].append({'title': '', 'artist': '', 'filename': ''})
testdata_wrong['discid'] = 'wrong'
testdata_wrong['ripdir'] = 'wrong'


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

@pytest.fixture
def albumdata(monkeypatch):
    monkeypatch.setitem(os.environ, 'HOME', '/home/User/')
    monkeypatch.setitem(os.environ, 'XDG_MUSIC_DIR', '/home/User/Music')
    from cdparacord import albumdata as a
    yield a


def test_cdstub_result(monkeypatch, albumdata):
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


def test_disc_result(monkeypatch, albumdata):
    """Test that disc result is processed correctly."""
    monkeypatch.setattr(
        'musicbrainzngs.get_releases_by_discid',
        lambda x, includes: testdata_disc_result)

    a = albumdata.Albumdata._albumdata_from_musicbrainz('test')[0]

    assert a['title'] == 'Test album'
    assert a['albumartist'] == 'Test Artist'
    assert a['date'] == '2018-01'
    assert a['tracks'][0]['title'] == 'Test track'
    assert a['tracks'][0]['artist'] == 'Test Artist'


def test_musicbrainzerror_result(monkeypatch, albumdata):
    """Test that getting no MusicBrainz result at all works."""
    def fake_get_releases(*x, **y):
        import musicbrainzngs
        raise musicbrainzngs.MusicBrainzError("test")

    monkeypatch.setattr(
        'musicbrainzngs.get_releases_by_discid',
        fake_get_releases)
    a = albumdata.Albumdata._albumdata_from_musicbrainz('test')
    assert a == []


def test_weird_nothing_result(monkeypatch, albumdata):
    """Test a weird implausible MusicBrainz result.

    Specifically, a case where we get neither cdstub nor disc which
    shouldn't happen will hit its own branch that should be treated as
    "no MusicBrainz result".
    """
    monkeypatch.setattr(
        'musicbrainzngs.get_releases_by_discid',
        lambda *x, **y: {})
    a = albumdata.Albumdata._albumdata_from_musicbrainz('test')
    assert a == []


def test_initialise_track(albumdata):
    """Test that track is correctly initialised."""
    t = albumdata.Track(testdata['tracks'][0])
    assert t.title == 'Test track'
    assert t.artist == 'Test Artist'
    assert t.filename == '/home/user/Music/Test Artist/Test album/01 - Test track.mp3'
    assert t.tracknumber == 1


def test_albumdata_tracks(albumdata):
    """Test that tracks are correctly added to albumdata."""
    a = albumdata.Albumdata(testdata)
    assert a.tracks[0].title == 'Test track'
    assert a.albumartist == 'Test Artist'
    assert a.title == 'Test album'
    assert a.date == '2018-01'


def test_initialise_albumdata(albumdata):
    """Try to initialise albumdata correctly."""
    a = albumdata.Albumdata(testdata)
    assert a.ripdir == '/tmp/cdparacord/1000-test'
    assert a.track_count == 1


def test_print_albumdata_80(capsys, monkeypatch, albumdata):
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


def test_print_albumdata_60(capsys, monkeypatch, albumdata):
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

def test_get_track_count(monkeypatch, albumdata):
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

def test_select_albumdata(capsys, monkeypatch, albumdata):
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


def test_previous_result(monkeypatch, albumdata):
    monkeypatch.setattr('os.path.isfile', lambda *x: True)
    monkeypatch.setattr('builtins.open', lambda *x: io.StringIO(yaml.safe_dump(testdata)))

    a = albumdata.Albumdata._albumdata_from_previous_rip('')
    assert a['source'] == 'Previous rip'
    assert a['title'] == testdata['title']
    assert a['albumartist'] == testdata['albumartist']
    assert a['tracks'][0]['title'] == testdata['tracks'][0]['title']


def test_invalid_previous_result(monkeypatch, albumdata):
    monkeypatch.setattr('os.path.isfile', lambda *x: True)
    monkeypatch.setattr('builtins.open', lambda *x: io.StringIO('[]'))

    with pytest.raises(albumdata.AlbumdataError):
        a = albumdata.Albumdata._albumdata_from_previous_rip('')


def test_from_user_input(monkeypatch, albumdata):
    monkeypatch.setattr('discid.read', lambda: 'test')
    monkeypatch.setattr('os.getuid', lambda: 1000)
    monkeypatch.setattr('cdparacord.albumdata.Albumdata._get_track_count', lambda *x: 1)
    monkeypatch.setattr('cdparacord.albumdata.Albumdata._albumdata_from_previous_rip', lambda *x: testdata)
    monkeypatch.setattr('cdparacord.albumdata.Albumdata._albumdata_from_musicbrainz', lambda *x: [])
    monkeypatch.setattr('cdparacord.albumdata.Albumdata._select_albumdata', lambda *x: None)
    monkeypatch.setattr('cdparacord.albumdata.Albumdata._edit_albumdata', lambda *x: None)
    monkeypatch.setattr('cdparacord.albumdata.Albumdata._generate_filename', lambda *x: 'file')

    class FakeDeps:
        @property
        def cdparanoia(self):
            pass

        def editor(self):
            pass

    class FakeConfig:
        def __init__(self):
            self.dict = {'use_musicbrainz': True, 'reuse_albumdata': True }

        def get(self, a):
            return self.dict[a]

    deps = FakeDeps()
    config = FakeConfig()
    assert albumdata.Albumdata.from_user_input(deps, config) is None
    
    monkeypatch.setitem(testdata, 'tracks', [])
    config.dict['use_musicbrainz'] = False
    config.dict['reuse_albumdata'] = True
    assert albumdata.Albumdata.from_user_input(deps, config) is None

    config.dict['use_musicbrainz'] = True
    config.dict['reuse_albumdata'] = False
    assert albumdata.Albumdata.from_user_input(deps, config) is None

    config.dict['use_musicbrainz'] = False
    config.dict['reuse_albumdata'] = False
    assert albumdata.Albumdata.from_user_input(deps, config) is None


def test_edit_albumdata(monkeypatch, albumdata):
    """Test _edit_albumdata."""
    @contextlib.contextmanager
    def fake_tempfile(*x, **y):
        class FakeTempfile:
            def flush(*x):
                pass

            def seek(*x):
                pass

            @property
            def name(*x):
                pass
        yield FakeTempfile()

    monkeypatch.setattr('tempfile.NamedTemporaryFile', fake_tempfile)
    monkeypatch.setattr('subprocess.run', lambda *x, **y: None)
    monkeypatch.setattr('yaml.safe_dump', lambda *x, **y: None)
    monkeypatch.setattr('yaml.safe_load', lambda *x, **y: testdata)
    monkeypatch.setattr('cdparacord.albumdata.Albumdata._generate_filename', lambda *x, **y: '')

    # Test with input None
    albumdata.Albumdata._edit_albumdata(None, 1, '', None)
    
    # Succesful edit & save
    seq = (i for i in ('e\n', 's\n'))
    monkeypatch.setattr('builtins.input', lambda *x: next(seq))
    albumdata.Albumdata._edit_albumdata(testdata, 1, '', None)

    # Succesful regen and rip
    seq = (i for i in ('f\n', 'r\n', 'n\n', 'r\n', 'y\n'))
    monkeypatch.setattr('builtins.input', lambda *x: next(seq))
    albumdata.Albumdata._edit_albumdata(testdata, 1, '', None)

    # Unsuccesful edit and abandon (all things wrong in edit)
    monkeypatch.setattr('yaml.safe_load', lambda *x, **y: testdata_wrong)
    seq = (i for i in ('e\n', 'a\n'))
    monkeypatch.setattr('builtins.input', lambda *x: next(seq))
    albumdata.Albumdata._edit_albumdata(testdata, 1, '', None)


def test_generate_filename(monkeypatch, albumdata):
    """Test generating filenames with various filters."""
    class FakeConfig:
        def __init__(self):
            self.dict = {'safetyfilter': 'ascii', 'target_template': '$track'}

        def get(self, a):
            return self.dict[a]

    config = FakeConfig()
    monkeypatch.setitem(testdata['tracks'][0], 'title', '!äbc/de')
    config.dict['safetyfilter'] = 'ascii'
    assert '!bc-de' == albumdata.Albumdata._generate_filename(testdata, testdata['tracks'][0], 1, config)
    config.dict['safetyfilter'] = 'windows1252'
    assert '!äbc-de' == albumdata.Albumdata._generate_filename(testdata, testdata['tracks'][0], 1, config)
    config.dict['safetyfilter'] = 'unicode_letternumber'
    assert 'äbcde' == albumdata.Albumdata._generate_filename(testdata, testdata['tracks'][0], 1, config)

    # Test that it fails when we given an invalid filter
    config.dict['safetyfilter'] = 'fake and not real'
    with pytest.raises(albumdata.AlbumdataError):
        albumdata.Albumdata._generate_filename(testdata, testdata['tracks'][0], 1, config)

def test_disc_result_no_date(monkeypatch, albumdata):
    """Test that disc result is processed even when lacking date."""
    monkeypatch.setattr('musicbrainzngs.get_releases_by_discid',
        lambda x, includes: testdata_disc_result)

    # Delete date, should still work
    monkeypatch.delitem(testdata_disc_result['disc']['release-list'][0], 'date')

    a = albumdata.Albumdata._albumdata_from_musicbrainz('test')[0]

    assert a['date'] == ''
