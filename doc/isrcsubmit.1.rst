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
    tried in this order otherwise.
--browser=<browser>
    Program to open URLs. If not given, xdg-open, firefox, chromium, opera and
    explorer are tried.
--force-submit
    Always open TOC/disc ID submission page in browser.
--server=<server>
    Server to send ISRCs to. If not given, musicbrainz.org is used.

Author
------

:program:`isrcsubmit` was written by Johannes Dewender.
