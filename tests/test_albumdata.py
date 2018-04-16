"""Tests for the albumdata module."""

import pytest
import copy
from cdparacord import albumdata


testdata = {
        'discid': 'test',
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
