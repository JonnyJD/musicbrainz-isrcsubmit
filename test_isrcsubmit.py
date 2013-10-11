#!/usr/bin/env python
# Copyright (C) 2013  Johannes Dewender
# This test is free. You can redistribute and/or modify it at will.

import os
import sys
import math
import unittest

import isrcsubmit

class TestInternal(unittest.TestCase):
    def setUp(self):
        # suppress output
        with open(os.devnull, 'w') as devnull:
            self._old_stdout = os.dup(sys.stdout.fileno())
            os.dup2(devnull.fileno(), 1)

    def test_gather_options(self):
        # make sure most important options always work
        options = isrcsubmit.gather_options(["isrcsubmit.py"])
        self.assertFalse(options.debug)
        self.assertTrue(options.backend)
        self.assertEqual(options.server, "musicbrainz.org")
        self.assertFalse(options.force_submit)
        self.assertTrue(options.user is None)
        self.assertTrue(options.release_id is None)

        user = "JonnyJD"
        device = "/some/other/device"
        options = isrcsubmit.gather_options(["isrcsubmit.py", user, device])
        self.assertEqual(options.user, user)
        self.assertEqual(options.device, device)
        options = isrcsubmit.gather_options(["isrcsubmit.py",
                                             "-u", user, "-d", device])
        self.assertEqual(options.user, user)
        self.assertEqual(options.device, device)
        options = isrcsubmit.gather_options(["isrcsubmit.py", "--user", user,
                                             "--device", device])
        self.assertEqual(options.user, user)
        self.assertEqual(options.device, device)

    def tearDown(self):
        # restore output
        os.dup2(self._old_stdout, 1)


class TestScript(unittest.TestCase):
    pass


class TestDisc(unittest.TestCase):
    """Test reading the disc currently in the drive
    """
    pass


if __name__ == "__main__":
    unittest.main()


# vim:set shiftwidth=4 smarttab expandtab:
