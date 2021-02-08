from mypy_extensions import TypedDict
from typing import (
    List,
)


_CDStubTrack = TypedDict("_CDStubTrack", {
    "track_or_recording_length": str,
    "length": str,
    "title": str,
})

_InnerCDStub = TypedDict("_InnerCDStub", {
    "track-list": List[_CDStubTrack],
    "barcode": str,
    "artist": str,
    "track-count": int,
    "id": str,
    "title": str,
    "date": str
}, total=False)

_CDStub = TypedDict("_CDStub", {
    "cdstub": _InnerCDStub
})

_InnerDiscArtistCredit = TypedDict("_InnerDiscArtistCredit", {
    "name": str,
    "id": str,
    "sort-name": str
})

_DiscArtistCredit = TypedDict("_DiscArtistCredit", {
    "artist": _InnerDiscArtistCredit
})

_DiscReleaseEventArea = TypedDict("_DiscReleaseEventArea", {
    "name": str,
    "id": str,
    "iso-3166-1-code-list": List[str],
    "sort-name": str
})

_DiscReleaseEvent = TypedDict("_DiscReleaseEvent", {
    "date": str,
    "area": _DiscReleaseEventArea
})

_DiscMediumTrackRecording = TypedDict("_DiscMediumTrackRecording", {
    "length": str,
    "id": str,
    "artist-credit-phrase": str,
    "title": str,
    "artist-credit": List[_DiscArtistCredit]
})

_DiscMediumTrack = TypedDict("_DiscMediumTrack", {
    "artist-credit": List[_DiscArtistCredit],
    "number": str,
    "recording": _DiscMediumTrackRecording,
    "length": str,
    "id": str,
    "track_or_recording_length": str,
    "position": str,
    "artist-credit-phrase": str
})

_DiscMediumDisc = TypedDict("_DiscMediumDisc", {
    "id": str,
    "offset-list": List[int],
    "sectors": str,
    "offset-count": int
})

_DiscMedium = TypedDict("_DiscMedium", {
    "track-list": List[_DiscMediumTrack],
    "track-count": int,
    "format": str,
    "disc-list": List[_DiscMediumDisc],
    "disc-count": int,
    "position": str
})

_DiscTextRepresentation = TypedDict("_DiscTextRepresentation", {
    "language": str,
    "script": str
})


_DiscCoverArtArchive = TypedDict("_DiscCoverArtArchive", {
    "artwork": str,
    "count": str,
    "front": str,
    "back": str
})

_DiscRelease = TypedDict("_DiscRelease", {
    "medium-count": int,
    "artist-credit": List[_DiscArtistCredit],
    "barcode": str,
    "date": str,
    "country": str,
    "release-event-list": List[_DiscReleaseEvent],
    "artist-credit-phrase": str,
    "title": str,
    "status": str,
    "medium-list": List[_DiscMedium],
    "id": str,
    "text-representation": _DiscTextRepresentation,
    "cover-art-archive": _DiscCoverArtArchive,
    "release-event-count": int,
    "quality": str
})

_InnerDisc = TypedDict("_InnerDisc", {
    "offset-list": List[int],
    "release-count": int,
    "release-list": List[_DiscRelease],
    "id": str,
    "sectors": str,
    "offset-count": int
})

_Disc = TypedDict("_Disc", {
    "disc": _InnerDisc
})
