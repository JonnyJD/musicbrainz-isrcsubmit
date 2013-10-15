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
    ]
else:
    man_pages = []


args = {}
if have_setuptools:
    args["install_requires"] = ["discid >=1.0.0", "musicbrainzngs >=0.4"],
    # we load isrcsubmit on setup
    args["setup_requires"] = args["install_requires"],
else:
    pass
    #args["requires"] = ["discid(>=1.0.0)", "musicbrainzngs(>=0.4)"]

setup(name="isrcsubmit",
        version=__version__,
        description="submit ISRCs from disc to MusicBrainz",
        long_description=open("README.rst").read(),
        author="Johannes Dewender",
        author_email="brainz@JonnyJD.net",
        url="https://github.com/JonnyJD/musicbrainz-isrcsubmit",
        requires=["discid(>=1.0.0)", "musicbrainzngs(>=0.4)"],
        scripts=["isrcsubmit.py"],
        license="GPLv3+",
        classifiers=[
            "Development Status :: 4 - Beta",
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
            "Topic :: Database :: Front-Ends",
            "Topic :: Multimedia :: Sound/Audio :: CD Audio :: CD Ripping",
            "Topic :: Text Processing :: Filters"
            ],
        data_files=man_pages,
        cmdclass=cmdclass,
        **args
        )

# vim:set shiftwidth=4 smarttab expandtab:
