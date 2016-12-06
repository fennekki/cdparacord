import os
import subprocess
import musicbrainzngs

from tempfile import TemporaryDirectory


class ParanoiaError(Exception):
    pass


def find_cdparanoia():
    paranoia_ok = False

    # Check that cdparanoia exists
    for path in os.environ['PATH'].split(os.pathsep):
        path = path.strip('"')
        cdparanoia = os.path.join(path, 'cdparanoia')
        # isfile checks both that file exists and is a file, os.access
        # with X_OK checks file has executable bit
        if os.path.isfile(cdparanoia) and os.access(cdparanoia, os.X_OK):
            paranoia_ok = True
            break

    if not paranoia_ok:
        raise ParanoiaError('cdparanoia executable not found in path')

    return cdparanoia


def main():
    # Import discid here because it might raise
    import discid

    cdparanoia = find_cdparanoia()
    with TemporaryDirectory(suffix='cdparacord') as tmpdir:
        print("Fetching disc id...", end=" ")
        disc = discid.read()
        print(disc)

        print("Fetching data from MusicBrainz...", end=" ")
        try:
            result = musicbrainzngs.get_releases_by_discid(disc.id)

        except musicbrainzngs.ResponseError:
            print("not found")

        print("Starting rip in the background")
        proc = subprocess.Popen([
            cdparanoia, '-e', '-B', '--', '1-',
            "{tmpdir}/".format(tmpdir=tmpdir)
        ])


if __name__ == "__main__":
    try:
        main()
    except OSError:
        print("The libdiscid was not found. Please make sure discid is"
              "installed before running cdparacord.")
    except ParanoiaError:
        print("A cdparanoia executable was not found. Please make sure"
              "cdparanoia is installed before running cdparacord.")
