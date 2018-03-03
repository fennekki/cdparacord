"""System for configuring cdparacord."""

import yaml
import os
from .error import CdparacordError
from xdg import XDG_CONFIG_HOME

class ConfigError(CdparacordError):
    """Raised on configuration error."""
    pass

class Config:
    """Represents the configuration of the program.

    The functionality is partially in the class and partially in the
    instance, for no reason in particular.
    """
    config_dir_name = 'cdparacord'
    config_dir = os.path.join(XDG_CONFIG_HOME, Config.config_dir_name)
    config_file_name = 'config.yaml'
    config_file = os.path.join(config_dir, config_file_name)

    # TODO: Put this somewhere else
    default_config = {
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
        config = Config.default_config.copy()

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
