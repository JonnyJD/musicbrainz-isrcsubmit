---
layout: default
title: libdiscid
---
## libdiscid
This library is needed by pyton-musicbrainz2 in order to get the ID from the disc, which is then used to lookup the disc at [MusicBrainz](http://musicbrainz.org).

### Linux
You should check if the package is in a repository for your distribution. It mostly is.

### Mac OS X
There are packages with pre-compiled libdiscid versions for Intel Macs (32 and 64 bit) and PPC in the <a href="download">Download section</a>.
32 bit versions are taken from [Picard](http://wiki.musicbrainz.org/MusicBrainz_Picard) compiles. I compiled a 64 bit version.

### Compile it yourself
You can download the source at [libdiscid](http://wiki.musicbrainz.org/libdiscid) and compile and install it in a terminal:

    wget http://users.musicbrainz.org/~matt/libdiscid-0.2.2.tar.gz
    tar -xf libdiscid-0.2.2.tar.gz
    cd libdiscid-0.2.2
    ./configure
    make
    sudo make install
