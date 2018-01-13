# cdparacord

`cdparacord` is a wrapper for cdparanoia and LAME that rips, encodes and tags
the tracks off a CD, and can use MusicBrainz to automatically populate the tags.

It is, however, probably not very useful if you don't share my goals in using it
(see below).

## Requirements

`cdparacord` requires LAME (for encoding), libdiscid (for reading disc ids for
MusicBrainz), and cdparanoia (for the actual ripping).

The `cdparanoia` and `lame` executables need to be in your `$PATH`, and
`libdiscid.so` needs to be somewhere your linker can find it. Installing the
relevant packages via your package manager will do this just fine but if you eg.
have LAME in a non-standard location you will want to set `$PATH` before running
cdparacord.

There are no version checks built into `cdparacord`; If a specific version of
LAME, libdiscid or cdparanoia causes it to malfunction, please file a bug.

## Weird design choices

The software hardcodes my preferences for things like directory and file names
(`~/Music/Artist/Album/01 - Track.mp3`), LAME quality (`-V2`), how to replace
"special" characters in filenames, the use of vim as the text editor and that
albums that are single-artist shouldn't have the album artist tag. These are not
bugs, though they could be made configurable.

## Known issues

After cdparacord puts you in vim, there's no way to terminate cdparacord before
it starts ripping other than inputting erroneous data (which you will
subsequently lose).

If something fails after entering disc information in a text editor, you lose
the data you inputted. You can manually save it elsewhere to mitigate.

The existence of cdparanoia is checked relatively late.
