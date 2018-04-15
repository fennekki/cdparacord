"""Tools for dealing with album data."""
import musicbrainzngs
import subprocess
import os
import shutil
import textwrap
from tempfile import NamedTemporaryFile
from .appinfo import __version__, __url__
from .utils import find_executable
from .error import CdparacordError


class AlbumdataError(CdparacordError):
    pass


class Track:
    def __init__(self, trackdata):
        self._title = trackdata['title']
        self._artist = trackdata['artist']
        self._filename = trackdata['filename']

    @property
    def title(self):
        """Print title of this track."""
        return self._title

    @property
    def artist(self):
        """Print artist of this track."""
        return self._artist

    @property
    def filename(self):
        """Print target filename for this track."""
        return self._filename


class Albumdata:
    def __init__(self, albumdata):
        """Initialises an Albumdata object from a dict.

        The dict albumdata contains the "plain" album data usually
        acquired from MusicBrainz, the user, or any albumdata already on
        disk.
        """
        self._ripdir = '/tmp/cdparacord/{uid}-{discid}'.format(
                uid=os.getuid(), discid=albumdata['discid'])
        self._tracks = []
        for trackdata in albumdata['tracks']:
            self._tracks.append(Track(trackdata))

    @staticmethod
    def _print_albumdata(albumdata, width):
        """Print albumdata to fit a terminal.

        This is powerfully hacky.
        """
        field_width_2 = int(width / 2 - 1)
        field_width_4 = int(width / 4 - 1)

        # This is extremely ridiculous but should not be unsafe
        double_field_format = '{{:<{}}}  {{:<{}}}'.format(
            field_width_2, field_width_2)
        triple_field_format = '{{:<{}}} {{:<{}}}  {{:<{}}}'.format(
            field_width_4, field_width_4, field_width_2)

        print('=' * width)
        print(double_field_format.format(
            textwrap.shorten(albumdata['albumartist'], field_width_2),
            textwrap.shorten(albumdata['title'], field_width_2)))
        print('=' * width)
        print(triple_field_format.format('Track', 'Track Artist', 'Suggested filename'))
        print('-' * width)
        for track in albumdata['tracks']:
            print(triple_field_format.format(
                textwrap.shorten(track['title'], field_width_4),
                textwrap.shorten(track['artist'], field_width_4),
                textwrap.shorten(track['filename'], field_width_2)))
        print('-' * width)

    @classmethod
    def from_user_input(cls, deps, config):
        """Initialises an Albumdata object from interactive user input.

        Returns None if the user chose to abort the selection.
        """

        width, height = shutil.get_terminal_size()

        min_width = 60
        max_width = max(min_width, width)

        use_musicbrainz = config['use_musicbrainz']
        reuse_albumdata = config['reuse_albumdata']

    @property
    def ripdir(self):
        """Return the directory this album's rip should be in."""
        return self._ripdir

    @property
    def track_count(self):
        """Return the directory this album's rip should be in."""
        return len(self._tracks)

    @property
    def tracks(self):
        """Return list of tracks"""
        return self._tracks


class ParanoiaError(Exception):
    pass


def find_cdparanoia():
    return find_executable("cdparanoia", ParanoiaError)


def print_tracks(release_counter, albumdata):
    print("------")
    print(release_counter, "-", albumdata["albumartist"], "/", albumdata["title"])
    print("---")

    track_counter = 0
    for track in albumdata["tracks"]:
        track_counter += 1
        print(track_counter, "-", track)
    print("------\n")


def parsed_from_disc(result):
    parsed = []
    data = result["disc"]["release-list"]

    release_counter = 0
    for release in data:
        albumdata = {}
        albumdata["title"] = release["title"]
        albumdata["date"] = release["date"]
        albumdata["tracks"] = []
        albumdata["artists"] = []
        albumartist = release["artist-credit-phrase"]
        albumdata["albumartist"] = albumartist

        release_counter += 1
        track_counter = 0
        medium = release["medium-list"][0]
        for track in medium["track-list"]:
            # Count tracks,
            track_counter += 1
            recording = track["recording"]
            albumdata["tracks"].append(recording["title"])
            albumdata["artists"].append(recording["artist-credit-phrase"])
        albumdata["track_count"] = track_counter

        parsed.append(albumdata)
        print_tracks(release_counter, albumdata)
    return parsed


def parsed_from_cdstub(result):
    release = result["cdstub"]

    albumdata = {}
    albumdata["title"] = release["title"]
    albumdata["date"] = release["date"]
    albumdata["tracks"] = []
    albumartist = release["artist"]
    albumdata["albumartist"] = albumartist

    release_counter = 1

    track_counter = 0
    for track in release["track-list"]:
        track_counter += 1
        albumdata["tracks"].append(track["title"])
        albumdata["artists"].append(albumartist)
    albumdata["track_count"] = track_counter
    parsed.append(albumdata)

    print_tracks(release_counter, albumdata)
    return albumdata


def musicbrainz_fetch(disc):
    cdparanoia = find_cdparanoia()

    try:
        musicbrainzngs.set_useragent("cdparacord", __version__, __url__)
        result = musicbrainzngs.get_releases_by_discid(
                disc.id, includes=["recordings", "artist-credits"])

        print("found")

        print("Pick release: ")
        if "disc" in result:
            parsed = parsed_from_disc(result)
        elif "cdstub" in result:
            parsed = parsed_from_cdstub(result)
        else:
            raise CdparacordError("No albumdata found")

        sel = -1
        release_count = len(parsed)
        while sel < 1 or sel > release_count:
            try:
                sel = int(input("Number between {}-{}: "
                                .format(1, release_count)))
            except:
                pass

        selected = parsed[sel - 1]

    except musicbrainzngs.ResponseError:
        print("not found")

        # Let's do a dirty hack to find the track count!
        proc = subprocess.run([cdparanoia, '-sQ'],
                              universal_newlines=True,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)
        # Error if it failed
        proc.check_returncode()

        output = proc.stdout
        start = False
        for line in output.split("\n"):
            # Stop at the end of the output
            if line[0:5] == "TOTAL":
                start = False

            if start:
                parts = line.split(".")
                num = int(parts[0].strip())

            # Start after the ===== line
            if not start and len(line) > 0 and line[0] == "=":
                start = True

        # Now we know how many tracks this CD has
        # Don't even give a shit about CD-Text
        selected = {
            "title": "",
            "albumartist": "",
            "date": "",
            "track_count": num,
            "tracks": [],
            "artists": []
        }

        # Generate right amount of track entries
        for i in range(selected["track_count"]):
            selected["tracks"].append("")
            selected["artists"].append("")

    return selected


def get_final_albumdata():
    # Import discid here because it might raise
    import discid

    print("Fetching disc id...", end=" ")
    disc = discid.read()
    print("Id:", disc)
    print("Submission url:", )

    print("Fetching data from MusicBrainz...", end=" ")
    selected = musicbrainz_fetch(disc)

    datafile = NamedTemporaryFile(
            prefix="cdparacord", mode="w+", delete=False)
    datafile_name = datafile.name

    d = [
        "ALBUMARTIST={}\n".format(selected["albumartist"]),
        "TITLE={}\n".format(selected["title"]),
        "DATE={}\n".format(selected["date"]),
        "TRACK_COUNT={}\n".format(selected["track_count"])
     ]

    for i in range(len(selected["tracks"])):
        # Group the tracks nicely
        d.append("\n")
        d.append("TRACK={}\n".format(selected["tracks"][i]))
        d.append("ARTIST={}\n".format(selected["artists"][i]))
    d.append("\n")
    d.append('# If you wish to correct this information in MusicBrainz,'
             ' use the following URL:\n')
    d.append("# {}\n".format(disc.submission_url))

    datafile.writelines(d)
    datafile.close()

    # TODO maybe some people don't enjoy vim
    subprocess.run(["/usr/bin/env", "vim", datafile_name])

    # Track count doesn't change
    final = {
        "discid": str(disc),
        "track_count": selected["track_count"],
        "tracks": [],
        "artists": []
    }

    # Parse the file to a map again
    with open(datafile_name, mode="r") as datafile:
        for line in datafile.readlines():
            if line.rstrip() == "":
                # Skip this line, it's empty
                continue
            if line.rstrip()[0] == "#":
                # Comment; continue
                continue
            key, val = line.rstrip().split("=", 1)
            if key == "ALBUMARTIST":
                final["albumartist"] = val
            elif key == "TITLE":
                final["title"] = val
            elif key == "TRACK_COUNT":
                # Currently does nothing
                ...
            elif key == "TRACK":
                final["tracks"].append(val)
            elif key == "ARTIST":
                if (val != ""):
                    final["artists"].append(val)
                else:
                    final["artists"].append(final["albumartist"])
            elif key == "DATE":
                final["date"] = val
            else:
                raise CdparacordError('Unknown key {}'.format(key))

    # We no longer need the temporary file, remove it
    os.remove(datafile_name)

    # Check that we haven't somehow given names for the wrong amount
    # of tracks
    if len(final["tracks"]) != final["track_count"]:
        raise CdparacordError("Wrong tag count: expected {}, got {}"
                       .format(final["track_count"],
                               len(final["tracks"])))

    if len(final["artists"]) != final["track_count"]:
        raise CdparacordError("Wrong artist count: expected {}, got {}"
                       .format(final["track_count"],
                               len(final["artists"])))

    return final
