---
layout: default
title: install
---
installation
------------

The script itself does not need any installation
other than making it executable on Linux:

    $ chmod a+x isrcsubmit.py

However, the libraries should get installed so that the
script has access to them.

You need
[python-musicbrainzngs](http://python-musicbrainzngs.readthedocs.org)
and
either [python-discid](http://python-discid.readthedocs.org)
or [python-libdiscid](http://pythonhosted.org/python-libdiscid/).

On Windows and Mac OS X it is recommended to download
the [binary packages of isrcsubmit](download).
These include all dependencies.

On Linux you should use find the dependencies
with the software management tool of your distribution.
If you can't find these packages you can try using [isrcsubmit 1](download#old),
which only depends on python-musicbrainz2 and libdiscid.
