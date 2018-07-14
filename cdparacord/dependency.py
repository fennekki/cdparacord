"""The module for finding external dependencies."""

import os
from .error import CdparacordError


class DependencyError(CdparacordError):
    pass


class Dependency:
    """A class for ensuring dependencies exist and are available.

    This essentially performs partial configuration validation, because
    most of the external dependencies are configurable.
    """
    def __init__(self, config):
        self._config = config
        self._discover()

    def _find_executable(self, name):
        """Locate an executable and return its path if it exists."""
        # isfile checks both that file exists and is a file, os.access
        # with X_OK checks file has executable bit
        if os.path.isfile(name) and os.access(name, os.X_OK):
            # We got a full path, or a relative path from the current
            # dir. I don't think anyone wants that but they... might...
            return name

        for path in os.environ['PATH'].split(os.pathsep):
            path = path.strip('"')
            binname = os.path.join(path, name)
            if os.path.isfile(binname) and os.access(binname, os.X_OK):
                return binname

        # If we haven't returned, the executable was not found
        raise DependencyError(
            'Executable {} not found or not executable'.format(name))

    def _verify_action_params(self, action):
        """Confirm certain things about action configuration."""
        if len(action) > 1:
            multiple_actions = ', '.join(action.keys())
            raise DependencyError(
                'Tried to configure multiple actions in one dict: {}'
                    .format(multiple_actions))

        if len(action) < 1:
            raise DependencyError(
                'Configuration opened an action dict but it had no keys')

        action_key = list(action.keys())[0]
        action_params = action[action_key]

        if type(action_params) is not list:
            raise DependencyError(
                '{} configuration has type {} (list expected)'
                    .format(action_key, type(action_params).__name__))

        for item in action_params:
            if type(item) is not str:
                raise DependencyError(
                    'Found {} parameter {} with type {} (str expected)'
                        .format(action_key, item, type(item).__name__))

    def _discover(self):
        """Discover dependencies and ensure they exist."""

        # Find the executables, and verify parameters for post-actions
        # and encoder
        self._encoder = self._find_executable(
            list(self._config.get('encoder').keys())[0])

        self._verify_action_params(self._config.get('encoder'))

        self._editor = self._find_executable(self._config.get('editor'))
        self._cdparanoia = self._find_executable(
            self._config.get('cdparanoia'))

        for post_action in ('post_rip', 'post_encode', 'post_finished'):
            for action in self._config.get(post_action):
                self._find_executable(list(action.keys())[0])
                self._verify_action_params(action)

        # Ensure discid is importable
        try:
            import discid
        # We don't need to coverage test this exception automatically;
        # it would be ridiculous as it only depends on documented
        # behaviour and only raises a further exception.
        except OSError as e:  # pragma: no cover
            raise DependencyError('Could not find libdiscid') from e

    @property
    def encoder(self):
        return self._encoder

    @property
    def editor(self):
        return self._editor

    @property
    def cdparanoia(self):
        return self._cdparanoia
