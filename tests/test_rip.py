import pytest
import asyncio
from cdparacord import rip

@pytest.fixture
def get_fake_config():
    class FakeConfig:
        def __init__(self):
            self.fail_one = False
            self.fail_all = False
            self.always_tag_albumartist = False

        def get(self, key):
            if key in ('post_rip', 'post_encode'):
                if self.fail_one:
                    return [{'false': ['${one_file}']}]
                else:
                    return [{'echo': ['${one_file}']}]
            elif key == 'post_finished':
                if self.fail_one:
                    return [{'false': ['${one_file}']}]
                elif self.fail_all:
                    return [{'false': ['${all_files}']}]
                else:
                    return [{'echo': ['${one_file}', '${all_files}']},{'echo': ['$all_files']}]
            elif key == 'encoder':
                if self.fail_one:
                    return {'false': ['${one_file}', '${out_file}']}
                else:
                    return {'echo': ['${one_file}', '${out_file}']}
            elif key == 'always_tag_albumartist':
                return self.always_tag_albumartist
            else:
                return ''
    yield FakeConfig

def test_construct_rip(monkeypatch):
    """Test constructing Rip object."""
    rip.Rip(None, None, None, 1, 1, True)

def test_rip_pipeline(monkeypatch, get_fake_config):
    """Test constructing Rip and running first pipeline function."""
    class FakeTrack:
        def __init__(self):
            self.tracknumber = 1

        @property
        def filename(self):
            return '/tmp/oispa-kaljaa/final/test.mp3'

    fake_track = FakeTrack()

    class FakeAlbumdata:
        @property
        def tracks(self):
            return [fake_track]

        @property
        def ripdir(self):
            return '/tmp/oispa-kaljaa'

    class FakeDeps:
        ...

    async def fake_rip(self, track):
        await fake_encode(self, track, track.filename)

    async def fake_encode(self, track, filename):
        await fake_tag(self, track, filename)

    async def fake_tag(self, track, filename):
        self._tagged_files[filename] = filename

    monkeypatch.setattr('cdparacord.rip.Rip._rip_track', fake_rip)
    monkeypatch.setattr('cdparacord.rip.Rip._encode_track', fake_encode)
    monkeypatch.setattr('os.makedirs', lambda x, exist_ok: None)
    monkeypatch.setattr('shutil.copy2', lambda x, y: True)

    fake_config = get_fake_config()
    r = rip.Rip(FakeAlbumdata(), FakeDeps(), fake_config, 1, 1, True)

    # Use isfile to cover both paths
    asyncio.set_event_loop(asyncio.new_event_loop())
    monkeypatch.setattr('os.path.isfile', lambda x: True)
    r.rip_pipeline()

    # This one will schedule a rip, not an encode
    asyncio.set_event_loop(asyncio.new_event_loop())
    monkeypatch.setattr('os.path.isfile', lambda x: False)
    r.rip_pipeline()

    # Make the post_rip tasks fail
    fake_config.fail_one = True
    fake_config.fail_all = True
    asyncio.set_event_loop(asyncio.new_event_loop())
    with pytest.raises(rip.RipError):
        r.rip_pipeline()
    asyncio.get_event_loop().close()
    fake_config.fail_one = False
    # Test the other fail
    asyncio.set_event_loop(asyncio.new_event_loop())
    with pytest.raises(rip.RipError):
        r.rip_pipeline()
    asyncio.get_event_loop().close()
    fake_config.fail_all = False

    # Track number past the range (and as such: empty ripped tracks)
    fake_track.tracknumber = 2
    asyncio.set_event_loop(asyncio.new_event_loop())
    r.rip_pipeline()
    fake_track.tracknumber = 1


def test_rip_track(monkeypatch, get_fake_config):
    class FakeTrack:
        def __init__(self):
            self.tracknumber = 1

        @property
        def filename(self):
            return '/tmp/oispa-kaljaa/final/test.mp3'

    fake_track = FakeTrack()

    class FakeAlbumdata:
        @property
        def tracks(self):
            return [fake_track]

        @property
        def ripdir(self):
            return '/tmp/oispa-kaljaa'

    class FakeDeps:
        def __init__(self):
            self.cdparanoia = 'echo'

    fake_config = get_fake_config()
    fake_deps = FakeDeps()
    r = rip.Rip(FakeAlbumdata(), fake_deps, fake_config, 1, 1, True)

    async def fake_encode(self, track, filename):
        ...

    monkeypatch.setattr('cdparacord.rip.Rip._encode_track', fake_encode)
    monkeypatch.setattr('os.rename', lambda x, y: True)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(r._rip_track(fake_track))
    loop.close()

    # Fail ripping track
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    fake_deps.cdparanoia = 'false'
    with pytest.raises(rip.RipError):
        loop.run_until_complete(r._rip_track(fake_track))
    fake_deps.cdparanoia = 'echo'
    loop.close()


    # Fail running post-rip task
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    fake_config.fail_one = True
    with pytest.raises(rip.RipError):
        loop.run_until_complete(r._rip_track(fake_track))
    fake_config.fail_one = False
    loop.close()


def test_encode_track(monkeypatch, get_fake_config):
    class FakeTrack:
        def __init__(self):
            self.tracknumber = 1

        @property
        def filename(self):
            return '/tmp/oispa-kaljaa/final/test.mp3'

    fake_track = FakeTrack()

    class FakeAlbumdata:
        @property
        def tracks(self):
            return [fake_track]

        @property
        def ripdir(self):
            return '/tmp/oispa-kaljaa'

    class FakeDeps:
        def __init__(self):
            self.encoder = 'echo'

    fake_config = get_fake_config()
    fake_deps = FakeDeps()
    r = rip.Rip(FakeAlbumdata(), fake_deps, fake_config, 1, 1, True)

    async def fake_tag(self, track, filename):
        ...

    monkeypatch.setattr('cdparacord.rip.Rip._tag_track', fake_tag)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(r._encode_track(fake_track, fake_track.filename))
    loop.close()

    # Fail ripping track
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    fake_deps.encoder = 'false'
    with pytest.raises(rip.RipError):
        loop.run_until_complete(r._encode_track(fake_track, fake_track.filename))
    fake_deps.encoder = 'echo'
    loop.close()


    # Fail running post-encode task
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    fake_config.fail_one = True
    with pytest.raises(rip.RipError):
        loop.run_until_complete(r._encode_track(fake_track, fake_track.filename))
    fake_deps.encoder = 'echo'
    fake_config.fail_one = False
    loop.close()


def test_tag_track(monkeypatch, get_fake_config):
    class FakeTrack:
        def __init__(self):
            self.tracknumber = 1
            self.artist = 'test'
            self.title = 'test'

        @property
        def filename(self):
            return '/tmp/oispa-kaljaa/final/test.mp3'

    fake_track = FakeTrack()

    class FakeAlbumdata:
        @property
        def tracks(self):
            return [fake_track]

        @property
        def ripdir(self):
            return '/tmp/oispa-kaljaa'

        @property
        def albumartist(self):
            return 'test'

        @property
        def multiartist(self):
            return False

        @property
        def title(self):
            return 'test'

        @property
        def date(self):
            return '2018'

    class FakeDeps:
        def __init__(self):
            self.encoder = 'echo'

    fake_config = get_fake_config()
    fake_deps = FakeDeps()
    r = rip.Rip(FakeAlbumdata(), fake_deps, fake_config, 1, 1, True)

    class FakeFile:
        def __init__(*a, **b):
            ...

        def add_tags(self):
            ...

        def __setitem__(self, key, value):
            ...

        def __getitem__(self, key):
            ...

        def save(self):
            ...

    class FakeFile2(FakeFile):
        def __init__(*a, **b):
            import mutagen
            raise mutagen.MutagenError('something')

    monkeypatch.setattr('mutagen.easyid3.EasyID3', FakeFile2)
    monkeypatch.setattr('mutagen.File', FakeFile)

    # Both skip and don't skip the albumartist branch
    for always_tag in (True, False):
        fake_config.always_tag_albumartist = always_tag
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(r._tag_track(fake_track, fake_track.filename))
        loop.close()

        # Assert we got the filename put in the dict
        assert r._tagged_files[fake_track.filename] == fake_track.filename
