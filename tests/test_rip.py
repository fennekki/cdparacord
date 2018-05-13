import pytest
import asyncio
from cdparacord import rip

def test_construct_rip(monkeypatch):
    """Test constructing Rip object."""
    rip.Rip(None, None, None, 1, 1, True)

def test_rip_pipeline(monkeypatch):
    """Test constructing Rip and running first pipeline function."""
    class FakeTrack:
        @property
        def tracknumber(self):
            return 1

    class FakeAlbumdata:
        @property
        def tracks(self):
            return [FakeTrack()]

        @property
        def ripdir(self):
            return '/tmp/oispa-kaljaa'

    class FakeDeps:
        ...

    class FakeConfig:
        def get(self, key):
            if key in ('post_rip', 'post_encode'):
                return [{'echo': ['${one_file}']}]
            elif key == 'post_finished':
                return [{'echo': ['${one_file}', '${all_files}']}]
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

    r = rip.Rip(FakeAlbumdata(), FakeDeps(), FakeConfig(), 1, 1, True)

    # Use isfile to cover both paths 
    asyncio.set_event_loop(asyncio.new_event_loop())
    monkeypatch.setattr('os.path.isfile', lambda x: True)
    r.rip_pipeline()

    asyncio.set_event_loop(asyncio.new_event_loop())
    monkeypatch.setattr('os.path.isfile', lambda x: True)
    r.rip_pipeline()
