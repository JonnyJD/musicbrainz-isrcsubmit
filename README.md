Isrcsubmit 0.5.2 for MusicBrainz
==============================
(Linux/Mac OS X/Windows)
------------------------

This python script extracts
[ISRCs](http://en.wikipedia.org/wiki/International_Standard_Recording_Code)
from audio cds
and submits them to [MusicBrainz](http://musicbrainz.org).

This script currently uses
[python-musicbrainz2](http://musicbrainz.org/doc/python-musicbrainz2)
to access the MusicBrainz API.
Python2 >= 2.4 should be fine for both.
You also need [libdiscid](http://jonnyjd.github.com/musicbrainz-isrcsubmit/libdiscid) and with python < 2.5 you also need [ctypes](http://starship.python.net/crew/theller/ctypes/).

The script works for Linux, Mac OS X and Windows. However, drutils, the backend for Mac WILL take a long time (several minutes) per disc and might give duplicates more often. Isrcsubmit will tell you about it though.


Usable backends:
---------------

* [mediatools](http://www.flanagan-family.com/mediatools.zip)
* [Cdrdao](http://en.wikipedia.org/wiki/Cdrdao)
* cd-info ([libcdio](http://www.gnu.org/software/libcdio/))
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

    isrcsubmit.py [options] [username] [device]

for detailed usage see:

    isrcsubmit.py -h

That is the username at musicbrainz and the device should be something like
`/dev/cdrom` (default), `/dev/dvdrw` or a drive letter (on Windows).
Some cd readers report the same ISRCs for different (adjacent) tracks.
Others don't, for the same physical disc.
For me my dvd writer worked better.
On Windows the mediatools backend should give correct results either way.

Isrcsubmit checks for problems with duplicate ISRCs and prints a warning.
You will always have the choice to cancel the submission if something
seems to be wrong.

If the disc is known to MusicBrainz, additional information about it
is fetched from MusicBrainz.
If the disc is unknown, you will be given the chance to submit the ID
to the server.


help:
-----

    isrcsubmit.py --help


"installation":
---------------

The script itself does not need any installation.
However, the backends and libraries should get installed so that the
script has access to them.

On Linux you just install python-musicbrainz2 and one of the backends with the package manager of your distribution.

On Windows and Mac you have to put the musicbrainz2 folder of python-musicbrainz2 in the same directory as this script or adjust the python path.
On Windows you also have to install a backend in the PATH or the same directory as the script.
The best backend is mediatools, but you can download a
[windows build of cdrdao](http://www.student.tugraz.at/thomas.plank/).
On Mac drutil is part of the Mac OS X.


-

In order to submit ISRCs to musicbrainz.org you need to have a user acount.
You can create an account at http://musicbrainz.org/register free of charge.

The core of the MusicBrainz dataset including the ISRC contributions is placed
into the Public Domain.

-

You might find additional information about this script at the
[MusicBrainz forums](http://forums.musicbrainz.org/viewtopic.php?id=3444).

Please report bugs on
[GitHub](https://github.com/JonnyJD/musicbrainz-isrcsubmit).
