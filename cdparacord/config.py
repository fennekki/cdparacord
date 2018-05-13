"""System for configuring cdparacord."""

import os
import sys
import yaml
import textwrap
from copy import deepcopy
from .error import CdparacordError
from .xdg import XDG_CONFIG_HOME

class ConfigError(CdparacordError):
    """Raised on configuration error."""
    pass


class Config:
    """Represents the configuration of the program.

    The functionality is partially in the class and partially in the
    instance, for no reason in particular.
    """
    # TODO: Put this somewhere else
    # The default config is written so that if you ever replace any of
    # the values in it, you have to replace them entirely. There is no
    # dict merge. However, in many cases, it should not be an issue, and
    # the feature can be added if necessary for some reason.
    # Input file is ${one_file}, output file is ${out_file}. Other file
    # references cannot be currently accessed but they would be
    # ${all_files}.
    __default_config = {
        # Config for the encoder
        'encoder': {
            'lame': {
                'parameters': [
                    '-V2',
                    '${one_file}',
                    '${out_file}'
                ]
            }
        },
        # Tasks follow the format of encoder
        # post_rip are run after an individual file has been ripped to a
        # wav file. The actions are expected to operate on the raw audio
        # data somehow. Can be used to add an additional encoder pass if
        # two encodings are desired for some reason. Scheduled on a
        # per-file basis.
        'post_rip': [
        ],
        # post_encode tasks run after the encoder task (usually LAME) is
        # run. Note that if you change your encoder, you might have to
        # change whatever post-encode tasks you run if they depend on the
        # previous file format! Scheduled on a per-file basis.
        'post_encode': [
        ],
        # post_finished tasks run on all files once all files have been
        # ripped and encoded. It is given the filenames of each encoded
        # file either individually, in which case it runs per-file, or
        # in aggregate, in which case it is run once for all files. If
        # both arguments are given, both will be expanded but the
        # command will be run once for each file. Scheduled exactly
        # once. NOTE: currently we try to find ${one_file} just by naive
        # string search so hope you didn't need that in your paths.
        # NOTE: ${all_files} is really hacky and probably won't work
        # unless it's the only thing in its parameter. Which should make
        # sense considering they're all separate parameters (this isn't
        # shell, spaces aren't separators)
        'post_finished': [
        ],
        # Only path to be configured for cdparanoia
        'cdparanoia': 'cdparanoia',
        # How to construct the name of each file.
        # You get a limited amount of variables to use here:
        # $home - the executing user's home directory
        # $album - album name from tags
        # $artist - song artist from tags.
        # $albumartist - albumartist from tags. This can also in reality
        #                be the artist tag but in that case the
        #                difference doesn't exist.
        # $xdgmusic - XDG_MUSIC_DIR. If the environment variable is
        #             unset, this is the same as $home/Music.
        # $tracknumber - number of the track on the album. Always two
        #                digits, unless the album has over 99 tracks, in
        #                which case the tracks beyond 99 have 3 digits.
        # $track - name of the track on the album.
        #
        # Note that this path must be absolute. More variables might
        # become available. Any directories on the path will be created
        # with default permissions. This allows you to make your music
        # directory structure as flat or spread out as you want. All
        # data from tags is subjected to the name safety filter before
        # it is allowed here.
        'target_template': '${xdgmusic}/${albumartist}/${album}/${tracknumber} - ${track}.mp3',
        # Controls whether the albumartist tag is always added, even
        # when the album is single-artist.
        'always_tag_albumartist': False,
        # The editor to be used. Defaults to the environment variable
        # EDITOR, or vim if undefined. If you don't have vim either,
        # well... You can always configure this option.
        'editor': os.environ.get('EDITOR', 'vim'),
        # How to safety filter data to be put in filenames.
        # NOTE: All of these filters *discard any characters that don't
        # pass the filter*! Note also that these are not sequentially
        # more or less restrictive ones: For instance,
        # unicode_letternumber removes *all* punctuation, even when
        # other filters would allow it. This filter may be redesigned,
        # however.
        # Options:
        # ascii - only allow 7-bit ASCII.
        # windows1252 - only allow valid Windows-1252 characters.
        # unicode_letternumber - only allow codepoints in the Letter and
        #                        Number categories in Unicode (those
        #                        with character properties Lu, Ll, Lt,
        #                        Lm, Lo, Nd, Nl and No). Rationale:
        #                        If a song's name contains several
        #                        non-latin-alphabet character, they are
        #                        most likely these, and these are the
        #                        most likely to be typeable in reality.
        # remove_restricted - remove restricted symbols from path.
        #                     NOTE: This filter is *always* run as a
        #                     part of the other filters.
        #
        # The filter cannot be completely disabled, because some
        # characters are never allowed in paths.
        'safetyfilter': 'remove_restricted',
        # Whether to lookup stuff from MusicBrainz by default
        'use_musicbrainz': True,
        # If album data exists, whether to use it by default
        'reuse_albumdata': True,
        # If True, temporary rip directory is deleted after rip
        # succesfully finished (but not otherwise)
        'keep_ripdir': False
    }

    def __init__(self):
        """Initialize configuration.

        Raises ConfigError on failure.
        """

        config_dir_name = 'cdparacord'
        config_dir = os.path.join(XDG_CONFIG_HOME, config_dir_name)
        config_file_name = 'config.yaml'
        config_file = os.path.join(config_dir, config_file_name)
        try:
            # We try to make it with the mode u=rwx,go= (but if it exists
            # with any other mode, that's fine, that's the user's choice)
            os.makedirs(config_dir, 0o700, exist_ok=True)
        except OSError:
            raise ConfigError('Could not create configuration directory')

        # Load default config
        # Here we take a deepcopy so any instance cannot mutate the
        # class default configuration by accident. Note that it can
        # still be mutated, just not through Config.get()
        self._config = deepcopy(Config.__default_config)

        # Now we check if the file exists.
        # There are two obvious race conditions here:
        #
        # - File does not exist but is created
        #
        #   This one is okay, because we'll just use the default
        #   configuration, and you can abort the execution to load the
        #   new config anyway.
        #
        # - File exists but is deleted before we open it
        #
        #   This one is more problematic; We *could* just go with the
        #   default config if the file is suddenly gone, as well, but I
        #   think it's safer if we instead consider this to be Weird and
        #   error out of here. Because of the exception, the object
        #   should not be constructed even if the object is caught.
        if os.path.isfile(config_file):
            try:
                with open(config_file, 'r') as f:
                    loaded = yaml.safe_load(f)
                    # Update configuration with the keys we loaded now
                    # Loudly announce any odd keys (but those are not an
                    # error so it's okay)
                    if (loaded is not None) and (type(loaded) is not dict):
                        raise ConfigError(textwrap.dedent("""\
                                Configuration file's
                                contents were of type {} (empty or one
                                YAML document containing a dict
                                expected)"""))
                    self.update(loaded, quiet_ignore=False)
            except OSError:
                raise ConfigError('Could not open configuration file')


    def get(self, key):
        """Fetch a configuration value.

        NOTE: Unlike dict.get, Config.get throws KeyError on access!
        (Indeed, the KeyError originates in a direct access to the
        dictionary.) This is intentional and derives from the idea that
        the default config should contain all the variables the program
        would ever access, even if empty, serving as a documentation for
        them. Therefore running the program with no configuration file
        would either function correctly (in the absence of KeyErrors) or
        fail to do so (because a nonexistent configuration value was
        requested).

        It's also worth noting that the program can mutate whatever
        mutable values are stored here. This doesn't seem worthwile to
        defend against, considering this software is the only consumer
        of its own settings. If it however turns out to be an issue,
        something *could* be done I suppose.
        For now, the only safeguard is a deep copy to guard against
        accidentally mutating the default configuration (which would
        then affect *future* instances). This may seem like a weird
        choice, but it is in fact exactly equivalent to initialising the
        default config for each object separately in __init__.
        """
        return self._config[key]

    def update(self, d, *, quiet_ignore=True):
        """Update configuration from provided dict.

        If quiet_ignore is False, messages will be printed to stderr
        when unknown keys are encountered.

        Only keys that already exist in the configuration are updated:
        No keys that don't exist in the dict already are changed. This
        is strictly because update is designed to be used to update the
        values from command-line options given in the main function,
        wherein such keys might be given; And to update the
        configuration from the custom configuration file, wherein they
        are probably either a typo or a misremembered option.
        """
        for key in d:
            if key in self._config:
                if d[key] is not None:
                    self._config[key] = d[key]
            elif not quiet_ignore and key not in self._config:
                print('Warning: Unknown configuration key {}'.format(key),
                    file=sys.stderr)
