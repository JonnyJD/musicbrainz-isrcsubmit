#!/usr/bin/env python

from distutils.core import setup

from isrcsubmit import __version__

setup(name="isrcsubmit",
        version=__version__,
        description="submit ISRCs from disc to MusicBrainz",
        long_description=open("README.md").read(),
        author="Johannes Dewender",
        author_email="brainz@JonnyJD.net",
        url="https://github.com/JonnyJD/musicbrainz-isrcsubmit",
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
            "Topic :: Database :: Front-Ends",
            "Topic :: Multimedia :: Sound/Audio :: CD Audio :: CD Ripping",
            "Topic :: Text Processing :: Filters"
            ]
        )

# vim:set shiftwidth=4 smarttab expandtab:
