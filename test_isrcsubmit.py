#!/usr/bin/env python
# Copyright (C) 2013  Johannes Dewender
# This test is free. You can redistribute and/or modify it at will.

import os
import sys
import math
import unittest
from io import TextIOWrapper, BytesIO

import discid
import musicbrainzngs
import isrcsubmit


try:
    import discid
    from discid import DiscError
except ImportError:
    from libdiscid.compat import discid
    from libdiscid.compat.discid import DiscError

SCRIPT_NAME = "isrcsubmit.py"

class TestInternal(unittest.TestCase):
    def setUp(self):
        # suppress output
        with open(os.devnull, 'w') as devnull:
            self._old_stdout = os.dup(sys.stdout.fileno())
            os.dup2(devnull.fileno(), 1)

    def test_encoding(self):
        self.assertTrue(type(isrcsubmit.encode("test")) is type(b"test"))
        self.assertEqual(isrcsubmit.encode("test"), b"test")
        self.assertTrue(type(isrcsubmit.decode(b"test"))
                        is type(b"test".decode()))
        self.assertEqual(isrcsubmit.decode(b"test"), "test")

        string = "test"
        self.assertEqual(isrcsubmit.decode(isrcsubmit.encode(string)),
                         string)
        bytestring = b"test"
        self.assertEqual(isrcsubmit.encode(isrcsubmit.decode(bytestring)),
                         bytestring)

    def test_gather_options(self):
        # make sure most important options always work
        options = isrcsubmit.gather_options([SCRIPT_NAME])
        self.assertFalse(options.debug)
        self.assertTrue(options.backend)
        self.assertEqual(options.server, "musicbrainz.org")
        self.assertFalse(options.force_submit)
        self.assertTrue(options.user is None)
        self.assertTrue(options.release_id is None)

        user = "JonnyJD"
        device = "/some/other/device"
        options = isrcsubmit.gather_options([SCRIPT_NAME, user, device])
        self.assertEqual(options.user, user)
        self.assertEqual(options.device, device)
        options = isrcsubmit.gather_options([SCRIPT_NAME,
                                             "-d", device, "-u", user])
        self.assertEqual(options.user, user)
        self.assertEqual(options.device, device)
        options = isrcsubmit.gather_options([SCRIPT_NAME, "--user", user,
                                             "--device", device])
        self.assertEqual(options.user, user)
        self.assertEqual(options.device, device)

    def tearDown(self):
        # restore output
        os.dup2(self._old_stdout, 1)


TEST_DATA = "test_data/"
save_run = True
data_sent = {}
mocked_disc = None

class Mocked_Disc(object):
    def __init__(self, id, mcn, tracks):
        self.id = id
        self.mcn = mcn
        self.tracks = tracks


# mock musicbrainzngs queries
# - - - - - - - - - - - - - -

# save mbngs functions
_mbngs_get_releases_by_discid = musicbrainzngs.get_releases_by_discid
_mbngs_get_release_by_id = musicbrainzngs.get_release_by_id
_mbngs_submit_isrcs = musicbrainzngs.submit_isrcs

def _get_releases_by_discid(disc_id, includes=[]):
    file_name = "%s%s_releases.py" % (TEST_DATA, disc_id)
    if save_run:
        releases = _mbngs_get_releases_by_discid(disc_id, includes)
        with open(file_name, "w") as releases_file:
            releases_file.write(repr(releases))
        return releases
    else:
        with open(file_name, "r") as releases_file:
            return releases_file.read()

musicbrainzngs.get_releases_by_discid = _get_releases_by_discid

def _get_release_by_id(release_id, includes=[]):
    file_name = "%s%s.py" % (TEST_DATA, release_id)
    if save_run:
        release = _mbngs_get_release_by_id(release_id, includes)
        with open(file_name, "w") as release_file:
            releases_file.write(repr(release))
        return releases
    else:
        with open(file_name, "r") as release_file:
            return release_file.read()

musicbrainzngs.get_release_by_id = _get_release_by_id

def _submit_isrcs(tracks2isrcs):
    global data_sent
    data_sent.tracks2isrcs = tracks2isrcs
    return True

musicbrainzngs.submit_isrcs = _submit_isrcs


# mock discid reading
# - - - - - - - - - -

# save discid functions
_discid_read = discid.read

def _read(device=None, features=[]):
    if save_run:
        return _discid_read(device, features)
    else:
        return mocked_disc

discid.read = _read


class SmartBuffer(TextIOWrapper):
    def write(self, string):
        try:
            return super(type(self), self).write(string)
        except TypeError:
            # redirect encoded byte strings directly to buffer
            return super(type(self), self).buffer.write(string)

class TestScript(unittest.TestCase):
    def setUp(self):
        # gather output
        self._old_stdout = sys.stdout
        self._stdout = SmartBuffer(BytesIO(), sys.stdout.encoding)
        sys.stdout = self._stdout
        self._old_stdin = sys.stdin
        self._stdin = SmartBuffer(BytesIO(), sys.stdin.encoding)
        sys.stdin = self._stdin

    def _input(self, msg):
        self._stdin.write(msg)
        self._stdin.seek(0)

    def _output(self):
        self._stdout.seek(0)
        return self._stdout.read()

    def _debug(self):
        return sys.stderr.write(self._output())

    def test_version(self):
        try:
            isrcsubmit.main([SCRIPT_NAME, "--version"])
        except SystemExit:
            pass
        finally:
            self.assertTrue(isrcsubmit.__version__ in self._output().strip())

    def test_help(self):
        try:
            isrcsubmit.main([SCRIPT_NAME, "-h"])
        except SystemExit:
            pass
        finally:
            self.assertTrue(self._output().strip())

    def test_read(self):
        global mocked_disc
        mocked_disc = Mocked_Disc("id zeug", "064811650", [])
        self._input("\n")
        try:
            isrcsubmit.main([SCRIPT_NAME])
        except SystemExit:
            pass
        finally:
            self.assertTrue(isrcsubmit.__version__ in self._output().strip())

    def tearDown(self):
        # restore output
        sys.stdout = self._old_stdout
        self._stdout.close()
        sys.stdin = self._old_stdin



class TestDisc(unittest.TestCase):
    """Test reading the disc currently in the drive
    """
    pass


if __name__ == "__main__":
    unittest.main()


# vim:set shiftwidth=4 smarttab expandtab:
