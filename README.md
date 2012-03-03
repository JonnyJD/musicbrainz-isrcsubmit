Isrcsubmit for MusicBrainz
==========================

This python script extracts
[ISRCs](http://en.wikipedia.org/wiki/International_Standard_Recording_Code)
from audio cds
and submits them to [MusicBrainz](http://musicbrainz.org).


Usable backends:
---------------

* [Cdrdao](http://en.wikipedia.org/wiki/Cdrdao)
* Cdda2wav (in [cdrtools](http://en.wikipedia.org/wiki/Cdrtools))
* Icedax (in [cdrkit](http://en.wikipedia.org/wiki/Cdrkit))


features:
--------

* read ISRCs from disc
* search for releases with the TOC of the disc
* display release information from MB
* submit ISRCs
* submit discIds / TOCs
* duplicate ISRC detection (local and on server)


usage:
-----

    isrcsubmit.py [-d] username [device]

That is the username at musicbrainz and the device should be something like
`/dev/cdrom` (default) or `/dev/dvdrw`.
Some cd readers report the same ISRCs for different (adjacent) tracks.
Others don't, for the same physical disc.
For me my dvd writer worked better.

Isrcsubmit checks for problems with duplicate ISRCs and prints a warning.
You will always have the choice to cancel the submission if something
seems wrong.

If the disc is known to MusicBrainz, additional information about it
is fetched from MusicBrainz.
If the disc is unknown, you will be given the chance to submit the ID
to the server.


help:
-----

    isrcsubmit.py -h


The script runs on Python version 2 and is tested with Python 2.7

-

In order to submit ISRCs to musicbrainz.org you need to have a user acount.
You can create an account at http://musicbrainz.org/register free of charge.

The core of the MusicBrainz dataset including the ISRC contributions is placed
into the Public Domain.

-

You might find additional information about this script at the
[MusicBrainz forums](http://forums.musicbrainz.org/viewtopic.php?id=1908).

Please report bugs on
[GitHub](https://github.com/JonnyJD/musicbrainz-isrcsubmit).
