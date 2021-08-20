#!/usr/bin/env python
# Copyright (C) 2009-2015 Johannes Dewender
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""This is a tool to submit ISRCs from a disc to MusicBrainz.

Mutagen is used to gather the ISRCs
and python-musicbrainz2 to submit them.
The project is hosted on
https://github.com/SheamusPatt/musicbrainz-isrcDigitalSubmit
"""

__version__ = "2.1.0"

import operator

AGENT_NAME = "isrcDigitalSubmit.py"
TOOL_NAME = "isrcDigitalSubmit"

import glob
import logging
import musicbrainzngs
import mutagen
import os
import sys
import zipfile
from musicbrainzngs import AuthenticationError, ResponseError, WebServiceError
from optparse import OptionParser

import isrcsubmit
from isrcsubmit import open_browser, config_path, user_input, \
    printf, print_encoded, print_error, print_release, setDefaultOptions

# Maximum time difference between MB and audio files,
#  else they will be considered different
max_time_diff = 3

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

if os.name == "nt":
    SHELLNAME = "isrcDigitalSubmit.bat"
else:
    SHELLNAME = "isrcDigitalSubmit.sh"
if os.path.isfile(SHELLNAME):
    SCRIPTNAME = SHELLNAME
else:
    SCRIPTNAME = os.path.basename(sys.argv[0])


# global variables
ws2 = None
logger = logging.getLogger("isrcDigitalSubmit")


def script_version():
    return "isrcDigitalSubmit %s by SheamusPatt" % (__version__)


def print_help(option=None, opt=None, value=None, parser=None):
    print("%s" % script_version())
    print(
"""
This python script extracts ISRCs from audio files and submits them to MusicBrainz (musicbrainz.org).
You need to have a MusicBrainz account, specify the username and will be asked for your password every time you execute the script.

IsrcDigitalSubmit will warn you if there are any problems and won't actually submit anything to MusicBrainz without giving a final choice.

IsrcDigitalSubmit will warn you if any duplicate ISRCs are detected and help you fix previously inserted duplicate ISRCs.
The ISRC-track relationship we found in the audio files is taken as our correct evaluation.
""")
    parser.print_usage()
    print("""\
Please report bugs on https://github.com/SheamusPatt/musicbrainz-isrcsubmit""")
    sys.exit(0)


def print_usage(option=None, opt=None, value=None, parser=None):
    print("%s\n" % script_version())
    parser.print_help()
    sys.exit(0)


class Isrc(object):
    def __init__(self, isrc, track=None):
        self._id = isrc
        self._tracks = []
        if track is not None:
            self._tracks.append(track)

    def add_track(self, track):
        if track not in self._tracks:
            self._tracks.append(track)

    def get_tracks(self):
        return self._tracks

    def get_track_numbers(self):
        numbers = []
        for track in self._tracks:
            numbers.append(track["position"])
        return ", ".join(numbers)


class Track(dict):
    """track with equality checking

    This makes it easy to check if this track is already in a collection.
    Only the element already in the collection needs to be hashable.
    """
    def __init__(self, track, number=None):
        self._recording = track
        self._number = number
        if track.__class__ == mutagen.ogg.OggFileType or track.__class__ == mutagen.flac.FLAC :
            if not self._number:
                self._number = int(track.get("tracknumber")[0])
            if (track.tags.get('artist')):
                self._artist = track.tags.get('artist')[0]
            else:
                self._artist = None
            if (track.tags.get('albumartist')):
                self._albumartist = track.tags.get('albumartist')[0]
            else:
                self._albumartist = None
            self._album = track.get("album")[0]
            self._title = track.get("title")[0]
            self._isrc = track.get("ISRC")
        elif track.__class__ == mutagen.mp3.MP3:
            if not self._number:
                trck = track.get("TRCK") or track.get("TRK")
                self._number = int(trck.text[0].partition("/")[0])
            if track.get("TPE1"):
                self._artist = track.get("TPE1")[0]
            elif track.get("TP1"):
                self._artist = track.get("TP1")[0]
            else:
                self._artist = None
            self._albumartist = None
            if track.get("TALB"):
                self._album = track.get("TALB")[0]
            elif track.get("TAL"):
                self._album = track.get("TAL")[0]
            else:
                self._album = None
            if track.get("TIT2"):
                self._title = track.get("TIT2")[0]
            elif track.get("TT2"):
                self._title = track.get("TT2")[0]
            else:
                self._title = None
            self._isrc = track.get("TSRC")

    def __eq__(self, other):
        return self["id"] == other["id"]

    def __getitem__(self, item):
        return self._recording[item]

    def get(self, item, default=None):
        return self._recording.get(item, default)


def gather_options(argv):
    global options

    config = ConfigParser()
    config.read(config_path(TOOL_NAME))

    parser = OptionParser(version=script_version(), add_help_option=False)
    parser.set_usage(
            "{prog} [options] [user] audioFile...\n       {prog} -h".format(
            prog=SCRIPTNAME))
    parser.add_option("-h", action="callback", callback=print_usage,
            help="Short usage help")
    parser.add_option("--help", action="callback", callback=print_help,
            help="Complete help for the script")
    parser.add_option("-u", "--user", metavar="USERNAME",
            help="MusicBrainz username, if not given as argument.")
    parser.add_option("--release-id", metavar="RELEASE_ID",
            help="Optional MusicBrainz ID of the release."
            + " This will be gathered if not given.")
    parser.add_option("--browser", metavar="BROWSER",
            help="Program to open URLs. This will be automatically detected"
            " for most setups, if not chosen manually.")
    parser.add_option("--force-submit", action="store_true", default=False,
            help="Always open TOC/disc ID in browser.")
    parser.add_option("--server", metavar="SERVER",
            help="Server to send ISRCs to. Default: %s" % isrcsubmit.DEFAULT_SERVER)
    parser.add_option("--debug", action="store_true", default=False,
            help="Show debug messages."
            + " Currently shows some backend messages.")
    parser.add_option("--keyring", action="store_true", dest="keyring",
            help="Use keyring if available.")
    parser.add_option("--no-keyring", action="store_false", dest="keyring",
            help="Disable keyring.")
    (options, args) = parser.parse_args(argv[1:])
    isrcsubmit.options = options

    print("%s" % script_version())

    # assign positional arguments to options
    if options.user is None and args:
        options.user = args[0]
        args = args[1:]
    if not args:
        print_error("No audio files to process")
        sys.exit(1)
    options.audioFiles = []
    for arg in args:
        for f in glob.glob(arg):
            options.audioFiles.append(f)

    setDefaultOptions(config, options)

    return options


class WebService2(isrcsubmit.WebService2):
    """A web service wrapper that asks for a password when first needed.

    This uses musicbrainzngs as a wrapper itself.
    """

    def __init__(self, username=None):
        isrcsubmit.WebService2.__init__(self, username)
        musicbrainzngs.set_useragent(AGENT_NAME, __version__,
                "http://github.com/SheamusPatt/musicbrainz-isrcsubmit")

    def tracks_match(self, mb_tracks, tracks):
        if len(mb_tracks) != len(tracks):
            return False
        mbIter = mb_tracks.iter()
        trackIter = tracks.iter()
        mbTrack = mbIter.next()
        while mbTrack:
            track = trackIter.next()
            if abs(track.info.length - mbTrack.length) > max_time_diff:
                return False
        return True

    def get_releases_by_name(self, artist, title, tracks, extra=""):
        query = '{} AND artist:"{}" AND tracks:{}{}'.format(title, artist, len(tracks), extra);
        try:
            response = musicbrainzngs.search_releases(query, strict=True)
        except ResponseError as err:
            if err.cause.code == 404:
                return []
            else:
                print_error("Couldn't fetch release: %s" % err)
                sys.exit(1)
        except WebServiceError as err:
            print_error("Couldn't fetch release: %s" % err)
            sys.exit(1)
        return response['release-list']


def gather_tracks(audioFiles):
    """read the disc in the device with the backend and extract the ISRCs
    """
    tracks = []

    for file in audioFiles:
        if zipfile.is_zipfile(file):
            zf = zipfile.ZipFile(file)
            for info in zf.infolist():
                if not info.is_dir() and not info.filename.startswith('__MACOSX/._'):
                    # Ignore AppleDouble resource files
                    member = zf.open(info.filename)
                    track = mutagen.File(member)
                    if (track):
                        tracks.append(Track(track))
                    else:
                        printf("Ignoring non-music member %s\n" % info.filename)
        else:
            track = mutagen.File(file)
            if (track):
                tracks.append(Track(track))
            else:
                printf("Ignoring non-music file %s\n" % file)
    tracks.sort(key=operator.attrgetter("_number"))
    return tracks


def check_isrcs_local(tracks, mb_tracks):
    """check tracls for (local) duplicates and inconsistencies
    """
    isrcs = dict()          # isrcs found on disc
    tracks2isrcs = dict()   # isrcs to be submitted
    errors = 0

    for track in tracks:
        track_number = track._number
        if track._isrc == None:
            print("Track %s %s has no ISRC" % (track_number, track._title))
        elif len(track._isrc) > 1:
            print_error("Track %s %s has multipl ISRCs. Has this file been tagged already?"
                        % (track_number, track._title, track._isrc))
            errors += 1
        else:
            isrc = track._isrc[0]
            mb_track = mb_tracks[track_number - 1]
            if isrc in isrcs:
                # found this ISRC for multiple tracks
                isrcs[isrc].add_track(mb_track)
            else:
                isrcs[isrc] = Isrc(isrc, mb_track)
            # check if the ISRC was already added to the track
            isrc_attached = False
            mbIsrcList = mb_track["recording"].get("isrc-list")
            if mbIsrcList:
                for mb_isrc in mbIsrcList:
                    if isrc == mb_isrc:
                        print("%s is already attached to track %d"
                              % (isrc, track_number))
                        isrc_attached = True
                        break
            if not isrc_attached:
                # single isrcs work in python-musicbrainzngs 0.4, but not 0.3
                # lists of isrcs don't work in 0.4 though, see pymbngs #113
                tracks2isrcs[mb_track.get("recording")["id"]] = isrc
                print("found new ISRC for track %d: %s"
                      % (track_number, isrc))

    # Check for multiple ISRCs on different tracks
    for isrc in isrcs.items():
        if len(isrc[1].get_tracks()) > 1:
            print("ISRC %s found on more than one track" % isrc._id)
            for track in isrc.get_tracks():
                print("-> %s" % track)
            errors += 1

    return isrcs, tracks2isrcs, errors


def check_global_duplicates(release, mb_tracks, isrcs):
    """Help cleaning up global duplicates of any of the isrcs from this digital release
    """
    duplicates = []
    # add already attached ISRCs
    for isrc in isrcs:
        recordings = ws2.get_recordings_by_isrc(isrc)
        if len(recordings) > 1:
            duplicates.append(isrc._id)

    if len(duplicates) > 0:
        printf("\nThere were %d ISRCs ", len(duplicates))
        print("that are attached to multiple tracks.")
        choice = user_input("Do you want to help clean those up? [y/N] ")
        if choice.lower() == "y":
            cleanup_isrcs(release, duplicates)


def cleanup_isrcs(release, isrcs):
    """Show information about duplicate ISRCs

    Our attached ISRCs should be correct -> helps to delete from other tracks
    """
    global options
    for isrc in isrcs:
        tracks = isrcs[isrc].get_tracks()
        print("\nISRC %s attached to:" % isrc)
        for track in tracks:
            printf("\t")
            artist = track.get("artist-credit-phrase")
            if artist and artist != release.get("artist-credit-phrase"):
                string = "%s - %s" % (artist, track["title"])
            else:
                string = "%s" % track["title"]
            print_encoded(string)
            # tab alignment
            if len(string) >= 32:
                printf("\n%s",  " " * 40)
            else:
                if len(string) < 7:
                    printf("\t")
                if len(string) < 15:
                    printf("\t")
                if len(string) < 23:
                    printf("\t")
                if len(string) < 31:
                    printf("\t")

            printf("\t track %s", track["position"])

            url = "http://%s/isrc/%s" % (options.server, isrc)
            if user_input("Open ISRC in the browser? [Y/n] ").lower() != "n":
                open_browser(url)
                user_input("(press <return> when done with this ISRC) ")

FEATURED_ARTIST_SEP = [' feat. ', ' duet with ']

def find_release(tracks, common_includes):
    global options
    global ws2
    albumartists = set()
    artists = set()
    albums = set()
    for track in tracks:
        artists.add(track._artist.lower().strip())
        if (track._albumartist):
            albumartists.add(track._albumartist.lower().strip())
        albums.add(track._album.lower().strip())
    if len(albumartists)>1:
        print("Release should have just one Album Artist, found %d: %s", len(artists), str(artists))
        sys.exit(1)
    elif len(albumartists)==1:
        albumartist = albumartists.pop()
    elif len(artists) == 1:
        albumartist = artists.pop()
    else:
        # Might still be a single artist album with 'featured' artists. Look for a common prefix
        # after breaking at common featured artist tags
        albumartist = None
        for otherartist in artists:
            for feat in FEATURED_ARTIST_SEP:
                otherartist = otherartist.partition(feat)[0]
            if not albumartist or len(otherartist) < len(albumartist):
                albumartist = otherartist
        for otherartist in artists:
            if len(albumartist) > len(otherartist) and albumartist.startswith(otherartist):
                albumartist = otherartist
            elif not otherartist.startswith(albumartist):
                albumartist = 'Various Artists'
                break

    if len(albums)>1:
        print("Release should have just one Album, found %d: %s", len(albums), str(albums))
        sys.exit(1)
    albumtitle = albums.pop()
    # We have a unique artist and album. See if we can locate it in MB
    results = ws2.get_releases_by_name(albumartist, albumtitle, tracks, ' AND format:"Digital Media"')
    if len(results) == 0:
        results = ws2.get_releases_by_name(albumartist, albumtitle, tracks)
        if len(results) > 0:
            print_error("Found a release but format is not Digital Media")
            print_release(results[0])
            sys.exit(1)
        else:
            # Various Artists downloads might not use Various Artists as the album artist
            results = ws2.get_releases_by_name("Various Artists", albumtitle, tracks, 'AND format:"Digital Media"')
    num_results = len(results)
    selected_release = None
    if num_results == 0:
        print("\n\"{}\" by \"{}\" is not in the database.".format(albumartist, albumtitle))
        sys.exit(1)
    elif num_results > 1:
        print("\nMultiple releases found for '{}' by '{}', please pick one:".format(albumtitle, albumartist))
        print(" 0: none of these\n")
        for i in range(num_results):
            release = results[i]
            # printed list is 1..n, not 0..n-1 !
            print_release(release, i + 1)
        try:
            num = user_input("Which one do you want? [0-%d] "
                             % num_results)
            if int(num) not in range(0, num_results + 1):
                raise IndexError
            if int(num) == 0:
                print("Release not found. You can resubmit using the --release-id option\n")
                sys.exit(1)
            else:
                selected_release = results[int(num) - 1]
        except (ValueError, IndexError):
            print_error("Invalid Choice")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\nexiting..")
            sys.exit(1)
    else:
        print("Found unique release\n")
        selected_release = results[0]

    return ws2.get_release_by_id(selected_release["id"], common_includes)


def main(argv):
    global options
    global ws2
    common_includes = ["artists", "labels", "recordings", "isrcs",
                       "artist-credits"]
    # preset logger
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logging.getLogger().addHandler(stream_handler) # add to root handler

    # global variables
    options = gather_options(argv)
    ws2 = WebService2(options.user)

    if options.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        stream_handler.setLevel(logging.INFO)

        # adding log file
        logfile = "isrcDigitalSubmit.log"
        file_handler = logging.FileHandler(logfile, mode='w',
                            encoding="utf8", delay=True)
        formatter = logging.Formatter("%(levelname)s:%(name)s: %(message)s")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.info("Writing debug log to %s", logfile)
        logging.getLogger().addHandler(file_handler)

        # add context to log file (DEBUG only added there)
        logger.debug(script_version())

    tracks = gather_tracks(options.audioFiles)
    if (options.release_id):
        release = ws2.get_release_by_id(options.release_id, common_includes)
    else:
        release = find_release(tracks, common_includes)

    print("")
    print_release(release.get('release'))

    # list, dict
    mb_tracks = release.get('release')['medium-list'][0]['track-list']
    isrcs, tracks2isrcs, errors = check_isrcs_local(tracks, mb_tracks)

    if isrcs:
        print("")
    # try to submit the ISRCs
    update_intention = True
    if not tracks2isrcs:
        print("No new ISRCs could be found.")
    else:
        if errors > 0:
            print_error("%d problems detected" % errors)
        if user_input("Do you want to submit? [y/N] ").lower() == "y":
            ws2.submit_isrcs(tracks2isrcs)
        else:
            update_intention = False
            print("Nothing was submitted to the server.")

    # check for overall duplicate ISRCs, including server provided
    if update_intention:
        # the ISRCs are deemed correct, so we can use them to check others
        check_global_duplicates(release, mb_tracks, isrcs)

if __name__ == "__main__":
    main(sys.argv)


# vim:set shiftwidth=4 smarttab expandtab:
