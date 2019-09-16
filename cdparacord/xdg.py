"""XDG-related functions."""
import os


# Using or here so that we don't need to try and find $HOME if the prior
# is configured. We don't *necessarily* need $HOME here.
XDG_CONFIG_HOME: str = (os.environ.get('XDG_CONFIG_HOME') or
    os.path.join(os.environ['HOME'], '.config'))

XDG_MUSIC_DIR: str = (os.environ.get('XDG_MUSIC_DIR') or
    os.path.join(os.environ['HOME'], 'Music'))
