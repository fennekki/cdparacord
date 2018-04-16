"""Tools for dealing with album data."""
import musicbrainzngs
import subprocess
import os
import os.path
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
        self._ripdir = albumdata['ripdir']
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

    @staticmethod
    def _albumdata_from_cdstub(cdstub):
        """Convert MusicBrainz cdstub to albumdata."""
        albumdata = {}

        albumdata['source'] = 'MusicBrainz'
        albumdata['title'] = cdstub['title']
        if 'date' in cdstub:
            albumdata['date'] = cdstub['date']
        else:
            albumdata['date'] = ''
        albumdata['albumartist'] = cdstub['artist']
        albumdata['tracks'] = []

        for track in cdstub['track-list']:
            albumdata['tracks'].append({
                'title': track['title'],
                'artist': cdstub['artist']
            })

        return albumdata

    @staticmethod
    def _albumdata_from_disc(disc):
        """Convert MusicBrainz disc result to multiple albumdata."""
        result = []

        releases = disc['release-list']
        for release in releases:
            albumdata = {}

            albumdata['source'] = 'MusicBrainz'
            albumdata['title'] = release['title']
            albumdata['date'] = release['date']
            albumdata['tracks'] = []
            albumdata['artists'] = []
            albumartist = release['artist-credit-phrase']
            albumdata['albumartist'] = albumartist

            medium = release['medium-list'][0]
            for track in medium['track-list']:
                recording = track['recording']
                albumdata['tracks'].append({
                    'title': recording['title'],
                    'artist': recording['artist-credit-phrase']
                })

            result.append(albumdata)
        return result

    @classmethod
    def _albumdata_from_musicbrainz(cls, disc):
        """Convert MusicBrainz result to list of usable albumdata."""
        musicbrainzngs.set_useragent('cdparacord', __version__, __url__)
        try:
            result = musicbrainzngs.get_releases_by_discid(
                disc, includes=['recordings', 'artist-credits'])

            if 'cdstub' in result:
                return [cls._albumdata_from_cdstub(result['cdstub'])]
            elif 'disc' in result:
                return cls._albumdata_from_disc(result['disc'])
        except musicbrainzngs.MusicBrainzError:
            return []

    @classmethod
    def _albumdata_from_previous_rip(cls, albumdata_file):
        if os.path.isfile(albumdata_file):
            with open(albumdata_file, 'r') as f:
                loaded_albumdata = yaml.safe_load(f)

                if type(loaded_albumdata) is not dict:
                    raise AlbumdataError(
                        'Albumdata file {} is corrupted'.format(
                            albumdata_file))
                loaded_albumdata['source'] = 'Previous rip'
                return loaded_albumdata

    @classmethod
    def from_user_input(cls, deps, config):
        """Initialises an Albumdata object from interactive user input.

        Returns None if the user chose to abort the selection.
        """

        # Since we're given deps, discid exists
        import discid

        width, height = shutil.get_terminal_size()

        min_width = 60
        max_width = max(min_width, width)

        use_musicbrainz = config.get('use_musicbrainz')
        reuse_albumdata = config.get('reuse_albumdata')

        try:
            disc = discid.read()
        except discid.DiscError:
            raise AlbumdataError('Could not read CD')

        ripdir = '/tmp/cdparacord/{uid}-{discid}'.format(
            uid=os.getuid(), discid=disc)
        albumdata_file = os.path.join(ripdir, 'albumdata.yaml')

        # Data to be merged to the albumdata we select
        common_albumdata = {
            'discid': str(disc),
            'ripdir': ripdir
        }
        results = []

        # If we are reusing albumdata and it exists, recommend that as a
        # first option
        if reuse_albumdata:
            loaded_albumdata = _albumdata_from_previous_rip(albumdata_file)
            results.append(loaded_albumdata)

        # Append results from MusicBrainz if needed
        if use_musicbrainz:
            # We get a list of results so we call extend
            results.extend(cls._albumdata_from_musicbrainz(disc))

        # TODO: calculate the track count somehow
        track_count = 10
        results.append({
            'source': 'Empty data',
            'title': '',
            'date': '',
            'albumartist': '',
            'artists': '',
            'tracks': [{
                'title': '',
                'artist': ''
            }] * track_count
        })

        
        for result in results:
            # Merge in the common data
            result.update(common_albumdata)
            # Template filenames for the songs
            # TODO: actually template them
            # TODO: This sucks, actually? If we have an editor it needs
            # a hotkey for "automatically generate filename from edited
            # title" or this'll be *worse* than before
            for track in result['tracks']:
                track['filename'] = 'TODO'

        # TODO: PERFORM THE SELECTION
        print('Sources available:')
        for i in range(1, len(results) + 1):
            print('{}) {}'.format(i, results[i - 1]['source']))
        
        # TODO  while input()


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


# REFACTOR LINE (ALL CODE ABOVE NEW) ------------------------------
#

def musicbrainz_fetch(disc):

    try:
        # REFACTOR LINE ---

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

    # ---- refactor line
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
