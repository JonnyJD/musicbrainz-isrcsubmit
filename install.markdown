---
layout: default
title: install
---
installation
------------

The script itself does not need any installation
other than making it executable on Linux:

    $ chmod a+x isrcsubmit.py

However, the backends and libraries should get installed so that the
script has access to them.

On Linux you just install [python-musicbrainz2](http://musicbrainz.org/doc/python-musicbrainz2)
and one of the backends with the package manager of your distribution.

On Windows and Mac you have to put the musicbrainz2 folder of python-musicbrainz2 in the same directory as this script or adjust the python path.
On Windows you also have to install a backend in the PATH or the same directory as the script.
The best backend is mediatools, but you can download a
[windows build of cdrdao](http://www.student.tugraz.at/thomas.plank/).
On Mac drutil is part of the Mac OS X.
