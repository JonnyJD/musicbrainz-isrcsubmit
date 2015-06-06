Isrcsubmit 2.0.1 for MusicBrainz
================================

This python script extracts ISRCs_ from audio CDs
and submits them to MusicBrainz_.

This script uses python-musicbrainzngs to access the MusicBrainz API
and python-discid to create an identifier for the disc.

The script works for Linux, Mac OS X and Windows.

.. _ISRCs: http://en.wikipedia.org/wiki/International_Standard_Recording_Code
.. _MusicBrainz: http://musicbrainz.org

Features:
---------

* read ISRCs from disc
* search for releases with the TOC of the disc
* display release information from MusicBrainz
* submit ISRCs
* submit discIds / TOCs
* duplicate ISRC detection (local and on server)


Dependencies:
-------------

* Python 2 >= 2.6 or Python 3 >= 3.1
* python-discid_ >= 1.0.0 (or python-libdiscid_ >= 0.2.0)
* python-musicbrainzngs_ >= 0.4
* keyring_ (optional)

.. _python-discid: http://python-discid.readthedocs.org/
.. _python-libdiscid: http://pythonhosted.org/python-libdiscid/
.. _python-musicbrainzngs: http://python-musicbrainzngs.readthedocs.org/
.. _keyring: https://bitbucket.org/kang/python-keyring-lib/


Usage:
------
::

    isrcsubmit.py [options] [username] [device]

All arguments are optional. For detailed usage see::

    isrcsubmit.py -h


Windows Usage:
--------------

Windows users should use::

    isrcsubmit.bat


Mac Usage:
----------

Mac users should rather use::

    isrcsubmit.sh

This also works on Linux.


Duplicate ISRCs:
----------------

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

You can install using pypi_ with::

    pip install isrcsubmit

This handles all python dependencies, but you still need to
install libdiscid (before running pip).

The script itself does not need any installation,
but "python setup.py install" might work for you.
However, the backends and libraries should get
installed so that the script has access to them.

On Linux you just install the above mentioneed dependencies with
the package manager of your distribution.
For Ubuntu all dependencies should be in the MusicBrainz Stable PPA,
if not in the official repositories.

On Windows and Mac you have to put the musicbrainzngs folder of
python-musicbrainzngs, discid of python-discid in the same
directory as this script or adjust the python path.
You also need to put discid.dll (Windows) and libdiscid.dylib.0 (Mac)
into this location or in the PATH.

.. _pypi: https://pypi.python.org/pypi


Additional information:
-----------------------

In order to submit ISRCs to musicbrainz.org you need to have a user acount.
You can create an account at http://musicbrainz.org/register free of charge.

The core of the MusicBrainz dataset including the ISRC contributions is placed
into the Public Domain.

For a documentation of the available backends please refer to the manual
or the `web page`_.

You might find additional information about this script at the
`MusicBrainz forums`_.

.. _web page: http://jonnyjd.github.io/musicbrainz-isrcsubmit/backends
.. _MusicBrainz forums: http://forums.musicbrainz.org/viewtopic.php?id=3444


Bugs:
-----

Please report bugs on GitHub_.

.. _GitHub: https://github.com/JonnyJD/musicbrainz-isrcsubmit


License:
--------

GNU General Public License Version 3 or later
