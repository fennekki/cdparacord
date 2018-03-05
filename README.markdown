[![Build Status](https://travis-ci.org/fennekki/cdparacord.svg?branch=master)](https://travis-ci.org/fennekki/cdparacord)
[![Coverage Status](https://coveralls.io/repos/github/fennekki/cdparacord/badge.svg?branch=master)](https://coveralls.io/github/fennekki/cdparacord?branch=master)
# cdparacord

Cdparacord is a wrapper for cdparanoia to ease the process of ripping, encoding
and tagging music. It was initially created as a quick and dirty hack to run
cdparanoia and LAME but is slowly accumulating more features

## Usage

```
cdparacord [ start-track [ end-track ] ]
```

`start-track` is a digit from 1 to the number of tracks on the album. If
`end-track` is specified, cdparacord will rip all tracks from `start-track` to
`end-track`, otherwise it will only rip `start-track`. If neither is provided,
cdparacord will rip the whole album.

Cdparacord tries to fetch tags from MusicBrainz, and lets you pick whichever
match you prefer. Once you pick your preferred pre-filled tags or no matches
are found, you will be dropped to a text editor, and shown either pre-filled or
empty tag information, in the following format:

```
ALBUMARTIST=Example Artist
TITLE=Example Album
DATE=1970-01-01
TRACK_COUNT=2

TRACK=Example Track
ARTIST=Example Artist

TRACK=Example Track 2
ARTIST=Example Artist 2 feat. Example Artist 2
```

You should edit any fields you feel dissatisfied with. After closing the text
editor, the rip will begin.

## Requirements

Cdparacord requires at least Python 3.5 for async.

It requires LAME (3.99.5 is known to work) for encoding (though custom encoder
support is Coming, see Bug #19).

Additionally, libdiscid0 (0.6.2 known to work) is needed for extracting disc
ids sent to MusicBrainz, and cdparanoia (10.2 known to work) for the actual
ripping.

The `cdparanoia` and `lame` executables need to be in your executable search
path (You will be able to manually configure their locations later, see Bugs
 #19, #21).

There are no version checks built into `cdparacord`; If a specific version of
LAME, libdiscid0 or cdparanoia causes it to malfunction, please file a bug.

## Known issues

Even if ripping individual tracks, the target directory existing will terminate
the rip (Bugs #9, #10).

The text editor is hardcoded to be vim (Bug #4).

Albumartist tags are only created if one or more tracks have a different
`ARTIST` value than the `ALBUMARTIST` value (Bug #6). This also applies to
ripping less than the entire album, and whether or not said tracks are the
tracks being ripped.

You are not asked if you wish to proceed after closing the text editor (Bug
 #1). Additionally, if you input incorrect information or otherwise terminate
the rip, you will lose the data you input (Bug #3). The rip cannot be restarted
without removing the target directory (Bugs #9, #10) and cannot be restarted
with existing data (Bug #11). The rip cannot be resumed if terminated (Bug
 #12).

The encoder is fixed to LAME with the quality parameter `-V2` (Bug #19).

The directory and filename to put music in is fixed to
`~/Music/$albumartist/$album/$trackno - $trackname.mp3` (Bug #20).

Some "special" characters are ripped from the filenames but their treatment is
inconsistent, the filtering is too little for filesystems that can't handle
Unicode, and it might be too much for you (Bug #16).

After cdparacord puts you in vim, there's no way to terminate cdparacord before
it starts ripping other than inputting erroneous data (which you will
subsequently lose) (Bug #1).

The existence of cdparanoia is checked relatively late (Bug #2).
