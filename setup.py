#!/usr/bin/env python

import sys
import unittest
try:
    from setuptools import setup, Command
    have_setuptools = True
except ImportError:
    from distutils.core import setup, Command
    have_setuptools = False
from distutils.command.build import build

from isrcsubmit import __version__

try:
    import sphinx
    from sphinx.setup_command import BuildDoc
    using_sphinx = True
except ImportError:
    using_sphinx = False

cmdclass = {}
if using_sphinx:
    # use Sphinx to build the manpage if it is available
    class BuildDocMan(BuildDoc):
        def initialize_options(self):
            BuildDoc.initialize_options(self)
            self.builder = 'man'
            self.source_dir = 'doc'
            self.build_dir = 'build'

    # automatically build manpages as sub target of build
    build.sub_commands.append(('build_sphinx_man', None))
    cmdclass['build_sphinx_man'] = BuildDocMan

    import platform
    if platform.system() in ['FreeBSD', 'OpenBSD']:
        man_dir = 'man'
    else:
        man_dir = 'share/man'

    import os.path
    man_pages = [
        (os.path.join(man_dir, 'man1'), ['build/man/isrcsubmit.1']),
        (os.path.join(man_dir, 'man5'), ['build/man/isrcsubmit-config.5'])
    ]
else:
    man_pages = []


args = {}
if have_setuptools:
    args["install_requires"] = ["discid >=1.0.0", "musicbrainzngs >=0.4"],
    # we load isrcsubmit on setup
    args["setup_requires"] = args["install_requires"],

class Test(Command):
    description = "run the test suite"
    # options as listed with "--help test"
    # --verbose --quiet -> self.verbose are already handles as global options
    user_options = [
            ("tests=", None,
                "a comma separated list of tests to run (default all)")
            ]

    def initialize_options(self):
        # set defaults
        self.tests = None

    def finalize_options(self):
        if self.verbose:
            self.verbosity = 2
        else:
            self.verbosity = 1
        if self.tests is not None:
            if self.tests:
                self.names = self.tests.split(",")
            else:
                self.names = []
        else:
            self.names = ["test_isrcsubmit.TestInternal",
                          "test_isrcsubmit.TestScript"]

    def run(self):
        suite = unittest.defaultTestLoader.loadTestsFromNames(self.names)
        runner = unittest.TextTestRunner(verbosity=self.verbosity)
        result = runner.run(suite)
        if result.wasSuccessful():
            sys.exit(0)
        else:
            sys.exit(len(result.failures) + len(result.errors))

cmdclass["test"] = Test

with open("README.rst") as readme:
    long_description = readme.read()

setup(name="isrcsubmit",
        version=__version__,
        description="submit ISRCs from disc to MusicBrainz",
        long_description=long_description,
        author="Johannes Dewender",
        author_email="brainz@JonnyJD.net",
        url="https://github.com/JonnyJD/musicbrainz-isrcsubmit",
        requires=["discid(>=1.0.0)", "musicbrainzngs(>=0.4)"],
        scripts=["isrcsubmit.py"],
        license="GPLv3+",
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Environment :: Console",
            "Environment :: MacOS X",
            "Environment :: Win32 (MS Windows)",
            "Intended Audience :: End Users/Desktop",
            "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
            "Operating System :: OS Independent",
            "Programming Language :: Python :: 2.6",
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.1",
            "Programming Language :: Python :: 3.2",
            "Programming Language :: Python :: 3.3",
            "Programming Language :: Python :: 3.4",
            "Topic :: Database :: Front-Ends",
            "Topic :: Multimedia :: Sound/Audio :: CD Audio :: CD Ripping",
            "Topic :: Text Processing :: Filters"
            ],
        data_files=man_pages,
        cmdclass=cmdclass,
        **args
        )

# vim:set shiftwidth=4 smarttab expandtab:
