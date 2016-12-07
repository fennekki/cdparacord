import os
import sys
import subprocess
import asyncio
import musicbrainzngs
import mutagen
import mutagen.easyid3

from tempfile import TemporaryDirectory, NamedTemporaryFile
from .appinfo import __version__, __url__


def find_executable(name, exception):
    ok = False

    for path in os.environ["PATH"].split(os.pathsep):
        path = path.strip('"')
        binname = os.path.join(path, name)
        # isfile checks both that file exists and is a file, os.access
        # with X_OK checks file has executable bit
        if os.path.isfile(binname) and os.access(binname, os.X_OK):
            ok = True
            break

    if ok:
        return binname
    raise exception("{} not found".format(name))


class ParanoiaError(Exception):
    pass


def find_cdparanoia():
    return find_executable("cdparanoia", ParanoiaError)


class LameError(Exception):
    pass


def find_lame():
    return find_executable("lame", LameError)


class TagError(Exception):
    pass


async def rip_encode_and_tag(cdparanoia, lame, albumdir, tmpdir, track_num,
                             artist, album, track_title, date):
    subprocess.run([
        cdparanoia, "--", str(track_num),
        "{tmpdir}/{track_num}.wav".format(tmpdir=tmpdir, track_num=track_num)
    ])

    final_name = "{albumdir}/{track_num:02d} - {title}.mp3".format(
            albumdir=albumdir, track_num=track_num,
            title=track_title.replace("/", "-")
            .replace(": ", " - ")
            .replace(":", "-")
            .replace(".", "_"))

    # Asynch encode this stuff with lame
    proc = await asyncio.create_subprocess_exec(
        lame, "-V2",
        "{tmpdir}/{track_num}.wav".format(
            tmpdir=tmpdir, track_num=track_num),
        final_name
    )
    await proc.wait()

    print("Encoded {}, tagging".format(track_title))
    await asyncio.sleep(1)

    try:
        audiofile = mutagen.easyid3.EasyID3(final_name)
    except:
        audiofile = mutagen.File(final_name, easy=True)
        audiofile.add_tags()
    audiofile["artist"] = artist
    audiofile["album"] = album
    audiofile["title"] = track_title
    audiofile["tracknumber"] = str(track_num)
    audiofile["date"] = date
    audiofile.save()
    print("Tagged {}".format(track_title))


def main(args):
    # Import discid here because it might raise
    import discid

    cdparanoia = find_cdparanoia()
    lame = find_lame()

    with TemporaryDirectory(prefix="cdparacord") as tmpdir:
        print("Fetching disc id...", end=" ")
        disc = discid.read()
        print(disc)

        print("Fetching data from MusicBrainz...", end=" ")
        try:
            musicbrainzngs.set_useragent("cdparacord", __version__, __url__)
            result = musicbrainzngs.get_releases_by_discid(
                    disc.id, includes=["recordings", "artists"])

            print("found")

            print("Pick release: ")
            parsed = []

            release_counter = 0
            data = result["disc"]["release-list"]
            for release in data:
                # TODO date
                albumdata = {}
                albumdata["title"] = release["title"]
                albumdata["tracks"] = []
                artist = release["artist-credit-phrase"]
                albumdata["artist"] = artist

                print("------")
                print(release_counter, "-", artist, "/", release["title"])
                print("---")
                release_counter += 1

                track_counter = 1
                medium = release["medium-list"][0]
                for track in medium["track-list"]:
                    recording = track["recording"]
                    albumdata["tracks"].append(recording["title"])
                    print(track_counter, "-", recording["title"])
                    track_counter += 1
                albumdata["track_count"] = track_counter
                parsed.append(albumdata)
                print("------\n")

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
                "artist": "",
                "track_count": num,
                "tracks": []
            }

            # Generate right amount of track entries
            for i in range(selected["track_count"]):
                selected["tracks"].append("")

        tempfile = NamedTemporaryFile(
                prefix="cdparacord", mode="w+", delete=False)
        tempfile_name = tempfile.name

        d = [
            "ARTIST={}\n".format(selected["artist"]),
            "TITLE={}\n".format(selected["title"]),
            "DATE=\n",
            "TRACK_COUNT={}\n".format(selected["track_count"])
         ]

        for track in selected["tracks"]:
            d.append("TRACK={}\n".format(track))

        tempfile.writelines(d)
        tempfile.close()

        # TODO maybe some people don't enjoy vim
        subprocess.run(["/usr/bin/env", "vim", tempfile_name])

        # Track count doesn't change
        final = {
            "track_count": selected["track_count"],
            "tracks": []
        }

        # Parse the file to a map again
        with open(tempfile_name, mode="r") as tempfile:
            for line in tempfile.readlines():
                key, val = line.rstrip().split("=", 1)
                if key == "ARTIST":
                    final["artist"] = val
                elif key == "TITLE":
                    final["title"] = val
                elif key == "TRACK":
                    final["tracks"].append(val)
                elif key == "DATE":
                    final["date"] = val

        # Check that we haven't somehow given names for the wrong amount
        # of tracks
        if len(final["tracks"]) != final["track_count"]:
            raise TagError("Wrong tag count: expected {}, got {}"
                           .format(final["track_count"],
                                   len(final["tracks"])))

        # TODO don't hardcode this I guess
        # TODO the formatting should strip even more "special"
        # characters
        # Where the mp3s will be put
        albumdir = "{home}/Music/{artist}/{album}/".format(
            home=os.environ["HOME"],
            artist=final["artist"].replace("/", "-"),
            album=final["title"].replace("/", "-"))\
            .replace(": ", " - ")\
            .replace(":", "-")

        os.makedirs(albumdir)
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
        for i in range(start_track, end_track + 1):
            tasks.append(asyncio.ensure_future(rip_encode_and_tag(
                cdparanoia, lame, albumdir, tmpdir, i, final["artist"],
                final["title"], final["tracks"][i - 1], final["date"]
            ), loop=loop))

        # Ensure we've run all tasks before we're done
        loop.run_until_complete(asyncio.gather(*tasks))
        loop.close()

    # Temp dir destroyed
    print("\n\nDone")


def entrypoint_wrapper():
    try:
        main(sys.argv)
    except OSError:
        print("The libdiscid was not found. Please make sure discid is"
              "installed before running cdparacord.")
    except ParanoiaError:
        print("A cdparanoia executable was not found. Please make sure"
              "cdparanoia is installed before running cdparacord.")
    except LameError:
        print("A lame executable was not found. Please make sure"
              "lame is installed before running cdparacord.")


if __name__ == "__main__":
    entrypoint_wrapper()
