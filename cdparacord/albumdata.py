"""Tools for dealing with album data."""
import musicbrainzngs
import subprocess

from tempfile import NamedTemporaryFile
from .appinfo import __version__, __url__
from .utils import find_executable

class ParanoiaError(Exception):
    pass


def find_cdparanoia():
    return find_executable("cdparanoia", ParanoiaError)


def print_tracks(release_counter, albumdata):
    print("------")
    print(release_counter, "-", albumartist, "/", albumdata["title"])
    print("---")

    track_counter = 0
    for track in albumdata["tracks"]:
        track_counter += 1
        print(track_counter, "-", track)
    print("------\n")


def parsed_from_disc():
    parsed = []
    data = result["disc"]["release-list"]

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


def parsed_from_cdstub():
    release = result["cdstub"]

    albumdata = {}
    albumdata["title"] = release["title"]
    albumdata["date"] = release["date"]
    albumdata["tracks"] = []
    albumartist = release["artist"]
    albumdata["albumartist"] = albumartist

    release_counter += 1

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
        release_counter = 0
        if "disc" in result:
            parsed = albumdata_from_disc()
        elif "cdstub" in result:
            parsed = albumdata_from_cdstub()
        else:
            raise CdparacordError("No albumdata found")

        sel = -1
        while sel < 0 or sel >= release_counter:
            try:
                sel = int(input("Number between {}-{}: "
                                .format(0, release_counter - 1)))
            except:
                pass

        selected = parsed[sel]

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
    print(disc)

    print("Fetching data from MusicBrainz...", end=" ")
    selected = musicbrainz_fetch(disc)

    tempfile = NamedTemporaryFile(
            prefix="cdparacord", mode="w+", delete=False)
    tempfile_name = tempfile.name

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

    tempfile.writelines(d)
    tempfile.close()

    # TODO maybe some people don't enjoy vim
    subprocess.run(["/usr/bin/env", "vim", tempfile_name])

    # Track count doesn't change
    final = {
        "track_count": selected["track_count"],
        "tracks": [],
        "artists": []
    }

    # Parse the file to a map again
    with open(tempfile_name, mode="r") as tempfile:
        for line in tempfile.readlines():
            if line.rstrip() == "":
                # Skip this line, it's empty
                continue
            key, val = line.rstrip().split("=", 1)
            if key == "ALBUMARTIST":
                final["albumartist"] = val
            elif key == "TITLE":
                final["title"] = val
            elif key == "TRACK":
                final["tracks"].append(val)
            elif key == "ARTIST":
                if (val != ""):
                    final["artists"].append(val)
                else:
                    final["artists"].append(final["albumartist"])
            elif key == "DATE":
                final["date"] = val

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
