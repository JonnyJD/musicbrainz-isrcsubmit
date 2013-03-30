Isrcsubmit 2.0.0 for MusicBrainz
==============================
(Linux/Mac OS X/Windows)
------------------------

This python script extracts
[ISRCs](http://en.wikipedia.org/wiki/International_Standard_Recording_Code)
from audio cds
and submits them to [MusicBrainz](http://musicbrainz.org).

This script uses
[python-musicbrainzngs](http://musicbrainz.org/doc/python-musicbrainz-ngs)
to access the MusicBrainz API
and [python-discid](https://python-discid.readthedocs.org/)
to create an identifier for the disc.
You need Python 2 >= 2.6.

The script works for Linux, Mac OS X and Windows.


Usable backends:
---------------

* [mediatools](http://www.flanagan-family.com/mediatools.zip)
* [Cdrdao](http://en.wikipedia.org/wiki/Cdrdao)
* discisrc ([mac build](http://isrcsubmit.jonnyjd.net/downloads/discisrc-mac.zip), others can be built from [libdiscid](https://github.com/metabrainz/libdiscid))
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

Mac users should rather use **isrcsubmit.sh**, which also works on Linux.
Windows users should use **isrcsubmit.bat**.

That is the username at musicbrainz and the device should be something like
`/dev/cdrom` (default), `/dev/dvdrw`, a drive letter (on Windows)
or a number (Mac OS X).
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

The script itself does not need any installation,
but "python2 setup.py install" might work for you.
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
