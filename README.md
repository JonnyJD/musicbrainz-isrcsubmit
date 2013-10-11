Isrcsubmit 2.0.0-dev for MusicBrainz
================================
(Linux/Mac OS X/Windows)
------------------------

This python script extracts
[ISRCs](http://en.wikipedia.org/wiki/International_Standard_Recording_Code)
from audio CDs
and submits them to [MusicBrainz](http://musicbrainz.org).

This script uses
[python-musicbrainzngs](http://musicbrainz.org/doc/python-musicbrainz-ngs) >= 0.4
to access the MusicBrainz API
and [python-discid](https://python-discid.readthedocs.org/) >= 1.0.0
to create an identifier for the disc.
You need Python 2 >= 2.6 or Python 3 >= 3.1.

The script works for Linux, Mac OS X and Windows.


Features:
--------

* read ISRCs from disc
* search for releases with the TOC of the disc
* display release information from MB
* submit ISRCs
* submit discIds / TOCs
* duplicate ISRC detection (local and on server)


Dependencies:
-------------

* Python 2 >= 2.6 or Python 3 >= 3.1
* python-discid >= 1.0.0 (or python-libdiscid >= 0.2.0)
* python-musicbrainzngs


Usage:
------

    isrcsubmit.py [options] [username] [device]

for detailed usage see:

    isrcsubmit.py -h

Mac users should rather use **isrcsubmit.sh**, which also works on Linux.
Windows users should use **isrcsubmit.bat**.

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


"Installation":
---------------

If you downloaded isrcsubmit as a zip package for your platform
then you only need to extract that somewhere and start using it.
You can also stop reading this section.

The script itself does not need any installation,
but "python2 setup.py install" might work for you.
However, the backends and libraries should get
installed so that the script has access to them.

On Linux you just install the above mentioneed dependencies with
the package manager of your distribution.
For Ubuntu all dependencies should be in the MusicBrainz Stable PPA,
if not in the official repositories.

On Windows and Mac you have to put the musicbrainzngs folder of
python-musicbrainzngs in the same directory as this script or
adjust the python path.


Additional information:
-----------------------

In order to submit ISRCs to musicbrainz.org you need to have a user acount.
You can create an account at http://musicbrainz.org/register free of charge.

The core of the MusicBrainz dataset including the ISRC contributions is placed
into the Public Domain.

You might find additional information about this script at the
[MusicBrainz forums](http://forums.musicbrainz.org/viewtopic.php?id=3444).


Bugs:
-----

Please report bugs on
[GitHub](https://github.com/JonnyJD/musicbrainz-isrcsubmit).
