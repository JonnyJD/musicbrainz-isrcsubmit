Isrcsubmit 0.4 for MusicBrainz
==============================
(Linux/Mac OS X)
----------------

This python script extracts
[ISRCs](http://en.wikipedia.org/wiki/International_Standard_Recording_Code)
from audio cds
and submits them to [MusicBrainz](http://musicbrainz.org).

This script currently uses
[python-musicbrainz2](http://musicbrainz.org/doc/python-musicbrainz2)
to access the MusicBrainz API.
Python2 >= 2.4 should be fine for both.
You also need [libdiscid](https://github.com/JonnyJD/musicbrainz-isrcsubmit/wiki/libdiscid) and with python < 2.5 you also need [ctypes](http://starship.python.net/crew/theller/ctypes/).

The script works for Linux and Mac OS X. However, drutils, the backend for Mac WILL take a long time (several minutes) per disc and might give duplicates more often. Isrcsubmit will tell you about it though.


Usable backends:
---------------

* [Cdrdao](http://en.wikipedia.org/wiki/Cdrdao)
* Cdda2wav (in [cdrtools](http://en.wikipedia.org/wiki/Cdrtools))
* Icedax (in [cdrkit](http://en.wikipedia.org/wiki/Cdrkit))
* drutil (in Mac OS X)


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

    isrcsubmit.py [options] username [device]

for detailed usage see:

    isrcsubmit.py -h

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

    isrcsubmit.py --help



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
