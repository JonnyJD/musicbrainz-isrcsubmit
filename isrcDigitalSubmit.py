#!/usr/bin/env python
# Copyright (C) 2009-2015 Johannes Dewender
# Copyright (C) 2021 Jim Patterson
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
"""This is a tool to submit ISRCs from audio files to MusicBrainz.

Mutagen is used to gather the ISRCs
and python-musicbrainz2 to submit them.
The project is hosted on
https://github.com/SheamusPatt/musicbrainz-isrcDigitalSubmit
"""

import operator
import re

from unidecode import unidecode

import isrcshared

AGENT_NAME = "isrcDigitalSubmit.py"

import glob
import logging
import musicbrainzngs
import mutagen
import os
import sys
import zipfile
from musicbrainzngs import ResponseError, WebServiceError
from optparse import OptionParser

from isrcshared import __version__, open_browser, config_path, \
    user_input, printf, print_encoded, print_error, print_release, \
    setDefaultOptions

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
This python script extracts ISRCs from audio files and submits them 
to MusicBrainz (musicbrainz.org). You need to have a MusicBrainz account,
specify the username and will be asked for your password when you 
submit ISRCs (keyring may be used to retain credentials between invocations).

IsrcDigitalSubmit will warn you if there are any problems and won't actually
submit anything to MusicBrainz without giving a final choice.

IsrcDigitalSubmit will warn you if any duplicate ISRCs are detected and help 
you fix previously inserted duplicate ISRCs. The ISRC-track relationship we
found in the audio files is taken as our correct evaluation.
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


trackNumMatcher = re.compile(r'(^|[/ -])(\d\d)\D[^/]+$')


class Track(dict):
    """track with equality checking

    This makes it easy to check if this track is already in a collection.
    Only the element already in the collection needs to be hashable.
    """
    def __init__(self, track, trackName):
        self._recording = track
        self._trackName = trackName
        self._number = None
        if track.__class__ == mutagen.oggvorbis.OggVorbis or track.__class__ == mutagen.flac.FLAC :
            if not self._number:
                if track.get("tracknumber") and track.get("tracknumber")[0]:
                    self._number = int(track.get("tracknumber")[0])
            if (track.get('artist')):
                self._artist = track.get('artist')[0]
            else:
                self._artist = None
            if (track.get('albumartist')):
                self._albumartist = track.tags.get('albumartist')[0]
            else:
                self._albumartist = None
            self._album = track.get("album")[0] if track.get("album") else None
            self._title = track.get("title")[0] if track.get("title") else None
            self._isrc = track.get("ISRC")
        elif track.__class__ == mutagen.mp3.MP3:
            if not self._number:
                trck = track.get("TRCK") or track.get("TRK")
                if trck:
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
        elif track.__class__ == mutagen.mp4.MP4:
            if not self._number:
                trck = track.get("trkn")
                if trck:
                    self._number = trck[0][0]
            if track.get("\xa9ART"):
                self._artist = track.get("\xa9ART")[0]
            else:
                self._artist = None
            if track.get("aART"):
                self._albumartist = track.get("aART")[0]
            else:
                self._albumartist = None
            if track.get("\xa9alb"):
                self._album = track.get("\xa9alb")[0]
            else:
                self._album = None
            if track.get("\xa9nam"):
                self._title = track.get("\xa9nam")[0]
            else:
                self._title = None
            self._isrc = track.get("----:com.apple.iTunes:ISRC")
            if (self._isrc and len(self._isrc)>0):
                # The M4A class wraps ISRC values - we need to convert
                # them to simple strings.
                self._isrc = (str(self._isrc[0],'UTF-8'),)
        if not self._number:
            match = trackNumMatcher.search(trackName)
            if match:
                self._number = match.group(2)
            else:
                print_error("All tracks must have a Track Number. None found on {}"
                            .format(trackName))

    def __eq__(self, other):
        return self["id"] == other["id"]

    def __getitem__(self, item):
        return self._recording[item]

    def get(self, item, default=None):
        return self._recording.get(item, default)


def gather_options(argv):
    global options

    config = ConfigParser()
    config.read(config_path())

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
            help="Server to send ISRCs to. Default: %s" % isrcshared.DEFAULT_SERVER)
    parser.add_option("--debug", action="store_true", default=False,
            help="Show debug messages."
            + " Currently shows some backend messages.")
    parser.add_option("--keyring", action="store_true", dest="keyring",
            help="Use keyring if available.")
    parser.add_option("--no-keyring", action="store_false", dest="keyring",
            help="Disable keyring.")
    (options, args) = parser.parse_args(argv[1:])

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


class WebService2(isrcshared.WebService2):
    """A web service wrapper that asks for a password when first needed.

    This uses musicbrainzngs as a wrapper itself.
    """

    def __init__(self, username=None):
        isrcshared.WebService2.__init__(self, username)
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
            if mbTrack.get("artist").lower() != track._artist.lower():
                return False
            if mbTrack.get("album").lower() != track._album.lower():                return False

        return True

    def get_releases_by_name(self, title, tracks, extra=""):
        query = '{} AND tracks:{}{}'.format(title, len(tracks), extra);
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
                if not info.is_dir() and not info.filename.startswith('__MACOSX/'):
                    # Ignore AppleDouble resource files
                    member = zf.open(info.filename)
                    try:
                        track = mutagen.File(member)
                        if (track):
                            tracks.append(Track(track, info.filename))
                        else:
                            printf("Ignoring non-music member %s\n" % info.filename)
                    except Exception as e:
                        print_error("Failed to load track {}: {}".format(info.filename, e))
        else:
            try:
                track = mutagen.File(file)
                if (track):
                    tracks.append(Track(track, file))
                else:
                    printf("Ignoring non-music file %s\n" % file)
            except Exception as e:
                print_error("Failed to load track {}: {}".format(file, e))
    tracks.sort(key=operator.attrgetter("_number"))
    return tracks


"""Return an ASCII version of str with all punctuation replaced by spaces
"""
def simplestr(str):
    result = unidecode(str)
    result = result.lower()
    words = re.split(r'\W+', result)
    return " ".join(words)


"""Do a fuzzy compare, ignoring case, accents and punctuation.
Returns true if strings are the same under those conditions.
"""
def fuzzycompare(str1, str2):
    return simplestr(str1) == simplestr(str2)


def check_isrcs_local(tracks, mb_tracks):
    """check tracls for (local) duplicates and inconsistencies
    Also verify that local tracks match those in MusicBrainz release
    """
    isrcs = dict()          # isrcs found on disc
    tracks2isrcs = dict()   # isrcs to be submitted
    errors = 0

    for track in tracks:
        track_number = track._number
        if track._isrc == None or not track._isrc[0]:
            print("Track %s %s has no ISRC" % (track_number, track._title))
        elif len(track._isrc) > 1:
            print_error("Track %s %s has multiple ISRCs. Has this file been tagged already?"
                        % (track_number, track._title))
            errors += 1
        else:
            isrc = track._isrc[0]
            mb_track = mb_tracks[track_number - 1]
            if not fuzzycompare(track._artist, mb_track["artist-credit-phrase"])\
                    and track._artist.lower() != "various artists":
                print_error("Track {} credited to {} which does not match credit in MusicBrainz: {}"
                            .format(track_number, track._artist, mb_track["artist-credit-phrase"]))
                errors += 1
            if not fuzzycompare(track._title, mb_track["recording"]["title"]):
                print_error("Track {} title {} does not match that in MusicBrainz: {}"
                            .format(track_number, track._title, mb_track["recording"]["title"]))
                errors += 1
            if abs(track._recording.info.length - float(mb_track["recording"]["length"])/1000)\
                    > max_time_diff:
                print_error("Track {} recording length {} more than {} seconds different than length in MusicBrainz: {}"
                            .format(track_number, track._recording.info.length,
                                    max_time_diff, float(mb_track["recording"]["length"])/1000))
                errors += 1
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
        if (track._artist):
            artists.add(track._artist.strip())
        if (track._albumartist):
            albumartists.add(track._albumartist.strip())
        albumtitle = track._album
        if not albumtitle:
            print_error("Track {} is missing an album name. \
We cannot search for an album unless all tracks have an album title".format(track._number))
            sys.exit(1)
        albums.add(albumtitle.strip().lower())
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
        print("Release should have just one Album, found %d: %s" % (len(albums), str(albums)))
        sys.exit(1)
    # We have a unique artist and album. See if we can locate it in MB
    formatQuery = ' AND format:"Digital Media"'
    if albumartist:
        artistQuery = ' AND artist:"{}"'.format(albumartist)
        results = ws2.get_releases_by_name(albumtitle, tracks, artistQuery + formatQuery)
        if len(results) == 0:
            results = ws2.get_releases_by_name(albumtitle, tracks, artistQuery)
            if len(results) > 0:
                print_error("Found a release but format is not Digital Media")
                print_release(results[0])
                sys.exit(1)
    else:
        results = []
    if len(results) == 0:
        # Try without the artist name. This can find Various Artists releases under odd names
        # or cases where the artist on tracks doesn't match MusicBrainz (it happens)
        results = ws2.get_releases_by_name(albumtitle, tracks, formatQuery)
        if len(results) == 0:
            results = ws2.get_releases_by_name(albumtitle, tracks)
            if len(results) > 0:
                print_error("Found a release but format is not Digital Media")
                print_release(results[0])
                sys.exit(1)
    num_results = len(results)
    if num_results == 0:
        print("\n\"Cannot find {}\" by \"{}\" with {} tracks in the database."
              .format(albumartist, albumtitle, len(tracks)))
        sys.exit(1)
    elif num_results > 1:
        print("\nMultiple releases found for '{0}' ({1} tracks) by '{2}', please pick one:"
              .format(albumtitle, len(tracks), albumartist))
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
        print_release(selected_release)

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
    options = isrcshared.options = gather_options(argv)

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
    if (len(tracks) == 0):
        print_error("No valid tracks found")
        sys.exit(1)
    if (options.release_id):
        release = ws2.get_release_by_id(options.release_id, common_includes)
        print_release(release.get('release'))
    else:
        release = find_release(tracks, common_includes)

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
