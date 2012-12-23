---
layout: default
title: home
---
## Available Backends

### Linux

 * [Cdrdao]((http://en.wikipedia.org/wiki/Cdrdao)
   can read ISRCs from subchannel and CD-Text and is the preferred backend
 * cd-info is a small utility included in
   [libcdio](http://www.gnu.org/software/libcdio/)
 * Cdda2wav also supports ISRC extraction and is included in
   [cdrtools](http://en.wikipedia.org/wiki/Cdrtools)
 * Icedax is in [cdrkit](http://en.wikipedia.org/wiki/Cdrkit),
   which is an outdated fork of cdrtools

The Cdrdao backend can read ISRCs from CD-Text if no ISRCs are
in the subchannel information.
This is rarely the case.

When ISRCs are in the subchannel,
all of these backens should yield the same results on the same drive.
However, some drives tend to randomly give duplicats.
Restarting the script might help and often CD writer drives
give less duplicates than CD reader drives.


### Mac OS X
 * drutil (in Mac OS X; very slow!)
 * [discisrc]({{ site.downloads.url }}discisrc-mac.zip) (IN PROGRESS)
   is included in another branch of the libdiscid project.
   There is a build available for mac, but the backend is not implemented yet.


### Windows
 * [mediatools](http://www.flanagan-family.com/mediatools.zip)
   is a tool that uses a different algorithm to gather ISRCs from the disc.
   This should give less duplicates on the same drive than other tools.
   However, there might be other problems.
   (see [Issue #34]({{ site.issues.url}}/34))
 * For [Cdrdao]((http://en.wikipedia.org/wiki/Cdrdao) there is a
   [Windows Build](http://www.student.tugraz.at/thomas.plank/) available.
   You need ```cdrdao.exe```, ```cyggcc\_s-sjlj-1.dll``` and ```cygwin1.dll```.
   Put all of these in the ```%PATH%```
   or the same directory you start isrcsubmit in.
