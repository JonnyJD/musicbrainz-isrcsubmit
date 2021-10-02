Isrcsubmit 2.2.1 for MusicBrainz
================================

This project includes two python scripts that extracts ISRCs
and submits them to MusicBrainz_. isrcsubmit extracts ISRCs from
Audio CDs. isrcDigitalSubmit extracts ISRCs from audio files.

These scripts use python-musicbrainzngs to access the MusicBrainz API.

isrcsubmit uses python-discid to create an identifier for the disc which
is used to locate corresponding releases in MusicBrainz. 

isrcDigitalSubmit uses mutagen to analyze audio files, and locates matching
MusicBrainz releases based on embedded Artist, Album and AlbumArtist tags.

The script works for Linux, Mac OS X and Windows.

.. _ISRCs: http://en.wikipedia.org/wiki/International_Standard_Recording_Code
.. _MusicBrainz: http://musicbrainz.org

Features:
---------

* read ISRCs from disc or audio files
* search for releases with the TOC of the disc or embedded tags
* display release information from MusicBrainz
* submit ISRCs
* submit discIds / TOCs (isrcsubmit)
* duplicate ISRC detection (local and on server)


Dependencies:
-------------

* Python 2 >= 2.6 or Python 3 >= 3.1
* python-discid_ >= 1.0.0 (or python-libdiscid_ >= 0.2.0)
* python-musicbrainzngs_ >= 0.4
* mutagen_ >= 1.45.1
* unidecode >= 1.2.0
* keyring_ (optional)

.. _python-discid: http://python-discid.readthedocs.org/
.. _python-libdiscid: http://pythonhosted.org/python-libdiscid/
.. _python-musicbrainzngs: http://python-musicbrainzngs.readthedocs.org/
.. _keyring: https://github.com/jaraco/keyring/
.. _mutaagen: https://mutagen.readthedocs.io/
.. _unicode: https://github.com/avian2/unidecode

Usage:
------
::

    isrcsubmit.py [options] [username] [device]
    isrcDigitalSubmit.py [options] [username] audioFiles ...

All arguments are optional other than audioFiles for isrcDigitalSubmit.
AudioFiles may be zipped (so a ZIP file as distributed by the vendor can
usually be passed directly to the script).

For detailed usage see::

    isrcsubmit.py -h
    isrcDigitalSubmit.py -h


Windows Usage:
--------------

Windows users should use::

    isrcsubmit.bat
    isrcDigitalSubmit.bat


Mac Usage:
----------

Mac users should rather use::

    isrcsubmit.sh
    isrcDigitalSubmit.sh

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

Identifying Releases from Tags
------------------------------

A Digital Media release has no equivalent of a DiscID as defined for CDs.
Instead, it uses tags that are embedded in the digital media files. The
tags of interest are Album, AlbumArtist, Artist and TrackNumber. (Other
formats eg. MP3 might name these different; this discussion will use the
Vorbis tag names).

Identifying a release is most straightforward if the albumartist tag is found. 
The same albumartist tag must be on all tracks. isrcDigitalSubmit will look for
a Digital Media release with that album artist and title. If more than one is found,
the user will be asked to choose.

If no Album Artist is found, the artist will be treated as an album artist. 
An attempt is made to strip away any "featured artist" from tracks, either by looking
for connectors like "feat." or "duet with", or by checking for a common name that
is found on all artist name strings. If it can't identify a single artist, it will
look for a release without specifying an artist.

If all else fails, the user can point the script to a specific release by use of
the --release-id= option.

isrcDigitalRelease always verifies that the digital media release matches the MusicBrainz
release by checking for matching titles and artists and similar track times. It also
verifies that the format is "Digital Media"; it will not attach
ISRCs to releases with a different format.


Installation:
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

On Linux you just install the above mentioned dependencies with
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
.. _MusicBrainz forums: https://community.metabrainz.org/search?q=isrcsubmit


Bugs:
-----

Please report bugs on GitHub_.

.. _GitHub: https://github.com/JonnyJD/musicbrainz-isrcsubmit


License:
--------

GNU General Public License Version 3 or later
