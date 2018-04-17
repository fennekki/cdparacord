"""Tools for dealing with album data."""
import musicbrainzngs
import subprocess
import os
import os.path
import sys
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
    def _print_albumdata(albumdata):
        """Print albumdata to fit a terminal.

        This is powerfully hacky.
        """

        max_width, max_height = shutil.get_terminal_size()

        min_width = 60
        width = max(min_width, max_width)

        threshold_width = 80
        field_width_big = int(width / 2 - 1)
        field_width_small = int(max(threshold_width, width) / 4 - 1)
        field_width_extra = width - 2 * field_width_small

        # This is extremely ridiculous but should not be unsafe
        double_field_format = '{{:<{}}}  {{:<{}}}'.format(
            field_width_big, field_width_big)
        triple_field_format = '{{:<{}}} {{:<{}}}  {{:<{}}}'.format(
            field_width_small, field_width_small, field_width_extra)

        threshold_met = False
        if width >= threshold_width and field_width_extra > 10:
            threshold_met = True

        print('=' * width)
        if threshold_met:
            print(triple_field_format.format(
                textwrap.shorten(albumdata['albumartist'], field_width_big),
                textwrap.shorten(albumdata['title'], field_width_big),
                textwrap.shorten(albumdata['discid'], field_width_extra)))
        else:
            print(double_field_format.format(
                textwrap.shorten(albumdata['albumartist'], field_width_big),
                textwrap.shorten(albumdata['title'], field_width_big)))
        print('=' * width)
        if threshold_met:
            print(triple_field_format.format('Track', 'Track Artist', 'Suggested filename'))
        else:
            print(double_field_format.format('Track', 'Track Artist'))
        print('-' * width)
        for track in albumdata['tracks']:
            if threshold_met:
                print(triple_field_format.format(
                    textwrap.shorten(track['title'], field_width_small),
                    textwrap.shorten(track['artist'], field_width_small),
                    textwrap.shorten(track['filename'], field_width_extra)))
            else:
                print(double_field_format.format(
                    textwrap.shorten(track['title'], field_width_big),
                    textwrap.shorten(track['artist'], field_width_big)))
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
        except musicbrainzngs.MusicBrainzError: # pragma: no cover
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
    def _get_track_count(cls, cdparanoia):
        """Find track count by running cdparanoia."""
        # Let's do a dirty hack to find the track count!
        proc = subprocess.run([cdparanoia, '-sQ'],
                              universal_newlines=True,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)
        # Error if it failed
        proc.check_returncode()

        output = proc.stdout
        extract_next = False
        lines = output.split('\n')
        # Go through lines in reverse until we find TOTAL
        # The line above that has the number
        for i in reversed(range(len(lines))):
            line = lines[i]
            if extract_next:
                parts = line.split(".")
                num = int(parts[0].strip())
                return num
            elif line[0:5] == 'TOTAL':
                extract_next = True


    @classmethod
    def from_user_input(cls, deps, config):
        """Initialises an Albumdata object from interactive user input.

        Returns None if the user chose to abort the selection.
        """

        # Since we're given deps, discid exists
        import discid

        use_musicbrainz = config.get('use_musicbrainz')
        reuse_albumdata = config.get('reuse_albumdata')

        try:
            disc = discid.read()
        except discid.DiscError:
            raise AlbumdataError('Could not read CD')

        ripdir = '/tmp/cdparacord/{uid}-{discid}'.format(
            uid=os.getuid(), discid=disc)
        albumdata_file = os.path.join(ripdir, 'albumdata.yaml')

        track_count = cls._get_track_count(deps.cdparanoia)

        # Data to be merged to the albumdata we select
        common_albumdata = {
            'discid': str(disc),
            'ripdir': ripdir
        }
        results = []

        # If we are reusing albumdata and it exists, recommend that as a
        # first option
        if reuse_albumdata:
            loaded_albumdata = cls._albumdata_from_previous_rip(albumdata_file)
            if loaded_albumdata is not None:
                results.append(loaded_albumdata)

        # Append results from MusicBrainz if needed
        if use_musicbrainz:
            # We get a list of results so we call extend
            results.extend(cls._albumdata_from_musicbrainz(disc))

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

        
        dropped = []
        for result in results:
            # Check that the track count is correct
            if len(result['tracks']) != track_count:
                print(' '.join("""\
                    Warning: Source {} dropped for wrong track count (Got {},
                    {} expected)""".format(
                        result['source'], len(result['tracks']), track_count
                    ).split()), file=sys.stderr)
                dropped.append(result)
                continue
            # Merge in the common data
            result.update(common_albumdata)
            # Template filenames for the songs
            # TODO: actually template them
            # TODO: This sucks, actually? If we have an editor it needs
            # a hotkey for "automatically generate filename from edited
            # title" or this'll be *worse* than before
            for track in result['tracks']:
                track['filename'] = 'TODO'

        # Actually drop results that have the wrong amount of tracks
        results = [r for r in results if r not in dropped]

        # TODO: PERFORM THE SELECTION
        
        selection = None
        state = 0
        while selection is None:
            # Only what we print depends on state: The state transitions
            # are always the same TODO except maybe "select this"?
            # State 0 is the first screen, other ones are the options
            if state == 0:
                print('=' * max_width)
                print('Albumdata sources available:')
                for i in range(1, len(results) + 1):
                    print('{}) {}'.format(i, results[i - 1]['source']))
                print('=' * max_width)
            elif state <= track_count:
                print('Source {}: {}'.format(
                    state, results[state - 1]['source']))
                cls._print_albumdata(results[state - 1])

            print(textwrap.dedent("""\
                0: return to listing
                1-{}: select source
                n: show next source:
                c: choose current source
                a: abort
                """).format(len(results)))
            s = input("> ").strip()

            if s in ('a', 'A'):
                # Abort
                return None
            elif s in ('n', 'N'):
                state = (state + 1) % (len(results) + 1)
                if state == 0:
                    print("All sources viewed, returning to listing")
            elif s in ('c', 'C'):
                if state > 0:
                    # Select the one being shown
                    return Albumdata(results[state - 1])
                else:
                    print(' '.join("""\
                        You can only choose current source when looking at a
                        source""".split()))
            else:
                try:
                    selected = int(s, base=10)
                    if selected < 1 or selected > len(results):
                        print('Source number must be between 1 and {}'.format(
                            len(results)))
                    else:
                        # Got a valid one
                        return Albumdata(results[selected - 1])
                except ValueError:
                    print("Invalid command: {}".format(s))

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
