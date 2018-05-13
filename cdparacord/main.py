import os
import click
import shutil
from .albumdata import Albumdata
from .config import Config
from .dependency import Dependency
from .error import CdparacordError
from .rip import Rip


@click.command()
@click.argument('begin_track', type=int, required=False)
@click.argument('end_track', type=int, required=False)
@click.option('--keep-ripdir/--no-keep-ripdir', '-r/-R', default=None,
    help="""Keep temporary ripping directory after rip finishes.""")
@click.option('--reuse-albumdata/--no-reuse-albumdata', '-a/-A',
    default=None, help="""Use albumdata from a previous rip if present""")
@click.option('--use-musicbrainz/--no-use-musicbrainz', '-m/-M',
    'use_musicbrainz', default=None, help="""Fetch albumdata from MuzicBrainz
    if available""")
@click.option('--continue', '-c', 'continue_rip', is_flag=True, default=False,
    help="""Continue rip from existing ripdir if ripdir is present (By default
    the rip is restarted) NOTE: DOES NOTHING YET""")
def main(begin_track, end_track, **options):
    """Rip, encode and tag CDs and fetch albumdata from MusicBrainz.

    If only BEGIN_TRACK is specified, only the specified track will be
    ripped. If both BEGIN_TRACK and END_TRACK are specified, the range
    starting from BEGIN_TRACK and ending at END_TRACK will be ripped. If
    neither is specified, the whole CD will be ripped.

    Cdparacord creates a temporary directory under /tmp, runs cdparanoia
    to rip discs into it and copies the resulting encoded files to the
    target directory configured in the configuration file.

    See documentation for more.
    """
    # Read configuration
    config = Config()
    # Update does not add new configuration options (because the way new
    # config is added is by adding new elements to the default config)
    config.update(options)

    # Discover dependencies
    deps = Dependency(config)

    # Ensure ripping directory exists and set relatively restrictive
    # permissions for it if it doesn't

    # Read albumdata from user and MusicBrainz
    albumdata = Albumdata.from_user_input(deps, config)
    if albumdata is None:
        print('User aborted albumdata selection.')
        return

    # Create the ripdir if we got albumdata
    os.makedirs(albumdata.ripdir, 0o700, exist_ok=True)

    # Choose which tracks to rip based on the command line.  The logic
    # is pretty straightforward: If we get neither argument, rip all. If
    # we get one argument, rip only that track. Otherwise rip the
    # inclusive range specified by the arguments.
    if begin_track is None:
        begin_track = 1
        end_track = albumdata.track_count
    elif end_track is None:
        end_track = begin_track

    if not (1 <= begin_track <= albumdata.track_count):
        raise CdparacordError(
            'Begin track {} out of range (must be between 1 and {})'
            .format(begin_track, albumdata.track_count))

    if not (begin_track <= end_track <= albumdata.track_count):
        raise CdparacordError(
            'End track out of range (Must be between begin track ({}) and {})'
            .format(begin_track, albumdata.track_count))

    print('Starting rip: tracks {} - {}'.format(begin_track, end_track))

    # Rip is the ripping and encoding process object
    # It deals with the rip queue, encoding, tagging
    rip = Rip(albumdata, deps, config, begin_track, end_track,
            options['continue_rip'])
    rip.rip_pipeline()

    # We have a flag to keep ripdir
    if not options['keep_ripdir']:
        print('Removing ripdir')
        shutil.rmtree(albumdata.ripdir)
    print('\n\nCdparacord finished.')

if __name__ == "__main__": # pragma: no cover
    main()
