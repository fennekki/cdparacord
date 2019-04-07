"""Tools for dealing with album data."""
import musicbrainzngs
import os
import os.path
import shutil
import string
import subprocess
import sys
import tempfile
import textwrap
import unicodedata
import yaml
from .appinfo import __version__, __url__
from .error import CdparacordError
from .xdg import XDG_MUSIC_DIR


class AlbumdataError(CdparacordError):
    pass


class Track:
    def __init__(self, trackdata):
        self._title = trackdata['title']
        self._artist = trackdata['artist']
        self._filename = trackdata['filename']
        self._tracknumber = trackdata['tracknumber']

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

    @property
    def tracknumber(self):
        """Print track number for this track."""
        return self._tracknumber


class Albumdata:
    def __init__(self, albumdata):
        """Initialises an Albumdata object from a dict.

        The dict albumdata contains the "plain" album data usually
        acquired from MusicBrainz, the user, or any albumdata already on
        disk.
        """
        self._dict = albumdata
        self._ripdir = albumdata['ripdir']
        self._tracks = []
        counter = 0

        for trackdata in albumdata['tracks']:
            counter = counter + 1
            trackdata['tracknumber'] = counter
            self._tracks.append(Track(trackdata))

        # Find out if there are multiple artists by seeing if at least
        # one of the track artists differs from album artist
        #
        # This check used to be per-track only later in the rip process
        # which caused issues.
        if any(t.artist != self.albumartist for t in self._tracks):
            self.multiartist = True
        else:
            self.multiartist = False


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
        field_width_extra = width - 2 * field_width_small - 3

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

        albumdata['source'] = 'MusicBrainz CD stub'
        albumdata['title'] = cdstub['title']
        # Sometimes cd stubs don't have date. We can just put an empty
        # value there.
        albumdata['date'] = cdstub.get('date', '')
        albumdata['albumartist'] = cdstub['artist']
        albumdata['tracks'] = []
        albumdata['cd_number'] = 1
        albumdata['cd_count'] = 1

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
            cd_number = 0
            for medium in release['medium-list']:
                cd_number +=1
                albumdata = {}

                albumdata['source'] = 'MusicBrainz'
                albumdata['title'] = release['title']
                # Sometimes albumdata doesn't seem to have date. In those
                # cases, we can just put an empty value there.
                albumdata['date'] = release.get('date', '')
                albumdata['tracks'] = []
                albumartist = release['artist-credit-phrase']
                albumdata['albumartist'] = albumartist
                albumdata['cd_number'] = cd_number
                albumdata['cd_count'] = len(release['medium-list'])

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
            pass
        # If we hit the exception or there's *neither* cdstub *nor*
        # disc, we get here.
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
    def _select_albumdata(cls, results):
        max_width, max_height = shutil.get_terminal_size()

        state = 0
        while True:
            # State 0 is the first screen, other ones are the options

            # There should be no way for state to escape these
            # constraints.
            assert 0 <= state <= len(results)

            if state == 0:
                print('=' * max_width)
                print('Albumdata sources available:')
                for i in range(1, len(results) + 1):
                    result = results[i - 1]
                    source_name = result['source']
                    extended_title = result['title']
                    if result['cd_count'] > 1:
                        extended_title += ' (CD {})'.format(
                            result['cd_number'])

                    print('{}) {}: {}'.format(
                        i,
                        source_name,
                        extended_title))
                print('=' * max_width)
            else:
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
                    return results[state - 1]
                else:
                    print(' '.join("""\
                        You can only choose current source when looking at a
                        source""".split()))
            else:
                try:
                    selected = int(s, base=10)
                    if selected < 1 or selected > len(results):
                        if selected == 0:
                            # back to menu
                            state = 0
                            continue
                        print('Source number must be between 1 and {}'.format(
                            len(results)))
                    else:
                        # Got a valid one
                        return results[selected - 1]
                except ValueError:
                    print("Invalid command: {}".format(s))

    @classmethod
    def _generate_filename(cls, data, track, tracknumber, config):
        safetyfilter = config.get('safetyfilter')
        target_template = string.Template(config.get('target_template'))
        s = {
            'album': data['title'],
            'artist': track['artist'],
            'albumartist': data['albumartist'],
            'tracknumber': '{:02}'.format(int(tracknumber)),
            'track': track['title']
        }

        # Apply the safetyfilters to the individual templatable parts so
        # we can still join them into a file path.
        for key in s:
            if safetyfilter == 'ascii':
                s[key] = s[key].encode(
                        'ascii', errors='ignore').decode('ascii')
            elif safetyfilter == 'windows1252':
                s[key] = (s[key]
                    .encode('windows-1252', errors='ignore')
                    .decode('windows-1252'))
            elif safetyfilter == 'unicode_letternumber':
                # Remove everything that's not in these categories
                s[key] = ''.join(
                    c for c in s[key] if unicodedata.category(c) in
                        ('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nd', 'Nl', 'No'))
            elif safetyfilter == 'remove_restricted':
                # This is the only valid option if it's nothing else. We
                # can safely pass because this filter is always applied
                # at the end.
                pass
            else:
                # Raise an error if *no* valid filter is found
                raise AlbumdataError(
                    'Invalid safety filter {}'.format(safetyfilter))

            # Finally apply remove_restricted
            # The generator expression picks out control characters such
            # as carriage returns, nulls and tabs.
            s[key] = ''.join(
                    c for c in s[key] if unicodedata.category(c)[0] != 'C')\
                .replace('/', '-')\
                .replace('\\', '-')\
                .replace(': ', ' - ')\
                .replace(':', '-')\
                .replace('.', '_')\
                .replace('"', '')\
                .replace('|', '')\
                .replace('?', '')\
                .replace('*', '')\
                .replace('<', '')\
                .replace('>', '')\
                .strip()  # Remove any trailing/leading whitespace

        # Add the 'safe' ones to the dict
        # These shouldn't need safety filtering, they're not from
        # albumdata input
        s.update({
            'home': os.getenv('HOME'),
            'xdgmusic': XDG_MUSIC_DIR
        })

        return target_template.substitute(s)

    @classmethod
    def _edit_albumdata(cls, selected, track_count, editor, config):
        if selected is None:
            return None

        max_width, max_height = shutil.get_terminal_size()

        data = selected
        state = None
        while True:
            if state == 'e':
                with tempfile.NamedTemporaryFile(mode='w+') as f:
                    yaml.safe_dump(data, f, default_flow_style=False,
                        allow_unicode=True)
                    f.flush()
                    subprocess.run([editor, f.name])
                    f.seek(0)
                    temp_data = yaml.safe_load(f)

                    erroneous_data = False
                    # TODO: more validation
                    if len(temp_data['tracks']) != len(data['tracks']):
                        print(' '.join("""Wrong track count in edited
                            data (Got {}, {} expected)""".split()).format(
                                len(temp_data['tracks']), len(data['tracks'])),
                            file=sys.stderr)
                        erroneous_data = True

                    if len(temp_data['discid']) != len(data['discid']):
                        print('Disc id was edited', file=sys.stderr)
                        erroneous_data = True

                    if len(temp_data['ripdir']) != len(data['ripdir']):
                        print('Ripdir was edited', file=sys.stderr)
                        erroneous_data = True

                    if erroneous_data:
                        print('Edited data not accepted.')
                    else:
                        data = temp_data
                    state = None
            elif state == 'f':
                # Regenerate filenames
                print('Filenames generated:')
                print('-' * max_width)
                counter = 0
                for track in data['tracks']:
                    counter = counter + 1
                    track['filename'] = cls._generate_filename(data, track, counter, config)
                    print(track['filename'])
                state = None
            elif state == 'r':
                # We start the rip by returing Albumdata :D
                print('Are you sure you want to rip this data:')
                cls._print_albumdata(data)
                print(' '.join("""\
                        Ensure your filenames are correct!! If your
                        terminal isn't wide enough, please cancel out
                        and hit 'e' on the menu to confirm the filenames
                        are correct.""".split()))
                if input(' [yN]> ').strip() == 'y':
                    return Albumdata(data)
                else:
                    print('Returning to menu')
                    state = None
            elif state == 'a':
                # Just abort, do nothing else
                return None
            elif state == 's':
                print('Saving state...')
                # Make the dir here since we won't be making it in main
                # and we need it now
                # Otherwise Rip will generate this file
                os.makedirs(data['ripdir'], 0o700, exist_ok=True)

                albumdata_file = os.path.join(
                    data['ripdir'], 'albumdata.yaml')
                with open(albumdata_file, 'w') as f:
                    yaml.safe_dump(data, f)
                return None
            else:
                print(textwrap.dedent("""\
                    Select action. 'Rip' starts the ripping process.
                    e: edit
                    f: regenerate filenames
                    r: rip
                    s: save and abort
                    a: discard and abort
                    """))
                state = input("> ").strip()

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
        except discid.DiscError:  # pragma: no cover
            raise AlbumdataError('Could not read CD')

        ripdir = '{tmp}/cdparacord/{uid}-{discid}'.format(
            tmp=tempfile.gettempdir(), uid=os.getuid(), discid=disc)
        albumdata_file = os.path.join(ripdir, 'albumdata.yaml')

        track_count = cls._get_track_count(deps.cdparanoia)

        if track_count is None:
            raise AlbumdataError('Could not figure out track count')

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

        emptydata = {
            'source': 'Empty data',
            'title': '',
            'date': '',
            'albumartist': '',
            'tracks': [],
            'cd_number': 1,
            'cd_count': 1
        }

        # We do this to avoid emitting anchors in the yaml (which it
        # would do if the objects were the same). This is for user
        # friendliness.
        for _ in range(track_count):
            emptydata['tracks'].append({
                'title': '',
                'artist': ''
            })

        results.append(emptydata)

        dropped = []
        for result in results:
            # Check that the track count is correct
            if len(result['tracks']) != track_count:
                print(' '.join("""\
                    Note: Dropped CD {} of source {} for
                    wrong track count (Got {}, {} expected)""".format(
                        result['cd_number'],
                        result['source'],
                        len(result['tracks']),
                        track_count
                    ).split()), file=sys.stderr)
                dropped.append(result)
                continue
            # Merge in the common data
            result.update(common_albumdata)
            # Template filenames for the songs
            counter = 0
            for track in result['tracks']:
                # If filenames exist, keep them (usually only previous
                # rip data)
                counter = counter + 1
                if not 'filename' in track:
                    track['filename'] = cls._generate_filename(
                        result, track, counter, config)

        # Actually drop results that have the wrong amount of tracks
        results = [r for r in results if r not in dropped]

        selected = cls._select_albumdata(results)

        # Edit albumdata
        return cls._edit_albumdata(selected, track_count, deps.editor, config)

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

    @property
    def title(self):
        """Return title."""
        return self.dict['title']

    @property
    def date(self):
        """Return date."""
        return self.dict['date']

    @property
    def albumartist(self):
        """Return albumartist."""
        return self.dict['albumartist']

    @property
    def dict(self):
        """Return dict this albumdata was generated from.

        Note: Editing this will edit the actual data in the dict, but
        will *not* update the properties of the Albumdata object! If you
        want to change the properties, you need to create a new
        Albumdata object from the edited data.
        """
        return self._dict
