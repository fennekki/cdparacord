"""Tools for encoding and tagging."""
import mutagen
import mutagen.easyid3

import asyncio
from sys import stderr
from .utils import print_error, sanitise_filename, \
    CdparacordError

# Module_level lock for the ripper
rip_lock = asyncio.Lock()

async def tag_file(filename, trackinfo):
    try:
        audiofile = mutagen.easyid3.EasyID3(filename)
    except:
        audiofile = mutagen.File(filename, easy=True)
        audiofile.add_tags()

    if "albumartist" in trackinfo:
        # Has album artist, so we'll always have artist info
        audiofile["albumartist"] = trackinfo["albumartist"]
        if "artist" in trackinfo:
            # Also has track artist info
            audiofile["artist"] = trackinfo["artist"]
        else:
            # In albumartist files we always want track artist, even if
            # it's the same as album artist. This is mostly a
            # consistency thing though it would not surprise me if not
            # doing this messed up some audio players.
            audiofile["artist"] = trackinfo["albumartist"]
    elif "artist" in trackinfo:
        # Just write track artist; This is an album that didn't need
        # albumartist
        audiofile["artist"] = trackinfo["artist"]
    else:
        print_error("TAGGING {}: No artist info!".format(filename))

    if "album" in trackinfo:
        audiofile["album"] = trackinfo["album"]
    else:
        print_error("TAGGING {}: No album name!".format(filename))

    if "title" in trackinfo:
        audiofile["title"] = trackinfo["title"]
    else:
        print_error("TAGGING {}: No track name!".format(filename))

    if "tracknumber" in trackinfo:
        # Note that we expect the track number could be a number.
        audiofile["tracknumber"] = str(trackinfo["tracknumber"])
    else:
        print_error("TAGGING {}: No track number!".format(filename))

    if "date" in trackinfo:
        # Just don't record a date if it wasn't given
        audiofile["date"] = trackinfo["date"]

    audiofile.save()

    print("Tagged {}".format(trackinfo["title"]))

async def rip_track(cdparanoia, trackinfo, temporary_name):
    # Only one coro can rip at once!!
    async with rip_lock:
        proc = await asyncio.create_subprocess_exec(
            cdparanoia, "--", str(trackinfo["tracknumber"]),
            temporary_name)
        await proc.wait()


async def encode_track(lame, trackinfo, tmpdir, final_name):
    proc = await asyncio.create_subprocess_exec(
        lame, "-V2",
        "{tmpdir}/{tracknumber}.wav".format(
            tmpdir=tmpdir, tracknumber=trackinfo["tracknumber"]),
        final_name
    )
    await proc.wait()


async def rip_encode_and_tag(cdparanoia, lame, trackinfo, albumdir, tmpdir):
    temporary_name = "{tmpdir}/{tracknumber}.wav".format(
            tmpdir=tmpdir,
            tracknumber=trackinfo["tracknumber"])
    final_name = "{albumdir}/{tracknumber:02d} - {title}.mp3".format(
            albumdir=albumdir,
            tracknumber=trackinfo["tracknumber"],
            title=sanitise_filename(trackinfo["title"]))

    await rip_track(cdparanoia, trackinfo, temporary_name)

    await encode_track(lame, trackinfo, tmpdir, final_name)

    print("Encoded {}, tagging".format(trackinfo["title"]))
    await tag_file(final_name, trackinfo)
