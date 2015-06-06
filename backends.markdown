---
layout: default
title: backends
---

## Additional Backends

Isrcsubmit 2 can use libdiscid >= 0.3.0 directly as an ISRC backend.
However there are other backend options available:

### Linux

 * [Cdrdao](http://en.wikipedia.org/wiki/Cdrdao)
   can read ISRCs from subchannel and CD-Text

The Cdrdao backend can read ISRCs from CD-Text if no ISRCs are
in the subchannel information.
This is rarely the case.

When ISRCs are in the subchannel,
all of these backends should yield the same results on the same drive.
However, some drives tend to extract the same ISRC to adjacent tracks.
Restarting the script might help and often CD writer drives
give less duplicates than CD reader drives.


### Windows
 * [mediatools](http://www.flanagan-family.com/mediatools.zip)
   is a tool that uses an experimental algorithm to gather ISRCs from the disc.
   This should give less duplicates on the same drive than other tools.
   However, there might be other problems.
   (see [Issue #34]({{ site.issues.url}}/34))
 * For [Cdrdao](http://en.wikipedia.org/wiki/Cdrdao) there is a
   [Windows Build](http://www.student.tugraz.at/thomas.plank/) available.
   You need ```cdrdao.exe```, ```cyggcc\_s-sjlj-1.dll``` and ```cygwin1.dll```.
   Put all of these in the ```%PATH%```
   or the same directory you start isrcsubmit in.
