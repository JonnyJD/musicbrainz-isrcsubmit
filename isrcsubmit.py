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

Various backends are used to gather the ISRCs
and python-musicbrainz2 to submit them.
The project is hosted on
https://github.com/JonnyJD/musicbrainz-isrcsubmit
"""

AGENT_NAME = "isrcsubmit.py"
# starting with highest priority
BACKENDS = ["mediatools", "media_info", "cdrdao", "libdiscid", "discisrc"]


import os
import re
import sys
import logging
import tempfile
from datetime import datetime
from optparse import OptionParser
from subprocess import Popen, PIPE
import isrcshared
from isrcshared import __version__, print_error, decode, \
    printf, user_input, open_browser, print_release, \
    has_program, logger, print_encoded, WebService2, \
    config_path, setDefaultOptions, encode

try:
    import discid
    from discid import DiscError
except ImportError:
    try:
        from libdiscid.compat import discid
        from libdiscid.compat.discid import DiscError
    except ImportError:
        # When both are not available, raise exception for python-discid
        import discid

import musicbrainzngs
from musicbrainzngs import ResponseError, WebServiceError

try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import ConfigParser

if os.name == "nt":
    SHELLNAME = "isrcsubmit.bat"
else:
    SHELLNAME = "isrcsubmit.sh"
if os.path.isfile(SHELLNAME):
    SCRIPTNAME = SHELLNAME
else:
    SCRIPTNAME = os.path.basename(sys.argv[0])

# global variables
options = None
ws2 = None


def script_version():
    return "isrcsubmit %s by JonnyJD for MusicBrainz" % __version__


def print_help(option=None, opt=None, value=None, parser=None):
    print("%s" % script_version())
    print(
"""
This python script extracts ISRCs from audio cds and submits them to MusicBrainz (musicbrainz.org).
You need to have a MusicBrainz account, specify the username and will be asked for your password every time you execute the script.

Isrcsubmit will warn you if there are any problems and won't actually submit anything to MusicBrainz without giving a final choice.

Isrcsubmit will warn you if any duplicate ISRCs are detected and help you fix priviously inserted duplicate ISRCs.
The ISRC-track relationship we found on our disc is taken as our correct evaluation.
""")
    parser.print_usage()
    print("""\
Please report bugs on https://github.com/JonnyJD/musicbrainz-isrcsubmit""")
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
        self._track = track
        self._recording = track["recording"]
        self._number = number
        # check that we found the track with the correct number
        assert(int(self._track["position"]) == self._number)

    def __eq__(self, other):
        return self["id"] == other["id"]

    def __getitem__(self, item):
        try:
            return self._recording[item]
        except KeyError:
            return self._track[item]

    def get(self, item, default=None):
        try:
            return self._recording.get(item, default)
        except KeyError:
            return self._track.get(item, default)


class OwnTrack(Track):
    """A track found on an analyzed (own) disc"""
    pass


def gather_options(argv):
    global options

    if sys.platform == "darwin":
        # That is the device drutil expects and stable
        # /dev/rdisk1 etc. change with multiple hard disks, dmgs mounted etc.
        # libdiscid < 0.6.0 can't handle drive numbers
        default_device = "1"
    else:
        default_device = discid.get_default_device()

    config = ConfigParser()
    config.read(config_path())

    parser = OptionParser(version=script_version(), add_help_option=False)
    parser.set_usage(
            "{prog} [options] [user] [device]\n       {prog} -h".format(
            prog=SCRIPTNAME))
    parser.add_option("-h", action="callback", callback=print_usage,
            help="Short usage help")
    parser.add_option("--help", action="callback", callback=print_help,
            help="Complete help for the script")
    parser.add_option("-u", "--user", metavar="USERNAME",
            help="MusicBrainz username, if not given as argument.")
    # note that -d previously stand for debug
    parser.add_option("-d", "--device", metavar="DEVICE",
            help="CD device with a loaded audio cd, if not given as argument."
            + " The default is %s." % default_device)
    parser.add_option("--release-id", metavar="RELEASE_ID",
            help="Optional MusicBrainz ID of the release."
            + " This will be gathered if not given.")
    parser.add_option("-b", "--backend", choices=BACKENDS, metavar="PROGRAM",
            help="Force using a specific backend to extract ISRCs from the"
            + " disc. Possible backends are: %s." % ", ".join(BACKENDS)
            + " They are tried in this order otherwise.")
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
    if options.device is None and args:
        options.device = args[0]
        args = args[1:]
    if args:
        logger.warning("Superfluous arguments: %s", ", ".join(args))

    setDefaultOptions(config, options)

    # assign remaining options automatically
    if options.device is None and config.has_option("general", "device"):
        options.device = config.get("general", "device")
    if options.device is None:
        options.device = default_device

    if options.backend is None and config.has_option("general", "backend"):
        options.backend = config.get("general", "backend")
        if options.backend not in BACKENDS:
            print_error("Backend given in config file is not a valid choice.",
                        "Choose a backend from %s" % ", ".join(BACKENDS))
            sys.exit(-1)
    if options.backend and not has_program(options.backend, BACKENDS, strict=True):
        print_error("Chosen backend not found. No ISRC extraction possible!",
                    "Make sure that %s is installed." % options.backend)
        sys.exit(-1)
    elif not options.backend:
        options.backend = find_backend()

    return options


def get_prog_version(prog):
    if prog == "libdiscid":
        version = discid.LIBDISCID_VERSION_STRING
    elif prog == "cdrdao":
        outdata = Popen([prog], stderr=PIPE).communicate()[1]
        version = b" ".join(outdata.splitlines()[0].split()[::2][0:2])
    else:
        version = prog

    return decode(version)


def find_backend():
    """search for an available backend
    """
    backend = None
    for prog in BACKENDS:
        if prog == "libdiscid":
            return "isrc" in discid.FEATURES
        elif has_program(prog, BACKENDS):
            backend = prog
            break

    if backend is None:
        print_error("Cannot find a backend to extract the ISRCS!",
                    "Isrcsubmit can work with one of the following:",
                    "  " + ", ".join(BACKENDS))
        sys.exit(-1)

    return backend


def get_real_mac_device(option_device):
    """drutil takes numbers as drives.

    We ask drutil what device name corresponds to that drive
    in order so we can use it as a drive for libdiscid
    """
    proc = Popen(["drutil", "status", "-drive", option_device], stdout=PIPE)
    try:
        given = proc.communicate()[0].splitlines()[3].split("Name:")[1].strip()
    except IndexError:
        print_error("could not find real device",
                     "maybe there is no disc in the drive?")
        sys.exit(-1)
    # libdiscid needs the "raw" version
    return given.replace("/disk", "/rdisk")


def backend_error(err):
    print_error("Couldn't gather ISRCs with %s: %i - %s"
                % (options.backend, err.errno, err.strerror))
    sys.exit(1)


def ask_for_submission(url, print_url=False):
    if options.force_submit:
        submit_requested = True
    else:
        printf("Would you like to open the browser to submit the disc?")
        submit_requested = user_input(" [y/N] ").lower() == "y"

    if submit_requested:
        open_browser(url, exit=True, submit=True)
    elif print_url:
        print("Please submit the Disc ID with this url:")
        print(url)


class WebService2(isrcshared.WebService2):
    """A web service wrapper that asks for a password when first needed.

    This uses musicbrainzngs as a wrapper itself.
    """

    def __init__(self, username=None):
        isrcshared.WebService2.__init__(self, username)
        musicbrainzngs.set_useragent(AGENT_NAME, __version__,
                                         "http://github.com/SheamusPatt/musicbrainz-isrcsubmit")

    def get_releases_by_discid(self, disc_id, includes=[]):
        try:
            response = musicbrainzngs.get_releases_by_discid(disc_id,
                                                             includes=includes)
        except ResponseError as err:
            if err.cause.code == 404:
                return []
            else:
                print_error("Couldn't fetch release: %s" % err)
                sys.exit(1)
        except WebServiceError as err:
            print_error("Couldn't fetch release: %s" % err)
            sys.exit(1)
        else:
            if response.get("disc"):
                return response["disc"]["release-list"]
            else:
                return []


class Disc(object):
    def read_disc(self):
        try:
            # calculate disc ID from disc
            if self._backend == "libdiscid" and not options.force_submit:
                disc = discid.read(self._device, features=["mcn", "isrc"])
            else:
                disc = discid.read(self._device)
            self._disc = disc
        except DiscError as err:
            print_error("DiscID calculation failed: %s" % err)
            sys.exit(1)

    def __init__(self, device, backend, verified=False):
        if sys.platform == "darwin":
            self._device = get_real_mac_device(device)
            logger.info("CD drive #%s corresponds to %s internally",
                        device, self._device)
        else:
            self._device = device
        self._disc = None
        self._release = None
        self._backend = backend
        self._verified = verified
        self._asked_for_submission = False
        self._common_includes=["artists", "labels", "recordings", "isrcs",
                               "artist-credits"] # the last one only for cleanup
        self.read_disc()        # sets self._disc

    @property
    def id(self):
        return self._disc.id

    @property
    def mcn(self):
        mcn = self._disc.mcn
        if mcn and int(mcn) > 0:
            return mcn
        else:
            return None

    @property
    def tracks(self):
        return self._disc.tracks

    @property
    def submission_url(self):
        url = self._disc.submission_url
        # mm.mb.o points to mb.o, if present in the url
        url = url.replace("//mm.", "//")
        return url.replace("musicbrainz.org", options.server)

    @property
    def asked_for_submission(self):
        return self._asked_for_submission

    @property
    def release(self):
        """The corresponding MusicBrainz release

        This will ask the user to choose if the discID is ambiguous.
        """
        if self._release is None:
            self.get_release(self._verified)
            # can still be None
        return self._release

    def fetch_release(self, release_id):
        """Check if a pre-selected release has the correct TOC attached
        """
        includes = self._common_includes + ["discids"]
        result = ws2.get_release_by_id(release_id, includes=includes)
        release = result["release"]
        for medium in release["medium-list"]:
            for disc in medium["disc-list"]:
                if disc["id"] == self.id:
                    return release
        # disc ID is not attached to the release
        return None

    def select_release(self):
        """Find the corresponding MusicBrainz release by disc ID

        This will ask the user to choose if the discID is ambiguous.
        """
        if options.force_submit:
            # If asked to force submission, just return None straight
            # away and skip all other logic, e.g. unneeded WS2 requests.
            print("\nSubmission forced.")
            return None
        includes = self._common_includes
        results = ws2.get_releases_by_discid(self.id, includes=includes)
        num_results = len(results)
        if num_results == 0:
            print("\nThis Disc ID is not in the database.")
            selected_release = None
        elif num_results > 1:
            print("\nThis Disc ID is ambiguous:")
            print(" 0: none of these\n")
            self._asked_for_submission = True
            for i in range(num_results):
                release = results[i]
                # printed list is 1..n, not 0..n-1 !
                print_release(release, i + 1)
            try:
                num =  user_input("Which one do you want? [0-%d] "
                                  % num_results)
                if int(num) not in range(0, num_results + 1):
                    raise IndexError
                if int(num) == 0:
                    ask_for_submission(self.submission_url, print_url=True)
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
            selected_release = results[0]

        return selected_release

    def get_release(self, verified=False):
        """This will get a release the ISRCs will be added to.
        """

        # check if a release was pre-selected
        if options.release_id:
            chosen_release = self.fetch_release(options.release_id)
        else:
            chosen_release = self.select_release()

        if chosen_release and chosen_release["id"] is None:
            # a "release" that is only a stub has no musicbrainz id
            print("\nThere is only a stub in the database:")
            print_encoded("%s - %s\n\n"
                          % (chosen_release["artist-credit-phrase"],
                             chosen_release["title"]))
            chosen_release = None       # don't use stub
            verified = True             # the id is verified by the stub

        if chosen_release is None or options.force_submit:
            if verified:
                url = self.submission_url
                ask_for_submission(url, print_url=True)
                sys.exit(1)
            else:
                print("recalculating to re-check..")
                self.read_disc()
                self.get_release(verified=True)

        self._release = chosen_release
        return chosen_release


def get_disc(device, backend, verified=False):
    """This creates a Disc object, which also calculates the id of the disc
    """
    disc = Disc(device, backend, verified)
    print('\nDiscID:\t\t%s' % disc.id)
    if disc.mcn:
        print('MCN/EAN:\t%s' % disc.mcn)
    print('Tracks on disc:\t%d' % len(disc.tracks))
    return disc


def gather_isrcs(disc, backend, device):
    """read the disc in the device with the backend and extract the ISRCs
    """
    backend_output = []
    devnull = open(os.devnull, "w")

    if backend == "libdiscid":
        pattern = r'[A-Z]{2}[A-Z0-9]{3}\d{2}\d{5}'
        for track in disc.tracks:
            if track.isrc:
                match = re.match(pattern, track.isrc)
                if match is None:
                    print("no valid ISRC: %s" % track.isrc)
                else:
                    backend_output.append((track.number, track.isrc))

    # redundant to "libdiscid", but this might be handy for prerelease testing
    elif backend == "discisrc":
        pattern = \
            r'Track\s+([0-9]+)\s+:\s+([A-Z]{2})-?([A-Z0-9]{3})-?(\d{2})-?(\d{5})'
        try:
            if sys.platform == "darwin":
                device = get_real_mac_device(device)
            proc = Popen([backend, device], stdout=PIPE)
            isrcout = proc.stdout
        except OSError as err:
            backend_error(err)
        for line in isrcout:
            line = decode(line) # explicitly decode from pipe
            ext_logger = logging.getLogger("discisrc")
            ext_logger.debug(line.rstrip())    # rstrip newline
            if line.startswith("Track") and len(line) > 12:
                match = re.search(pattern, line)
                if match is None:
                    print("can't find ISRC in: %s" % line)
                    continue
                track_number = int(match.group(1))
                isrc = ("%s%s%s%s" % (match.group(2), match.group(3),
                                      match.group(4), match.group(5)))
                backend_output.append((track_number, isrc))

    # media_info is a preview version of mediatools, both are for Windows
    # this does some kind of raw read
    elif backend in ["mediatools", "media_info"]:
        pattern = \
            r'ISRC\s+([0-9]+)\s+([A-Z]{2})-?([A-Z0-9]{3})-?(\d{2})-?(\d{5})'
        if backend == "mediatools":
            args = [backend, "drive", device, "isrc"]
        else:
            args = [backend, device]
        try:
            proc = Popen(args, stdout=PIPE)
            isrcout = proc.stdout
        except OSError as err:
            backend_error(err)
        for line in isrcout:
            line = decode(line) # explicitly decode from pipe
            ext_logger = logging.getLogger("mediatools")
            ext_logger.debug(line.rstrip())    # rstrip newline
            if line.startswith("ISRC") and not line.startswith("ISRCS"):
                match = re.search(pattern, line)
                if match is None:
                    print("can't find ISRC in: %s" % line)
                    continue
                track_number = int(match.group(1))
                isrc = ("%s%s%s%s" % (match.group(2), match.group(3),
                                      match.group(4), match.group(5)))
                backend_output.append((track_number, isrc))

    # cdrdao will create a temp file and we delete it afterwards
    # cdrdao is also available for windows
    # this will also fetch ISRCs from CD-TEXT
    elif backend == "cdrdao":
        # no byte pattern, file is opened as unicode
        pattern = r'[A-Z]{2}[A-Z0-9]{3}\d{2}\d{5}'
        tmpname = "cdrdao-%s.toc" % datetime.now()
        tmpname = tmpname.replace(":", "-")     # : is invalid on windows
        tmpfile = os.path.join(tempfile.gettempdir(), tmpname)
        logger.info("Saving toc in %s..", tmpfile)
        if os.name == "nt":
            if device != discid.get_default_device():
                logger.warning("cdrdao uses the default device")
            args = [backend, "read-toc", "-v", "0", tmpfile]
        else:
            args = [backend, "read-toc", "--device", device, "-v", "0", tmpfile]
        try:
            if options.debug:
                proc = Popen(args, stdout=devnull)
            else:
                proc = Popen(args, stdout=devnull, stderr=devnull)
            if proc.wait() != 0:
                print_error("%s returned with %i" % (backend, proc.returncode))
                sys.exit(1)
        except OSError as err:
            backend_error(err)
        else:
            # that file seems to be opened in Unicode mode in Python 3
            with open(tmpfile, "r") as toc:
                track_number = None
                for line in toc:
                    ext_logger = logging.getLogger("cdrdao")
                    ext_logger.debug(line.rstrip())    # rstrip newline
                    words = line.split()
                    if words:
                        if words[0] == "//":
                            track_number = int(words[2])
                        elif words[0] == "ISRC" and track_number is not None:
                            isrc = "".join(words[1:]).strip('"- ')
                            match = re.match(pattern, isrc)
                            if match is None:
                                print("no valid ISRC: %s" % isrc)
                            else:
                                backend_output.append((track_number, isrc))
                                # safeguard against missing trackNumber lines
                                # or duplicated ISRC tags (like in CD-Text)
                                track_number = None
        finally:
            try:
                os.unlink(tmpfile)
            except OSError:
                pass

    devnull.close()
    return backend_output


def check_isrcs_local(backend_output, mb_tracks):
    """check backend_output for (local) duplicates and inconsistencies
    """
    isrcs = dict()          # isrcs found on disc
    tracks2isrcs = dict()   # isrcs to be submitted
    errors = 0

    for (track_number, isrc) in backend_output:
        if isrc not in isrcs:
            isrcs[isrc] = Isrc(isrc)
            # check if we found this ISRC for multiple tracks
            with_isrc = [item for item in backend_output if item[1] == isrc]
            if len(with_isrc) > 1:
                track_list = [str(item[0]) for item in with_isrc]
                print_error("%s gave the same ISRC for multiple tracks!"
                            % options.backend,
                            "ISRC: %s\ttracks: %s"
                            % (isrc, ", ".join(track_list)))
                errors += 1
        try:
            track = mb_tracks[track_number - 1]
        except IndexError:
            print_error("ISRC %s found for unknown track %d"
                        % (isrc, track_number))
            errors += 1
        else:
            own_track = OwnTrack(track, track_number)
            isrcs[isrc].add_track(own_track)
            # check if the ISRC was already added to the track
            if isrc not in own_track.get("isrc-list", []):
                # single isrcs work in python-musicbrainzngs 0.4, but not 0.3
                # lists of isrcs don't work in 0.4 though, see pymbngs #113
                tracks2isrcs[own_track["id"]] = isrc
                print("found new ISRC for track %d: %s"
                      % (track_number, isrc))
            else:
                print("%s is already attached to track %d"
                      % (isrc, track_number))

    return isrcs, tracks2isrcs, errors


def check_global_duplicates(release, mb_tracks, isrcs):
    """Help cleaning up global duplicates with the information we got
    from our disc.
    """
    duplicates = 0
    # add already attached ISRCs
    for i in range(0, len(mb_tracks)):
        track = mb_tracks[i]
        track_number = i + 1
        track = Track(track, track_number)
        for isrc in track.get("isrc-list", []):
            # only check ISRCS we also found on our disc
            if isrc in isrcs:
                isrcs[isrc].add_track(track)
    # check if we have multiple tracks for one ISRC
    for isrc in isrcs:
        if len(isrcs[isrc].get_tracks()) > 1:
            duplicates += 1

    if duplicates > 0:
        printf("\nThere were %d ISRCs ", duplicates)
        print("that are attached to multiple tracks on this release.")
        choice = user_input("Do you want to help clean those up? [y/N] ")
        if choice.lower() == "y":
            cleanup_isrcs(release, isrcs)


def cleanup_isrcs(release, isrcs):
    """Show information about duplicate ISRCs

    Our attached ISRCs should be correct -> helps to delete from other tracks
    """
    for isrc in isrcs:
        tracks = isrcs[isrc].get_tracks()
        if len(tracks) > 1:
            print("\nISRC %s attached to:" % isrc)
            for track in tracks:
                printf("\t")
                artist = track.get("artist-credit-phrase")
                if artist and artist != release["artist-credit-phrase"]:
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
                if isinstance(track, OwnTrack):
                    print("   [OUR EVALUATION]")
                else:
                    print("")

            url = "http://%s/isrc/%s" % (options.server, isrc)
            if user_input("Open ISRC in the browser? [Y/n] ").lower() != "n":
                open_browser(url)
                user_input("(press <return> when done with this ISRC) ")


def main(argv):
    global options
    global ws2

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
        logfile = "isrcsubmit.log"
        file_handler = logging.FileHandler(logfile, mode='w',
                            encoding="utf8", delay=True)
        formatter = logging.Formatter("%(levelname)s:%(name)s: %(message)s")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.info("Writing debug log to %s", logfile)
        logging.getLogger().addHandler(file_handler)

        # add context to log file (DEBUG only added there)
        logger.debug(script_version())

    logger.info("using discid version %s", discid.__version__)
    print("using %s" % get_prog_version(options.backend))

    disc = get_disc(options.device, options.backend)
    disc.get_release()
    print("")
    print_release(disc.release)
    if not disc.asked_for_submission:
        print("")
        print("Is this information different for your release?")
        ask_for_submission(disc.submission_url)

    media = []
    for medium in disc.release["medium-list"]:
        for disc_entry in medium["disc-list"]:
            if disc_entry["id"] == disc.id:
                media.append(medium)
                break
    if len(media) > 1:
        raise DiscError("number of discs with id: %d" % len(media))
    mb_tracks = media[0]["track-list"]

    print("")
    # (track, isrc)
    backend_output = gather_isrcs(disc, options.backend, options.device)
    # list, dict
    isrcs, tracks2isrcs, errors = check_isrcs_local(backend_output, mb_tracks)

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
        check_global_duplicates(disc.release, mb_tracks, isrcs)

if __name__ == "__main__":
    main(sys.argv)


# vim:set shiftwidth=4 smarttab expandtab:
