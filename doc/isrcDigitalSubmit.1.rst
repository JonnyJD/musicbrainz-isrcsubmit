isrcDigitalSubmit manual page
======================

Synopsis
--------

**isrcDigitalSubmit** [*options*] [*user*] *audioFile*...

Description
-----------

:program:`isrcDigitalSubmit` extracts International Standard Recording Codes (ISRC)
from audio files and allows one to submit the data to MusicBrainz. ISRCs are used
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
--release-id=<release_id>
    Optional MusicBrainz ID of the release. This will be gathered if not given.
--browser=<browser>
    Program to open URLs. This will be automatically deteced for most setups,
    if not chosen manually.
--server=<server>
    Server to send ISRCs to. If not given, musicbrainz.org is used.
--keyring
    Use keyring if it is available.
--no-keyring
    Do not use keyring.

See also
--------

:manpage:`isrcsubmit-config(5)`

Author
------

This manual was written by Sebastian Ramacher and Johannes Dewender.
:program:`isrcDigitalSubmit` was written by Jim Patterson adapted from isrcsubmit by Johannes Dewender.
