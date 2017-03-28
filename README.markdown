# cdparacord

`cdparacord` is a quick and dirty cdparanoia wrapper I wrote
because apparently abcde is hot trash and breaks on non-ASCII
characters.

## Requirements

`cdparacord` requires you to have installed `lame` (the LAME
MP3 encoder executable), `libdiscid` (for detecting the disc
ID of the CD in the drive) and `cdparanoia` itself. The
`cdparanoia` and `lame` binaries are searched for at at runtime
by going through the `PATH` environment variable - if your
copies of these binaries are not called exactly the names I use
here, you will have to modify cdparacord to search for the
correct filenames. The `libdiscid` library is not explicitly
checked for and need only be  somewhere your OS linker can find
it.

There are no version checks built into `cdparacord`; If a
specific version of `lame`, `libdiscid` or `cdparanoia`
causes it to malfunction, please file a bug.
