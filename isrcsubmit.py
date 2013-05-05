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

__version__ = "2.0.0-dev"
AGENT_NAME = "isrcsubmit.py"
MUSICBRAINZ_SERVER = "musicbrainz.org"
# starting with highest priority
BACKENDS = ["mediatools", "media_info", "cdrdao", "libdiscid", "discisrc"]

DEFAULT_BROWSER = "firefox"

import os
import re
import sys
import codecs
import getpass
import tempfile
from datetime import datetime
from optparse import OptionParser
from subprocess import Popen, PIPE, call

import discid
import musicbrainzngs
from discid import DiscError
from musicbrainzngs import AuthenticationError, ResponseError, WebServiceError

shellname = "isrcsubmit.sh"
if os.path.isfile(shellname):
    scriptname = shellname
else:
    scriptname = os.path.basename(sys.argv[0])

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
        default_device = discid.DEFAULT_DEVICE

    parser = OptionParser(version=script_version(), add_help_option=False)
    parser.set_usage(
            "{prog} [options] [user] [device]\n       {prog} -h".format(
            prog=scriptname))
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
    parser.add_option("-b", "--backend", choices=BACKENDS, metavar="PROGRAM",
            help="Force using a specific backend to extract ISRCs from the"
            + " disc. Possible backends are: %s." % ", ".join(BACKENDS)
            + " They are tried in this order otherwise." )
    parser.add_option("--browser", metavar="BROWSER",
            help="Program to open urls. The default is " + DEFAULT_BROWSER)
    parser.add_option("--force-submit", action="store_true", default=False,
            help="Always open TOC/disc ID in browser.")
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
    if options.browser is None:
        options.browser = DEFAULT_BROWSER
    options.sane_which = test_which()
    if options.backend and not has_backend(options.backend, strict=True):
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
    devnull = open(os.devnull, "w")
    try:
        # "which" should at least find itself (even without searching which.exe)
        return_code = call(["which", "which"], stdout=devnull, stderr=devnull)
    except OSError:
        return False        # no which at all
    else:
        if (return_code == 0):
            return True
        else:
            print('warning: your version of the tool "which" is buggy/outdated')
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

def has_backend(backend, strict=False):
    """When the backend is only a symlink to another backend,
       we will return False, unless we strictly want to use this backend.
    """
    if backend == "libdiscid":
        return "isrc" in discid.FEATURES

    devnull = open(os.devnull, "w")
    if options.sane_which:
        p_which = Popen(["which", backend], stdout=PIPE, stderr=devnull)
        backend_path = p_which.communicate()[0].strip()
        if p_which.returncode == 0:
            # check if it is only a symlink to another backend
            real_backend = os.path.basename(os.path.realpath(backend_path))
            if backend != real_backend and real_backend in BACKENDS: 
                if strict:
                    print("WARNING: %s is a symlink to %s"
                          % (backend, real_backend))
                    return True
                else:
                    return False # use real backend instead, or higher priority
            return True
        else:
            return False
    else:
        try:
            # we just try to start these non-interactive console apps
            call([backend], stdout=devnull, stderr=devnull)
        except OSError:
            return False
        else:
            return True

def find_backend():
    """search for an available backend
    """
    for prog in BACKENDS:
        if has_backend(prog):
            backend = prog
            break

    if backend is None:
        print_error("Cannot find a backend to extract the ISRCS!")
        print_error2("Isrcsubmit can work with one of the following:")
        print_error2("  " + ", ".join(backend))
        sys.exit(-1)

    return backend

def get_real_mac_device(option_device):
    """drutil takes numbers as drives.

    We ask drutil what device name corresponds to that drive
    in order so we can use it as a drive for libdiscid
    """
    p = Popen(["drutil", "status", "-drive", option_device], stdout=PIPE)
    try:
        given = p.communicate()[0].splitlines()[3].split("Name:")[1].strip()
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

def print_release_position(release, pos):
    print_encoded("%d: %s - %s"
                  % (pos, release["artist-credit-phrase"], release["title"]))
    if release.get("status"):
        print("(%s)" % release["status"])
    else:
        print("")
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
    print_encoded("\t%s\t%s\t%s\t%s\n" % (country, date, barcode, catnumbers))

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

class WebService2():
    """A web service wrapper that asks for a password when first needed.

    This uses musicbrainzngs as a wrapper itself.
    """

    def __init__(self, username=None):
        self.auth = False
        self.username = username
        musicbrainzngs.set_hostname(MUSICBRAINZ_SERVER)
        musicbrainzngs.set_useragent(AGENT_NAME, __version__,
                "http://github.com/JonnyJD/musicbrainz-isrcsubmit")

    def authenticate(self):
        """Sets the password if not set already
        """
        if not self.auth:
            print("")
            if self.username is None:
                printf("Please input your MusicBrainz username: ")
                self.username = user_input()
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
        try:
            self.authenticate()
            musicbrainzngs.submit_isrcs(tracks2isrcs)
        except AuthenticationError as err:
            print_error("Invalid credentials: %s" % err)
            sys.exit(1)
        except WebServiceError as err:
            print_error("Couldn't send ISRCs: %s" % err)
            sys.exit(1)
        else:
            print("Successfully submitted %d ISRCS." % len(tracks2isrcs))



class Disc(object):
    def read_disc(self):
        try:
            # calculate disc ID from disc
            if self._backend == "libdiscid":
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
        self._release = None
        self._backend = backend
        self._verified = verified
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
        return self._disc.submission_url

    @property
    def release(self):
        """The corresponding MusicBrainz release

        This will ask the user to choose if the discID is ambiguous.
        """
        if self._release is None:
            self._release = self.get_release(self._verified)
            # can still be None
        return self._release

    def get_release(self, verified=False):
        """Find the corresponding MusicBrainz release

        This will ask the user to choose if the discID is ambiguous.
        """
        includes=["artists", "labels", "recordings", "isrcs",
                  "artist-credits"] # the last one only for cleanup
        results = ws2.get_releases_by_discid(self.id, includes=includes)
        num_results = len(results)
        if options.force_submit:
            print("\nSubmission forced.")
            self._release = None
        elif num_results == 0:
            print("\nThis Disc ID is not in the database.")
            self._release = None
        elif num_results > 1:
            print("\nThis Disc ID is ambiguous:")
            for i in range(num_results):
                release = results[i]
                # printed list is 1..n, not 0..n-1 !
                print_release_position(release, i + 1)
            try:
                num =  user_input("Which one do you want? [1-%d] "
                                  % num_results)
                if int(num) not in range(1, num_results + 1):
                    raise IndexError
                self._release = results[int(num) - 1]
            except (ValueError, IndexError):
                print_error("Invalid Choice")
                sys.exit(1)
            except KeyboardInterrupt:
                print("\nexiting..")
                sys.exit(1)
        else:
            self._release = results[0]

        if self._release and self._release["id"] is None:
            # a "release" that is only a stub has no musicbrainz id
            print("\nThere is only a stub in the database:")
            print_encoded("%s - %s\n\n"
                          % (self._release["artist-credit-phrase"],
                             self._release["title"]))
            self._release = None        # don't use stub
            verified = True             # the id is verified by the stub

        if self._release is None or options.force_submit:
            if verified:
                url = self.submission_url
                if options.force_submit:
                    submit_requested = True
                else:
                    printf("Would you like to open the browser"
                           + " to submit the disc?")
                    submit_requested = user_input(" [y/N] ") == "y"
                if submit_requested:
                    try:
                        if os.name == "nt":
                            # silly but necessary for spaces in the path
                            os.execlp(options.browser,
                                    '"' + options.browser + '"', url)
                        else:
                            # linux/unix works fine with spaces
                            os.execlp(options.browser, options.browser, url)
                    except OSError as err:
                        print_error("Couldn't open the url in %s: %s"
                                    % (options.browser, str(err)))
                        print_error2("Please submit it via:", url)
                        sys.exit(1)
                else:
                    print("Please submit the Disc ID with this url:")
                    print(url)
                    sys.exit(1)
            else:
                print("recalculating to re-check..")
                self.read_disc()
                self.get_release(verified=True)

        return self._release

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
                m = re.match(pattern, track.isrc)
                if m is None:
                    print("no valid ISRC: %s" % track.isrc)
                else:
                    backend_output.append((track.number, track.isrc))

    # redundant to "libdiscid", but this might be handy for prerelease testing
    elif backend == "discisrc":
        pattern = \
            br'Track\s+([0-9]+)\s+:\s+([A-Z]{2})-?([A-Z0-9]{3})-?(\d{2})-?(\d{5})'
        try:
            if sys.platform == "darwin":
                device = get_real_mac_device(device)
            p = Popen([backend, device], stdout=PIPE)
            isrcout = p.stdout
        except OSError as err:
            backend_error(err)
        for line in isrcout:
            if options.debug:
                printf(line)    # already includes a newline
            if line.startswith(b"Track") and len(line) > 12:
                m = re.search(pattern, line)
                if m is None:
                    print("can't find ISRC in: %s" % line)
                    continue
                track_number = int(m.group(1))
                isrc = m.group(2) + m.group(3) + m.group(4) + m.group(5)
                isrc = decode(isrc)
                backend_output.append((track_number, isrc))

    # media_info is a preview version of mediatools, both are for Windows
    # this does some kind of raw read
    elif backend in ["mediatools", "media_info"]:
        pattern = \
            br'ISRC\s+([0-9]+)\s+([A-Z]{2})-?([A-Z0-9]{3})-?(\d{2})-?(\d{5})'
        if backend == "mediatools":
            args = [backend, "drive", device, "isrc"]
        else:
            args = [backend, device]
        try:
            p = Popen(args, stdout=PIPE)
            isrcout = p.stdout
        except OSError as err:
            backend_error(err)
        for line in isrcout:
            if options.debug:
                printf(line)    # already includes a newline
            if line.startswith(b"ISRC") and not line.startswith(b"ISRCS"):
                m = re.search(pattern, line)
                if m is None:
                    print("can't find ISRC in: %s" % line)
                    continue
                track_number = int(m.group(1))
                isrc = m.group(2) + m.group(3) + m.group(4) + m.group(5)
                isrc = decode(isrc)
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
            p = Popen(args, stdout=devnull, stderr=devnull)
            if p.wait() != 0:
                print_error("%s returned with %i" % (backend, p.returncode))
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
                            m = re.match(pattern, isrc)
                            if m is None:
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
                tracks2isrcs[own_track["id"]] = [isrc]
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

            url = "http://%s/isrc/%s" % (MUSICBRAINZ_SERVER, isrc)
            if user_input("Open ISRC in the browser? [Y/n] ") != "n":
                Popen([options.browser, url])
                user_input("(press <return> when done with this ISRC) ")


if __name__ == "__main__":

    print("%s" % script_version())

    # global variables
    options = gather_options(sys.argv)
    ws2 = WebService2(options.user)

    disc = get_disc(options.device, options.backend)
    release_id = disc.release["id"]         # implicitly fetches release
    print("")
    print_encoded('Artist:\t\t%s\n' % disc.release["artist-credit-phrase"])
    print_encoded('Release:\t%s\n' % disc.release["title"])

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
