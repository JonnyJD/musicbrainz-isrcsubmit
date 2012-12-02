---
layout: default
title: libdiscid
---
## libdiscid
This library is needed by pyton-musicbrainz2 in order to get the ID
from the disc, which is then used to lookup the disc at
[MusicBrainz](http://musicbrainz.org).

### Linux
You should check if the package is in a repository for your distribution.
It often is.

### Mac OS X
There are
[Mac builds](https://github.com/downloads/JonnyJD/musicbrainz-isrcsubmit/libdiscid-0.2.2-mac.zip)
of this library available for Intel Macs (32 and 64 bit), PPC
and an universal library which works for all of these.

### Windows
There is a
[Windows build](https://github.com/downloads/JonnyJD/musicbrainz-isrcsubmit/libdiscid-0.2.2-win32.zip)
(32 bit) available.

### Compile it yourself
You can download the source at [libdiscid](http://wiki.musicbrainz.org/libdiscid) and compile and install it in a terminal:

    wget http://users.musicbrainz.org/~matt/libdiscid-0.2.2.tar.gz
    tar -xf libdiscid-0.2.2.tar.gz
    cd libdiscid-0.2.2
    ./configure
    make
    sudo make install
