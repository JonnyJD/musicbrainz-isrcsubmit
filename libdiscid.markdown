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
[Mac builds]({{ site.downloads.url }}libdiscid-0.2.2-mac.zip)
of this library available for Intel Macs (32 and 64 bit), PPC
and an universal library which works for all of these.

### Windows
There is a
[Windows build]({{ site.downloads.url }}libdiscid-0.3.0-win32.zip)
(32 bit) available.

### Compile it yourself
You can download the source at
[libdiscid](http://musicbrainz.org/doc/libdiscid),
compile it and install it in a terminal:

    wget https://github.com/metabrainz/libdiscid/archive/v{{ site.libdiscid.lversion}}.tar.gz
    tar -xf {{ site.libdiscid.current }}.tar.gz
    cd {{ site.libdiscid.current }}
    ./configure
    make
    sudo make install
