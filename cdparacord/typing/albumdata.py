from mypy_extensions import TypedDict
from typing import (
    List,
)


class RequiredTrackDict(TypedDict):
    title: str
    artist: str

class TrackDict(RequiredTrackDict, total=False):
    filename: str
    tracknumber: int

class AlbumdataDict(TypedDict):
    source: str
    title: str
    date: str
    albumartist: str
    tracks: List[TrackDict]
    cd_number: int
    cd_count: int

class AugmentedAlbumdataDict(AlbumdataDict, total=False):
    discid: str
    ripdir: str
