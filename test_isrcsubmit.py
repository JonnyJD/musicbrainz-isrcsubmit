#!/usr/bin/env python
# Copyright (C) 2013  Johannes Dewender
# This test is free. You can redistribute and/or modify it at will.

import os
import sys
import math
import json
import pickle
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
TEST_DATA = "test_data/"
SAVE_RUN = False

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


data_sent = {}
mocked_disc_id = None

class MockedTrack(object):
    def __init__(self, track):
        self.number = track.number
        self.isrc = track.isrc

class MockedDisc(object):
    def __init__(self, disc):
        self.id = disc.id
        self.submission_url = disc.submission_url
        self.mcn = disc.mcn
        tracks = []
        for track in disc.tracks:
            tracks.append(MockedTrack(track))
        self.tracks = tracks


# mock musicbrainzngs queries
# - - - - - - - - - - - - - -

# save mbngs functions
_mbngs_get_releases_by_discid = musicbrainzngs.get_releases_by_discid
_mbngs_get_release_by_id = musicbrainzngs.get_release_by_id
_mbngs_submit_isrcs = musicbrainzngs.submit_isrcs

def _get_releases_by_discid(disc_id, includes=[]):
    file_name = "%s%s_releases.json" % (TEST_DATA, disc_id)
    if SAVE_RUN:
        releases = _mbngs_get_releases_by_discid(disc_id, includes)
        with open(file_name, "w") as releases_file:
            json.dump(releases, releases_file, indent=2)
        return releases
    else:
        with open(file_name, "r") as releases_file:
            return json.load(releases_file)

musicbrainzngs.get_releases_by_discid = _get_releases_by_discid

def _get_release_by_id(release_id, includes=[]):
    file_name = "%s%s.json" % (TEST_DATA, release_id)
    if SAVE_RUN:
        release = _mbngs_get_release_by_id(release_id, includes)
        with open(file_name, "w") as release_file:
            json.dump(release, releases_file, indent=2)
        return releases
    else:
        with open(file_name, "r") as release_file:
            return json.load(release_file)

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
    if SAVE_RUN:
        # always read all features to save full libdiscid information
        disc = _discid_read(device, ["read", "mcn", "isrc"])
        file_name = "%s%s.pickle" % (TEST_DATA, disc.id)
        with open(file_name, "wb") as disc_file:
            pickle.dump(MockedDisc(disc), disc_file, 2)
        return disc
    else:
        file_name = "%s%s.pickle" % (TEST_DATA, mocked_disc_id)
        with open(file_name, "rb") as disc_file:
            return pickle.load(disc_file)

discid.read = _read

last_question = None

def append_to_stdin(msg):
    position = sys.stdin.tell()
    sys.stdin.write(msg)
    sys.stdin.seek(position)

def answer_on_stdin(answer, default=True):
    if answer == default:
        append_to_stdin("\n")
    elif answer:
        append_to_stdin("y\n")
    else:
        append_to_stdin("n\n")

def handle_question(string):
    global last_question
    question = False
    default = False

    # these questions can be handled right now
    if "username" in string:
        append_to_stdin("invalid_username\n")   # doesn't matter, mocked
    elif "password" in string:
        append_to_stdin("invalid_password\n")   # doesn't matter, mocked
    elif "Which one do you want?" in string:
        #TODO: don't pick at random
        append_to_stdin("1\n")
    elif "press <return>" in string:
        append_to_stdin("\n")

    # these questions use multiple writes
    if "submit" in string and "disc" in string:
        last_question = "submit_disc"
    elif "help clean" in string:
        last_question = "clean"
    elif "ISRC in browser" in string:
        last_question = "open_isrc"
    # question and prompt can be on different writes
    if "[y/N]" in string: question = True; default = False
    if "[Y/n]" in string: question = True; default = True

    if question:
        #TODO: don't just pick default, use last_question
        answer_on_stdin(default, default)

class SmartStdin(TextIOWrapper):
    def write(self, string):
        try:
            return super(type(self), self).write(string)
        except TypeError:
            # redirect encoded byte strings directly to buffer
            return super(type(self), self).buffer.write(string)

class SmartStdout(TextIOWrapper):
    def write(self, string):
        handle_question(string)
        try:
            return super(type(self), self).write(string)
        except TypeError:
            # redirect encoded byte strings directly to buffer
            return super(type(self), self).buffer.write(string)

class TestScript(unittest.TestCase):
    def setUp(self):
        # gather output
        self._old_stdout = sys.stdout
        self._stdout = SmartStdout(BytesIO(), sys.stdout.encoding)
        sys.stdout = self._stdout
        self._old_stdin = sys.stdin
        self._stdin = SmartStdin(BytesIO(), sys.stdin.encoding)
        sys.stdin = self._stdin

    def _output(self):
        sys.stdout.seek(0)
        return sys.stdout.read()

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

    def test_libdiscid(self):
        global mocked_disc_id
        mocked_disc_id = "TqvKjMu7dMliSfmVEBtrL7sBSno-"
        try:
            isrcsubmit.main([SCRIPT_NAME, "--backend", "libdiscid"])
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
