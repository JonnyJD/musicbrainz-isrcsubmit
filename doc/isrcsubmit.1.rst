isrcsubmit manual page
======================

Synopsis
--------

**isrcsubmit** [*options*] [*user*] [*device*]

Description
-----------

:program:`isrcsubmit` extracts International Standard Recording Codes (ISRC)
from audio CDs and allows one to submit the data to MusicBrainz. ISRCs are used
to uniquely identifiy sound and music video recordings.

Options
-------

--version
    Show program's version number and exit.
-h
    Short usage help.
--help
    Complete help for the program.
--debug
    Show debug messages.
-u <username>, --user=<username>
    MusicBrainz username, if not given as argument.
-d <device>, --device=<device>
    CD device with a loaded audio CD, if not given as argument. The default is
    /dev/cdrom.
--release-id=<release_id>
    Optional MusicBrainz ID of the release. This will be gathered if not given.
-b <program>, --backend=<program>
    Force using a specific backend to extract ISRCs from the disc. Possible
    backends are: mediatools, media_info, cdrdao, libdiscid, discisrc. They are
    tried in this order otherwise. See also :strong:`BACKENDS`.
--browser=<browser>
    Program to open URLs. This will be automatically deteced for most setups,
    if not chosen manually.
--force-submit
    Always open TOC/disc ID submission page in browser.
--server=<server>
    Server to send ISRCs to. If not given, musicbrainz.org is used.
--keyring
    Use keyring if it is available.
--no-keyring
    Do not use keyring.

Backends
--------

:program:`isrcsubmit` is able to use various backends to extract the ISRC.
The **libdiscid** library is a requirement for isrcsubmit
and can also be used as a backend on most systems.

ISRCs are nearly always stored in the subchannel information
and all tools read them from there.
However, some drives tend to extract the same ISRC for adjacent tracks.
Restarting the script might help and using a different drive might help.
CD writers are reported to give better results than many CD reader drives.

mediatools, media_info
    These tools use an experimental algorithm to gather ISRCs from the disc.
    This should give less duplicates on the same drive than with other tools.
    However, there might be other problems. (only available for Windows)

cdrdao
    This tool can read ISRCs from CD-Text if no ISRCs are in the subchannel
    information.
    This is rarely the case. Most ISRCs are stored in the subchannel.
    (usually available on Linux, but there are also Windows builds (plank))

libdiscid
    Starting with **libdiscid** 0.3.0 this can be used not only for
    the disc ID, but also to extract ISRCs.
    (Windows, Mac; Linux support with 0.3.1)

discisrc
    The **discisrc** binary is created from source builds of **libdiscid**.
    There is an experimental branch *isrc_raw* that might give
    better results regarding duplicate ISRCs on Linux.
    You can use this binary separately without installing
    an experimental libdiscid library on the system.


See also
--------

:manpage:`isrcsubmit-config(5)`

Author
------

This manual was written by Sebastian Ramacher and Johannes Dewender.
:program:`isrcsubmit` was written by Johannes Dewender.
