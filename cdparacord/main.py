import os
import sys
import asyncio

from tempfile import TemporaryDirectory
from .appinfo import __version__, __url__
from .albumdata import get_final_albumdata, find_cdparanoia,\
        ParanoiaError
from .encode import rip_encode_and_tag
from .utils import sanitise_filename, find_executable


class LameError(Exception):
    pass


def find_lame():
    return find_executable("lame", LameError)


def main(args):
    lame = find_lame()

    final = get_final_albumdata()
    # TODO don't hardcode this I guess
    # Where the mp3s will be put
    albumdir = "{home}/Music/{artist}/{album}/".format(
        home=os.environ["HOME"],
        artist=sanitise_filename(final["albumartist"]),
        album=sanitise_filename(final["title"]))

    # Create rip directory for this album
    ripdir = '/tmp/cdparacord/{uid}-{discid}'.format(
        uid=os.getuid(),
        discid=final['discid'])
    os.makedirs(ripdir, 0o700, exist_ok=True)

    try:
        os.makedirs(albumdir)
    except FileExistsError:
        print("Directory", albumdir, "already exists")
        return
    loop = asyncio.get_event_loop()
    tasks = []

    if len(args) > 1:
        start_track = int(args[1])
        if len(args) > 2:
            end_track = int(args[2])
        else:
            end_track = int(args[1])
    else:
        start_track = 1
        end_track = final["track_count"]

    print("Starting rip of tracks {}-{}".format(start_track, end_track))
    # See if we're multi-artist. This is signaled by having
    # different artists than the album artist for at least 1 track
    multi_artist = False
    for artist in final["artists"]:
        if artist != final["albumartist"]:
            print("Album is multi-artist, tagging album artist")
            multi_artist = True
            break

    for i in range(start_track, end_track + 1):
        trackinfo = {}
        if multi_artist:
            trackinfo["albumartist"] = final["albumartist"]
        trackinfo["album"] = final["title"]
        trackinfo["artist"] = final["artists"][i - 1]
        trackinfo["title"] = final["tracks"][i - 1]
        trackinfo["date"] = final["date"]
        trackinfo["tracknumber"] = i
        tasks.append(asyncio.ensure_future(rip_encode_and_tag(
            find_cdparanoia(), lame, trackinfo, albumdir, ripdir
        ), loop=loop))

    # Ensure we've run all tasks before we're done
    loop.run_until_complete(asyncio.gather(*tasks))
    loop.close()

    # If we got here, we're done: Destroy the rip dir and cdparacorddir
    # I think removedirs is kinda scary but it should only remove empty
    # directories we're allowed to remove.
    # TODO: Move this in its own function
    # TODO: Yes, it's intentional the dir is kept if not empty, but it
    # might need a try-except
    for tracknumber in range(start_track, end_track + 1):
        os.remove("{ripdir}/{tracknumber}.wav".format(
            ripdir=ripdir,
            tracknumber=tracknumber))
    os.removedirs(ripdir)
    print("Rip finished, rip directory removed.")


def entrypoint_wrapper():
    try:
        main(sys.argv)
    except IOError:
        print("Error reading disc. Please make sure there's a music CD in your"
              " drive before running cdparacord.")
    except OSError:
        print("The libdiscid library was not found. Please make sure discid"
              " is installed before running cdparacord.")
    except ParanoiaError:
        print("A cdparanoia executable was not found. Please make sure"
              " cdparanoia is installed before running cdparacord.")
    except LameError:
        print("A lame executable was not found. Please make sure"
              " lame is installed before running cdparacord.")


if __name__ == "__main__":
    entrypoint_wrapper()
