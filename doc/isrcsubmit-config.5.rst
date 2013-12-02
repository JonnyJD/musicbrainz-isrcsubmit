:orphan:

isrcsubmit configuration
========================

Synopsis
--------

**$XDG_CONFIG_HOME/isrcsubmit/config**

Description
-----------

The configuration file contains various options controlling the behavior of
:program:`isrcsubmit`. All the options given here can be overriden by passing
command line arguments to :program:`isrcsubmit`.

general
-------

This refers to the ``[general]`` section of the configuration file.

backend
^^^^^^^
Force using a specific backend to extract ISRCs from the disc. Possible
backends are: mediatools, media_info, cdrdao, libdiscid, discisrc.

browser
^^^^^^^
Program to open URLs.

device
^^^^^^
CD device with a loaded audio CD.

keyring
^^^^^^^
Use keyring if it is available.


musicbrainz
-----------

This refers to the ``[musicbrainz]`` section of the configuration file.

server
^^^^^^
Server to send ISRCs to.

user
^^^^
MusicBrainz username.

Example
-------

This snippet demonstrates the format of the configuration file.

.. code-block:: text

    [general]
    backend = libdiscid

    [musicbrainz]
    server = test.musicbrainz.org

Author
------

This manual page was written by Sebastian Ramacher. :program:`isrcsubmit` was
written by Johannes Dewender.
