"""System for configuring cdparacord."""

import os
import yaml
from copy import deepcopy
from xdg import XDG_CONFIG_HOME
from .error import CdparacordError

class ConfigError(CdparacordError):
    """Raised on configuration error."""
    pass

class Config:
    """Represents the configuration of the program.

    The functionality is partially in the class and partially in the
    instance, for no reason in particular.
    """
    __config_dir_name = 'cdparacord'
    __config_dir = os.path.join(XDG_CONFIG_HOME, Config.__config_dir_name)
    __config_file_name = 'config.yaml'
    __config_file = os.path.join(
            Config.__config_dir, Config.__config_file_name)

    # TODO: Put this somewhere else
    __default_config = {
        'lame':  {
            'executable': 'lame',
            'search_dirs': os.environ['PATH'].split(os.pathsep)
        },
        'cdparanoia': {
            'executable': 'cdparanoia',
            'search_dirs': os.environ['PATH'].split(os.pathsep)
        },
        '':
    }

    def __init__(self):
        """Initialize configuration.

        Raises ConfigError on failure.
        """
        try:
            # We try to make it with the mode u=rwx,go= (but if it exists
            # with any other mode, that's fine, that's the user's choice)
            os.makedirs(Config.config_dir, 0o700, exist_ok=True)
        except OSError:
            raise ConfigError('Could not create configuration directory')
        except:
            raise ConfigError('Unknown issue creating configuration directory')

        # Load default config
        # Here we take a deepcopy so any instance cannot mutate the
        # class default configuration by accident. Note that it can
        # still be mutated, just not through Config.get()
        config = Config.__default_config.deepcopy()

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
                    loaded = yaml.safe_load_all(f)
                    # Update configuration with the keys we loaded now
                    config.update(loaded)
            except OSError:
                raise ConfigError('Could not open configuration file')
        
        self.__config = config

    def get(key):
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
