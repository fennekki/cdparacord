import pytest
import asyncio
from cdparacord import rip

def test_construct_rip(monkeypatch):
    """Test constructing Rip object."""
    rip.Rip(None, None, None, 1, 1, True)

def test_rip_pipeline(monkeypatch):
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

    class FakeConfig:
        def __init__(self):
            self.fail_post_finished_one = False
            self.fail_post_finished_all = False

        def get(self, key):
            if key in ('post_rip', 'post_encode'):
                return [{'echo': ['${one_file}']}]
            elif key == 'post_finished':
                if self.fail_post_finished_one:
                    return [{'false': ['${one_file}']}]
                elif self.fail_post_finished_all:
                    return [{'false': ['${all_files}']}]
                else:
                    return [{'echo': ['${one_file}', '${all_files}']},{'echo': ['$all_files']}]
            elif key == 'encoder':
                return {'echo': ['${one_file}', '${out_file}']}
            else:
                return ''

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

    fake_config = FakeConfig()
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
    fake_config.fail_post_finished_one = True
    fake_config.fail_post_finished_all = True
    asyncio.set_event_loop(asyncio.new_event_loop())
    with pytest.raises(rip.RipError):
        r.rip_pipeline()
    asyncio.get_event_loop().close()
    fake_config.fail_post_finished_one = False
    # Test the other fail
    asyncio.set_event_loop(asyncio.new_event_loop())
    with pytest.raises(rip.RipError):
        r.rip_pipeline()
    asyncio.get_event_loop().close()
    fake_config.fail_post_finished_all = False

    # Track number past the range (and as such: empty ripped tracks)
    fake_track.tracknumber = 2
    asyncio.set_event_loop(asyncio.new_event_loop())
    r.rip_pipeline()
    fake_track.tracknumber = 1
