import os
import subprocess
import musicbrainzngs
import eyed3

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


def main():
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
                tracks.append("")

        tempfile = NamedTemporaryFile(
                prefix="cdparacord", mode="w+", delete=False)
        tempfile_name = tempfile.name

        d = [
            "ARTIST={}\n".format(selected["artist"]),
            "TITLE={}\n".format(selected["title"]),
            "TRACK_COUNT={}\n".format(selected["track_count"])
         ]

        for track in selected["tracks"]:
            d.append("TRACK={}\n".format())

        tempfile.writelines(d)
        tempfile.close()

        # TODO maybe some people don't enjoy vim
        subprocess.run(["/usr/bin/env", "vim", tempfile_name])

        # Track count doesn't change
        final = {"track_count": selected["track_count"]}

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

        # Check that we haven't somehow given names for the wrong amount
        # of tracks
        if len(final["tracks"] != final["track_count"]):
            raise TagError("Wrong tag count: expected {}, got {}"
                           .format(final["track_count"],
                                   len(final["tracks"])))

        # TODO don't hardcode this I guess
        # Where the mp3s will be put
        albumdir = "{home}/Music/{artist}/{album}/".format(
            home=os.environ["HOME"],
            artist=final["artist"],
            album=final["title"])

        os.makedirs(albumdir)
        encode_jobs = []
        final_names = []
        print("Starting rip of {} tracks".format(final["track_count"]))
        for i in range(1, final["track_count"] + 1):
            subprocess.run([
                cdparanoia, "--", str(i),
                "{tmpdir}/{i}.wav".format(tmpdir=tmpdir, i=i)
            ])
            # Huff, but the i - 1 is only needed specifically here, i
            # elsewhere too
            track_title = final["tracks"][i - 1]
            final_name = "{albumdir}/{i:02d} - {title}.mp3".format(
                    albumdir=albumdir, i=i, title=track_title)
            # So we can do the tagging eventually
            final_names.append(final_name)

            # Asynch encode this stuff with lame
            proc = subprocess.Popen([
                lame, "-V2",
                "{tmpdir}/{i}.wav".format(tmpdir=tmpdir, i=i),
                final_name])
            # So we can wait on it later
            encode_jobs.append(proc)

        # Wait till encodes are over and tag
        file_counter = 0
        for job in encode_jobs:
            job.wait()
            # Fortunately they're always in the same order
            audiofile = eyed3.load(final_names[file_counter])
            audiofile.tag.artist = final["artist"]
            audiofile.tag.album = final["title"]
            audiofile.tag.title = final["tracks"][file_counter]
            audiofile.tag.track_num = file_counter + 1
            audiofile.tag.save()

    # Temp dir destroyed
    print("Done")


if __name__ == "__main__":
    try:
        main()
    except OSError:
        print("The libdiscid was not found. Please make sure discid is"
              "installed before running cdparacord.")
    except ParanoiaError:
        print("A cdparanoia executable was not found. Please make sure"
              "cdparanoia is installed before running cdparacord.")
    except LameError:
        print("A lame executable was not found. Please make sure"
              "lame is installed before running cdparacord.")
