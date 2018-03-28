"""System for configuring cdparacord."""

import os
import yaml
from copy import deepcopy
from .error import CdparacordError
from .xdg import XDG_CONFIG_HOME

class ConfigError(CdparacordError):
    """Raised on configuration error."""
    pass

# Intentionally accessed like this because we probably need to crash if
# $HOME isn't defined.

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
    __default_config = {
        # Config for the encoder
        'encoder': {
            'executable': 'lame',
            'parameters': [
                '-V2'
            ]
        },
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
        'safetyfilter': 'unicode_letternumber'
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
        config = deepcopy(Config.__default_config)

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
        #   error out of here.
        if os.path.isfile(config_file):
            try:
                with open(config_file, 'r') as f:
                    loaded = yaml.safe_load(f)
                    # Update configuration with the keys we loaded now
                    config.update(loaded)
            except OSError:
                raise ConfigError('Could not open configuration file')

        self.__config = config

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
        return self.__config[key]
