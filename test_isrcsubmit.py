#!/usr/bin/env python
# Copyright (C) 2014  Johannes Dewender
# This test is free. You can redistribute and/or modify it at will.

import os
import re
import sys
import math
import json
import pickle
import unittest
from io import TextIOWrapper, BytesIO
from subprocess import Popen

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

isrcsubmit.discid.read = _read


# mock cdrdao reading
# - - - - - - - - - -

class _Popen(Popen):
    def __new__(cls, args, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr):
        if args[0] == "cdrdao":
            file_name = "%s%s_cdrdao.toc" % (TEST_DATA, mocked_disc_id)
            if SAVE_RUN:
                # save file to a different place
                args[-1] = file_name
                # delete file so cdrdao doesn't complain it's already there
                os.remove(file_name)
            else:
                # don't actually call cdrdao
                args = ["echo", "mocked cdrdao"]
        return Popen(args, stdin=stdin, stdout=stdout, stderr=stderr)

isrcsubmit.Popen = _Popen

def _open(name, mode):
    if re.search("cdrdao-.*\.toc", name):
        name = "%s%s_cdrdao.toc" % (TEST_DATA, mocked_disc_id)
    return open(name, mode)

isrcsubmit.open = _open

# general mocking
# - - - - - - - -

_isrcsubmit_has_program = isrcsubmit.has_program
_isrcsubmit_get_prog_version = isrcsubmit.get_prog_version

def _has_program(program, strict=False):
    if program == "libdiscid":
        # we mock it anyways
        # libdiscid >= 0.2.2 still needed to load discid
        return True
    elif program == "cdrdao":
        # also mocked
        return True
    else:
        return _isrcsubmit_has_program(program, strict)

def _get_prog_version(prog):
    if prog == "libdiscid":
        version = "mocked libdiscid"
    elif prog == "cdrdao":
        version = "mocked cdrdao"
    else:
        return _isrcsubmit_get_prog_version(prog)
    return isrcsubmit.decode(version)

isrcsubmit.has_program = _has_program
isrcsubmit.get_prog_version = _get_prog_version


# mock answers given by user
# - - - - - - - - - - - - -

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
        try:
            append_to_stdin("%d\n" % answers["choice"])
        except KeyError:
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
        try:
            answer = answers[last_question]
        except KeyError:
            answer = default
        answer_on_stdin(answer, default)


class SmartStdin(TextIOWrapper):
    def write(self, string):
        if type(string) == bytes:
            string = string.decode()
        return super(type(self), self).write(string)

class SmartStdout(TextIOWrapper):
    def write(self, string):
        handle_question(string)
        # using "except TypeError" and the buffer would be nice
        # but exceptions don't seem to work here in Python 2.6
        # additionally TexIOWrapper doesn't have "buffer" in 2.6
        if type(string) == bytes:
            string = string.decode()
        return super(type(self), self).write(string)


# the actual tests of the overall script
# - - - - - - - - - - - - - - - - - - -

class TestScript(unittest.TestCase):
    def setUp(self):
        global answers, data_sent, mocked_disc_id
        global last_question

        # make sure globals are unset
        answers = data_sent = {}
        mocked_disc_id = last_question = None

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

    def assert_output(self, string):
        self.assertTrue(string in self._output().strip())

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
        # we use defaults to questions -> no settings here
        try:
            isrcsubmit.main([SCRIPT_NAME, "--backend", "libdiscid"])
        except SystemExit:
            pass
        finally:
            self.assertTrue(isrcsubmit.__version__ in self._output().strip())
            self.assert_output("mocked libdiscid")
            self.assert_output("TqvKjMu7dMliSfmVEBtrL7sBSno-")
            self.assert_output("07090529-0fbf-4bd3-adc4-fe627343976d")
            self.assert_output("submit the disc?")
            self.assert_output("DEC680000220 is already attached to track 4")
            self.assert_output("No new ISRCs")

    def test_cdrdao(self):
        global mocked_disc_id
        mocked_disc_id = "hSI7B4G4AkB5.DEBcW.3KCn.D_E-"
        answers["choice"] = 1
        try:
            isrcsubmit.main([SCRIPT_NAME, "--backend", "cdrdao", "--device", "/dev/cdrw"])
        except SystemExit:
            pass
        finally:
            self.assertTrue(isrcsubmit.__version__ in self._output().strip())
            self.assert_output("mocked cdrdao")
            self.assert_output("hSI7B4G4AkB5.DEBcW.3KCn.D_E-")
            self.assert_output("none of these")
            self.assert_output("174a5513-73d1-3c9d-a316-3c1c179e35f8")
            self.assert_output("GBBBN7902023 is already attached to track 7")
            self.assert_output("No new ISRCs")

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
