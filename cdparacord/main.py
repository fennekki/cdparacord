import os
import string
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
@click.option('--keep-ripdir/--no-keep-ripdir', '-K', default=False,
        help="""Keep temporary ripping directory after rip finishes.
        (Default: --no-keep-ripdir)""")
def main(begin_track, end_track, keep_ripdir):
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

    # Discover dependencies
    deps = Dependency(config)

    # Ensure ripping directory exists and set relatively restrictive
    # permissions for it if it doesn't
    ripdir = '/tmp/cdparacord/{uid}-{discid}'.format(
        uid=os.getuid(),
        discid=final['discid'])
    os.makedirs(ripdir, 0o700, exist_ok=True)

    # Read albumdata from user and MusicBrainz
    albumdata = Albumdata(deps, config, ripdir)

    # Choose which tracks to rip based on the command line.  The logic
    # is pretty straightforward: If we get neither argument, rip all. If
    # we get one argument, rip only that track. Otherwise rip the
    # inclusive range specified by the arguments.
    if begin_track is None:
        begin_track = 1
        end_track = albumdata.track_count
    elif end_track is None:
        end_track = begin_track

    if begin_track < 1 or begin_track > albumdata.track_count:
        raise CdparacordError(
            'Begin track {} out of range (must be between 1 and {})'
            .format(begin_track, albumdata.track_count))

    if end_track < begin_track or end_track > albumdata.track_count:
        raise CdparacordError(
            'End track out of range (Must be between begin track ({}) and {})'
            .format(begin_track, albumdata.track_count))

    print('Starting rip: tracks {} - {}'.format(begin_track, end_track))

    # Rip is the ripping and encoding process object
    # It deals with the rip queue, encoding, tagging
    rip = Rip(albumdata, deps, config, ripdir, begin_track, end_track)
    rip.rip_pipeline()

    # We have a flag to keep ripdir
    if not keep_ripdir:
        print("Removing ripdir")
        shutil.rmtree(ripdir)
    print("\n\nCdparacord finished.")

if __name__ == "__main__":
    main()
