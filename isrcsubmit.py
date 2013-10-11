#!/usr/bin/env python
# Copyright (C) 2010-2013 Johannes Dewender
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

__version__ = "2.0.0-beta.5"
AGENT_NAME = "isrcsubmit.py"
DEFAULT_SERVER = "musicbrainz.org"
# starting with highest priority
BACKENDS = ["mediatools", "media_info", "cdrdao", "libdiscid", "discisrc"]
BROWSERS = ["xdg-open", "x-www-browser",
            "firefox", "chromium", "chrome", "opera"]
# The webbrowser module is used when nothing is found in this list.
# This especially happens on Windows and Mac OS X (browser mostly not in PATH)

import os
import re
import sys
import codecs
import getpass
import tempfile
import webbrowser
from datetime import datetime
from optparse import OptionParser
from subprocess import Popen, PIPE, call

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
from musicbrainzngs import AuthenticationError, ResponseError, WebServiceError

SHELLNAME = "isrcsubmit.sh"
if os.path.isfile(SHELLNAME):
    SCRIPTNAME = SHELLNAME
else:
    SCRIPTNAME = os.path.basename(sys.argv[0])

# make code run on Python 2 and 3
try:
    user_input = raw_input
except NameError:
    user_input = input

try:
    unicode_string = unicode
except NameError:
    unicode_string = str

def script_version():
    return "isrcsubmit %s by JonnyJD for MusicBrainz" % __version__

def print_help(option=None, opt=None, value=None, parser=None):
    print(\
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

    if os.name == "nt":
        default_device = "D:"
        # this is "cdaudio" in libdiscid, but no user understands that..
        # cdrdao is not given a device and will try 0,1,0
        # this default is only for libdiscid and mediatools
    elif sys.platform == "darwin":
        # That is the device drutil expects and stable
        # /dev/rdisk1 etc. change with multiple hard disks, dmgs mounted etc.
        default_device = "1"
    else:
        default_device = discid.get_default_device()

    parser = OptionParser(version=script_version(), add_help_option=False)
    parser.set_usage(
            "{prog} [options] [user] [device]\n       {prog} -h".format(
            prog=SCRIPTNAME))
    parser.add_option("-h", action="help",
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
            + " They are tried in this order otherwise." )
    parser.add_option("--browser", metavar="BROWSER",
            help="Program to open URLs. This will be automatically detected"
            " for most setups, if not chosen manually.")
    parser.add_option("--force-submit", action="store_true", default=False,
            help="Always open TOC/disc ID in browser.")
    parser.add_option("--server", metavar="SERVER",
            help="Server to send ISRCs to. Default: %s" % DEFAULT_SERVER)
    parser.add_option("--debug", action="store_true", default=False,
            help="Show debug messages."
            + " Currently shows some backend messages.")
    (options, args) = parser.parse_args(argv[1:])

    # assign positional arguments to options
    if options.user is None and args:
        options.user = args[0]
        args = args[1:]
    if options.device is None:
        if args:
            options.device = args[0]
            args = args[1:]
        else:
            # Mac: device is changed again, when we know the final backend
            # Win: cdrdao is not given a device and will try 0,1,0
            options.device = default_device
    if args:
        print("WARNING: Superfluous arguments: %s" % ", ".join(args))

    # assign remaining options automatically
    options.sane_which = test_which()
    if options.browser is None:
        options.browser = find_browser()
    if options.server is None:
        options.server = DEFAULT_SERVER
    if options.backend and not has_program(options.backend, strict=True):
        print_error("Chosen backend not found. No ISRC extraction possible!")
        print_error2("Make sure that %s is installed." % options.backend)
        sys.exit(-1)
    elif not options.backend:
        options.backend = find_backend()
    print("using %s" % get_prog_version(options.backend))

    return options


def test_which():
    """There are some old/buggy "which" versions on Windows.
    We want to know if the user has a "sane" which we can trust.
    Unxutils has a broken 2.4 version. Which >= 2.16 should be fine.
    """
    with open(os.devnull, "w") as devnull:
        try:
            # "which" should at least find itself
            return_code = call(["which", "which"],
                               stdout=devnull, stderr=devnull)
        except OSError:
            return False        # no which at all
        else:
            if (return_code == 0):
                return True
            else:
                print('warning: your version of the tool "which"'
                      ' is buggy/outdated')
                if os.name == "nt":
                    print('         unxutils is old/broken, GnuWin32 is good.')
                return False

def get_prog_version(prog):
    if prog == "libdiscid":
        version = discid.LIBDISCID_VERSION_STRING
    elif prog == "cdrdao":
        outdata = Popen([prog], stderr=PIPE).communicate()[1]
        version = b" ".join(outdata.splitlines()[0].split()[::2][0:2])
    else:
        version = prog

    return decode(version)

def has_program(program, strict=False):
    """When the backend is only a symlink to another backend,
       we will return False, unless we strictly want to use this backend.
    """
    if program == "libdiscid":
        return "isrc" in discid.FEATURES

    with open(os.devnull, "w") as devnull:
        if options.sane_which:
            p_which = Popen(["which", program], stdout=PIPE, stderr=devnull)
            program_path = p_which.communicate()[0].strip()
            if p_which.returncode == 0:
                # check if it is only a symlink to another backend
                real_program = os.path.basename(os.path.realpath(program_path))
                if program != real_program and (
                        real_program in BACKENDS or real_program in BROWSERS):
                    if strict:
                        print("WARNING: %s is a symlink to %s"
                              % (program, real_program))
                        return True
                    else:
                        return False # use real program (target) instead
                return True
            else:
                return False
        elif program in BACKENDS:
            try:
                # we just try to start these non-interactive console apps
                call([program], stdout=devnull, stderr=devnull)
            except OSError:
                return False
            else:
                return True
        else:
            return False

def find_backend():
    """search for an available backend
    """
    for prog in BACKENDS:
        if has_program(prog):
            backend = prog
            break

    if backend is None:
        print_error("Cannot find a backend to extract the ISRCS!")
        print_error2("Isrcsubmit can work with one of the following:")
        print_error2("  " + ", ".join(backend))
        sys.exit(-1)

    return backend

def find_browser():
    """search for an available browser
    """
    for browser in BROWSERS:
        if has_program(browser):
            return browser

    # This will use the webbrowser module to find a default
    return None

def open_browser(url, exit=False, submit=False):
    """open url in the selected browser, default if none
    """
    if options.browser:
        if exit:
            try:
                if os.name == "nt":
                    # silly but necessary for spaces in the path
                    os.execlp(options.browser, '"' + options.browser + '"', url)
                else:
                    # linux/unix works fine with spaces
                    os.execlp(options.browser, options.browser, url)
            except OSError as err:
                print_error("Couldn't open the url in %s: %s"
                            % (options.browser, str(err)))
                if submit:
                    print_error2("Please submit via:", url)
                sys.exit(1)
        else:
            try:
                if options.debug:
                    Popen([options.browser, url])
                else:
                    with open(os.devnull, "w") as devnull:
                        Popen([options.browser, url], stdout=devnull)
            except FileNotFoundError as err:
                print_error("Couldn't open the url in %s: %s"
                            % (options.browser, str(err)))
                if submit:
                    print_error2("Please submit via:", url)
    else:
        try:
            if options.debug:
                webbrowser.open(url)
            else:
                # this supresses stdout
                webbrowser.get().open(url)
        except webbrowser.Error as err:
            print_error("Couldn't open the url:", str(err))
            if submit:
                print_error2("Please submit via:", url)
        if exit:
            sys.exit(1)

def get_real_mac_device(option_device):
    """drutil takes numbers as drives.

    We ask drutil what device name corresponds to that drive
    in order so we can use it as a drive for libdiscid
    """
    proc = Popen(["drutil", "status", "-drive", option_device], stdout=PIPE)
    try:
        given = proc.communicate()[0].splitlines()[3].split("Name:")[1].strip()
    except IndexError:
        print_error("could not find real device")
        print_error2("maybe there is no disc in the drive?")
        sys.exit(-1)
    # libdiscid needs the "raw" version
    return given.replace("/disk", "/rdisk")

def cp65001(name):
    """This might be buggy, but better than just a LookupError
    """
    if name.lower() == "cp65001":
        return codecs.lookup("utf-8")

codecs.register(cp65001)

def printf(format_string, *args):
    """Print with the % and without additional spaces or newlines
    """
    if not args:
        # make it convenient to use without args -> different to C
        args = (format_string, )
        format_string = "%s"
    sys.stdout.write(format_string % args)

def decode(msg):
    """This will replace unsuitable characters and use stdin encoding
    """
    if isinstance(msg, bytes):
        return msg.decode(sys.stdin.encoding, "replace")
    else:
        return unicode_string(msg)

def encode(msg):
    """This will replace unsuitable characters and use stdout encoding
    """
    if isinstance(msg, unicode_string):
        return msg.encode(sys.stdout.encoding, "replace")
    else:
        return bytes(msg)

def print_encoded(*args):
    """This will replace unsuitable characters and doesn't append a newline
    """
    stringArgs = ()
    for arg in args:
        stringArgs += encode(arg),
    msg = b" ".join(stringArgs)
    if not msg.endswith(b"\n"):
        msg += b" "
    if os.name == "nt":
        os.write(sys.stdout.fileno(), msg)
    else:
        try:
            sys.stdout.buffer.write(msg)
        except AttributeError:
            sys.stdout.write(msg)

def print_release(release, position=None):
    """Print information about a release.

    If the position is given, this should be an entry
    in a list of releases (choice)
    """
    country = (release.get("country") or "").ljust(2)
    date = (release.get("date") or "").ljust(10)
    barcode = (release.get("barcode") or "").rjust(13)
    label_list = release["label-info-list"]
    catnumber_list = []
    for label in label_list:
        cat_number = label.get("catalog-number")
        if cat_number:
            catnumber_list.append(cat_number)
    catnumbers = ", ".join(catnumber_list)

    if position is None:
        print_encoded("Artist:\t\t%s\n" % release["artist-credit-phrase"])
        print_encoded("Release:\t%s" % release["title"])
    else:
        print_encoded("%#2d:" % position)
        print_encoded("%s - %s" % (
                      release["artist-credit-phrase"], release["title"]))
    if release.get("status"):
        print("(%s)" % release["status"])
    else:
        print("")
    if position is None:
        print_encoded("Release Event:\t%s\t%s\n" % (date, country))
        print_encoded("Barcode:\t%s\n" % release.get("barcode") or "")
        print_encoded("Catalog No.:\t%s\n" % catnumbers)
        print_encoded("MusicBrainz ID:\t%s\n" % release["id"])
    else:
        print_encoded("\t%s\t%s\t%s\t%s\n" % (
                      country, date, barcode, catnumbers))

def print_error(*args):
    string_args = tuple([str(arg) for arg in args])
    msg = " ".join(("ERROR:",) + string_args)
    sys.stderr.write(msg + "\n")

def print_error2(*args):
    """following lines for print_error()"""
    string_args = tuple([str(arg) for arg in args])
    msg = " ".join(("      ",) + string_args)
    sys.stderr.write(msg + "\n")

def backend_error(err):
    print_error("Couldn't gather ISRCs with %s: %i - %s"
                % (options.backend, err.errno, err.strerror))
    sys.exit(1)

def ask_for_submission(url, print_url=False):
    if options.force_submit:
        submit_requested = True
    else:
        printf("Would you like to open the browser to submit the disc?")
        submit_requested = user_input(" [y/N] ") == "y"

    if submit_requested:
        open_browser(url, exit=True, submit=True)
    elif print_url:
        print("Please submit the Disc ID with this url:")
        print(url)

class WebService2():
    """A web service wrapper that asks for a password when first needed.

    This uses musicbrainzngs as a wrapper itself.
    """

    def __init__(self, username=None):
        self.auth = False
        self.username = username
        musicbrainzngs.set_hostname(options.server)
        musicbrainzngs.set_useragent(AGENT_NAME, __version__,
                "http://github.com/JonnyJD/musicbrainz-isrcsubmit")

    def authenticate(self):
        """Sets the password if not set already
        """
        if not self.auth:
            print("")
            if self.username is None:
                printf("Please input your MusicBrainz username (empty=abort): ")
                self.username = user_input()
            if len(self.username) == 0:
                print("(aborted)")
                sys.exit(1)
            password = getpass.getpass(
                                    "Please input your MusicBrainz password: ")
            print("")
            musicbrainzngs.auth(self.username, password)
            self.auth = True

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

    def get_release_by_id(self, release_id, includes=[]):
        try:
            return musicbrainzngs.get_release_by_id(release_id,
                                                    includes=includes)
        except WebServiceError as err:
            print_error("Couldn't fetch release: %s" % err)
            sys.exit(1)

    def submit_isrcs(self, tracks2isrcs):
        if options.debug:
            print("tracks2isrcs: %s" % tracks2isrcs)
        while True:
            try:
                self.authenticate()
                musicbrainzngs.submit_isrcs(tracks2isrcs)
            except AuthenticationError as err:
                print_error("Invalid credentials: %s" % err)
                self.auth = False
                self.username = None
                continue
            except WebServiceError as err:
                print_error("Couldn't send ISRCs: %s" % err)
                sys.exit(1)
            else:
                print("Successfully submitted %d ISRCS." % len(tracks2isrcs))
                break



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
            if options.debug:
                print("CD drive #%s corresponds to %s internally"
                      % (device, self._device))
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
        includes = self._common_includes
        results = ws2.get_releases_by_discid(self.id, includes=includes)
        num_results = len(results)
        if options.force_submit:
            print("\nSubmission forced.")
            selected_release = None
        elif num_results == 0:
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
            line = decode(line) # explicitely decode from pipe
            if options.debug:
                printf(line)    # already includes a newline
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
            line = decode(line) # explicitely decode from pipe
            if options.debug:
                printf(line)    # already includes a newline
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
        if options.debug:
            print("Saving toc in %s.." % tmpfile)
        if os.name == "nt" and device != "D:":
            print("warning: cdrdao uses the default device")
            args = [backend, "read-toc", "--fast-toc", "-v", "0", tmpfile]
        else:
            args = [backend, "read-toc", "--fast-toc", "--device", device,
                "-v", "0", tmpfile]
        try:
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
                    if options.debug:
                        printf(line)    # already includes a newline
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
                            % options.backend)
                print_error2("ISRC: %s\ttracks: %s"
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
        if user_input("Do you want to help clean those up? [y/N] ") == "y":
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
            if user_input("Open ISRC in the browser? [Y/n] ") != "n":
                open_browser(url)
                user_input("(press <return> when done with this ISRC) ")


if __name__ == "__main__":

    print("%s" % script_version())
    print("using discid version %s" % discid.__version__)

    # global variables
    options = gather_options(sys.argv)
    ws2 = WebService2(options.user)

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
            print_error(errors, "problems detected")
        if user_input("Do you want to submit? [y/N] ") == "y":
            ws2.submit_isrcs(tracks2isrcs)
        else:
            update_intention = False
            print("Nothing was submitted to the server.")

    # check for overall duplicate ISRCs, including server provided
    if update_intention:
        # the ISRCs are deemed correct, so we can use them to check others
        check_global_duplicates(disc.release, mb_tracks, isrcs)


# vim:set shiftwidth=4 smarttab expandtab:
