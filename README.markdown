[![Build Status](https://travis-ci.org/fennekki/cdparacord.svg?branch=master)](https://travis-ci.org/fennekki/cdparacord)
[![Coverage Status](https://coveralls.io/repos/github/fennekki/cdparacord/badge.svg?branch=master)](https://coveralls.io/github/fennekki/cdparacord?branch=master)
# cdparacord

Cdparacord is a wrapper for cdparanoia to ease the process of ripping, encoding
and tagging music. It was initially created as a quick and dirty hack to run
cdparanoia and LAME but is slowly accumulating more features

## Usage

```
Usage: cdparacord [OPTIONS] [BEGIN_TRACK] [END_TRACK]

  Rip, encode and tag CDs and fetch albumdata from MusicBrainz.

  If only BEGIN_TRACK is specified, only the specified track will be ripped.
  If both BEGIN_TRACK and END_TRACK are specified, the range starting from
  BEGIN_TRACK and ending at END_TRACK will be ripped. If neither is
  specified, the whole CD will be ripped.

  Cdparacord creates a temporary directory under /tmp, runs cdparanoia to
  rip discs into it and copies the resulting encoded files to the target
  directory configured in the configuration file.

  See documentation for more.

Options:
  -r, --keep-ripdir / -R, --no-keep-ripdir
                                  Keep temporary ripping directory after rip
                                  finishes.
  -a, --reuse-albumdata / -A, --no-reuse-albumdata
                                  Use albumdata from a previous rip if present
  -m, --use-musicbrainz / -M, --no-use-musicbrainz
                                  Fetch albumdata from MuzicBrainz
                                  if
                                  available
  -c, --continue                  Continue rip from existing ripdir if ripdir
                                  is present (By default
                                  the rip is restarted)
  --help                          Show this message and exit.
```

## Requirements

Cdparacord requires at least Python 3.5 for async.

By default it requires LAME for encoding. You can, however, customise the
encoder as you see fit, though configuration documentation is currently scarce.
See config.py for more.

Additionally, libdiscid0 (0.6.2 known to work) is needed for extracting disc
ids sent to MusicBrainz, and cdparanoia (10.2 known to work) for the actual
ripping.

You need the `cdparanoia` and encoder applications to either be in your
executable search path or specified in the configuration with their full paths.

There are no version checks built into `cdparacord`; If a specific version of
libdiscid0 or cdparanoia causes it to malfunction, please file a bug.

## Configuration

This documentation is work in progress. See config.py for extant documentation
on configuration.

The cdparacord configuration file is located at
`$XDG_CONFIG_HOME/cdparacord/config.yaml`. `$XDG_CONFIG_HOME` is a standard
configuration directory and defaults to `$HOME/.config`.
