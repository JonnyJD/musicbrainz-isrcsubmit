---
layout: default
title: download
---
<div class="download">
<a href="https://github.com/{{ site.github.url }}/downloads">
<img src="img/download_128.png"></a>
</div>

Available Downloads
===================


isrcsubmit.py:
--------------
(core script)

This is the core script and mainly intended for Linux users.
The additional libraries can be installed with the package manager of your distribution or manually.


isrcsubmit-\*-MacIntel/PPC:
---------------------------
(script + libdiscid + python-musicbrainz2)

These are packages for Mac OS X users.
It is more difficult to get libdiscid precompiled for Mac and less Mac users have Xcode installed to compile it themselves (or don't have root privileges)
Therefore the Mac Packages include a precompiled libdiscid.0.dylib for the appropriate architecture.
The Intel32 and PPC libraries are taken from MusicBrainz Picard.
I compiled the 64-bit version.


isrcsubmit-\*.tar.gz:
---------------------
(official tarball; complete source download as on github)

This is the official release version.
This is basically the same as downloading the tag in github. There might be minor packaging differences and the folder name is different.
