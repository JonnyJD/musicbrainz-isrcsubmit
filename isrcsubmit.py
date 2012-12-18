#!/usr/bin/env python2
# Copyright (C) 2010-2012 Johannes Dewender
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

Icedax is used to gather the ISRCs and python-musicbrainz2 to submit them.
The project is hosted on
https://github.com/JonnyJD/musicbrainz-isrcsubmit
and the script is also available on
http://kraehen.org/isrcsubmit.py
"""

isrcsubmitVersion = "0.5.1"
agentName = "isrcsubmit-jonnyjd-" + isrcsubmitVersion
# starting with highest priority
backends = ["mediatools", "media_info", "cdrdao", "cd-info",
            "cdda2wav", "icedax", "drutil"]
packages = {"cd-info": "libcdio", "cdda2wav": "cdrtools", "icedax": "cdrkit"}

import os
import re
import sys
import getpass
import tempfile
from datetime import datetime
from optparse import OptionParser
from subprocess import Popen, PIPE, call
from distutils.version import StrictVersion
from musicbrainz2 import __version__ as musicbrainz2_version
from musicbrainz2.disc import readDisc, DiscError, getSubmissionUrl
from musicbrainz2.model import Track
from musicbrainz2.webservice import WebService, Query
from musicbrainz2.webservice import ReleaseFilter, ReleaseIncludes
from musicbrainz2.webservice import RequestError, AuthenticationError
from musicbrainz2.webservice import ConnectionError, WebServiceError

# using a shellscript to get the correct python version (2.5 - 2.7)
shellname = "isrcsubmit.sh"
if os.path.isfile(shellname):
    scriptname = shellname
else:
    scriptname = os.path.basename(sys.argv[0])

def scriptVersion(option=None, opt=None, value=None, parser=None):
    return "isrcsubmit %s by JonnyJD for MusicBrainz" % isrcsubmitVersion

def printHelp(option=None, opt=None, value=None, parser=None):
    print \
"""
This python script extracts ISRCs from audio cds and submits them to MusicBrainz (musicbrainz.org).
You need to have a MusicBrainz account, specify the username and will be asked for your password every time you execute the script.

Isrcsubmit will warn you if there are any problems and won't actually submit anything to MusicBrainz without giving a final choice.

Isrcsubmit will warn you if any duplicate ISRCs are detected and help you fix priviously inserted duplicate ISRCs.
The ISRC-track relationship we found on our disc is taken as our correct evaluation.

A note on Multi-disc-releases:

Isrcsubmit uses the MusicBrainz web service version 1.
This api is not tailored for MusicBrainz NGS (Next Generation Schema) and expects to have one release per disc. So it does not know which tracks are on a specific disc and lists all tracks in the overall release.
In order to attach the ISRCs to the correct tracks an offset is necessary for multi-disc-releases. For the first disc and last disc this can be guessed easily. Starting with 3 discs irscsubmit will ask you for the offset of the "middle discs".
The offset is the sum of track counts on all previous discs.

Example:
    disc 1: (13 tracks)
    disc 2: (17 tracks)
    disc 3:  19 tracks (current disc)
    disc 4: (23 tracks)
    number of tracks altogether: 72

The offset we have to use is 30 (= 13 + 17)

Isrcsubmit only knows how many tracks the current disc has and the total number of tracks on the release given by the web service. So the offset must be between 0 and 53 (= 72 - 19), which is the range isrcsubmit lets you choose from.

The number of discs in the release and the position of this disc give by isrcsubmit is not necessarily correct. There can be multiple disc IDs per actual disc. You should only count tracks on your actual discs.
Isrcsubmit can give you a link for an overview of the disc IDs for your release.
"""
    parser.print_usage()
    print """\
Please report bugs on https://github.com/JonnyJD/musicbrainz-isrcsubmit"""
    sys.exit(0)


class Isrc(object):
    def __init__(self, isrc, track=None):
        self._id = isrc
        self._tracks = []
        if track is not None:
            self._tracks.append(track)

    def addTrack(self, track):
        if track not in self._tracks:
            self._tracks.append(track)

    def getTracks(self):
        return self._tracks

    def getTrackNumbers(self):
        numbers = []
        for track in self._tracks:
            numbers.append(track.getNumber())
        return ", ".join(map(str, numbers))


class EqTrack(Track):
    """track with equality checking

    This makes it easy to check if this track is already in a collection.
    Only the element already in the collection needs to be hashable.

    """
    def __init__(self, track):
        self._track = track

    def __eq__(self, other):
        return self.getId() == other.getId()

    def getId(self):
        return self._track.getId()

    def getArtist(self):
        return self._track.getArtist()

    def getTitle(self):
        return self._track.getTitle()

    def getISRCs(self):
        return self._track.getISRCs()

class NumberedTrack(EqTrack):
    """A track found on an analyzed (own) disc

    """
    def __init__(self, track, number):
        self._track = track
        self._number = number

    def getNumber(self):
        """The track number on the analyzed disc"""
        return self._number

class OwnTrack(NumberedTrack):
    """A track found on an analyzed (own) disc

    """
    pass

def gatherOptions(argv):
    if os.name == "nt":
        defaultDevice = "D:"
        # cdrdao is not given a device and will try 0,1,0
        # this default is only for libdiscid and mediatools
    else:
        defaultDevice = "/dev/cdrom"
    defaultBrowser = "firefox"
    prog = scriptname
    parser = OptionParser(version=scriptVersion(), add_help_option=False)
    parser.set_usage("%s [options] [user] [device]\n       %s -h" % (prog, prog))
    parser.add_option("-h", action="help",
            help="Short usage help")
    parser.add_option("--help", action="callback", callback=printHelp,
            help="Complete help for the script")
    parser.add_option("-u", "--user", metavar="USERNAME",
            help="MusicBrainz username, if not given as argument.")
    # note that -d previously stand for debug
    parser.add_option("-d", "--device", metavar="DEVICE",
            help="CD device with a loaded audio cd, if not given as argument."
            + " The default is " + defaultDevice + " (and '1' for mac)")
    parser.add_option("-b", "--backend", choices=backends, metavar="PROGRAM",
            help="Force using a specific backend to extract ISRCs from the"
            + " disc. Possible backends are: %s." % ", ".join(backends)
            + " They are tried in this order otherwise." )
    parser.add_option("--browser", metavar="BROWSER",
            help="Program to open urls. The default is " + defaultBrowser)
    parser.add_option("--debug", action="store_true", default=False,
            help="Show debug messages."
            + " Currently shows some backend messages.")
    (options, args) = parser.parse_args(argv[1:])

    # assign positional arguments to options
    if options.user is None and len(args) > 0:
        options.user = args[0]
        args = args[1:]
    if options.device is None:
        if len(args) > 0:
            options.device = args[0]
            args = args[1:]
        else:
            # Mac: device is changed again, when we know the final backend
            # Win: cdrdao is not given a device and will try 0,1,0
            options.device = defaultDevice
    if options.browser is None:
        options.browser = defaultBrowser
    if len(args) > 0:
        print "WARNING: Superfluous arguments:", ", ".join(args)
    if options.backend and not hasBackend(options.backend, strict=True):
        printError("Chosen backend not found. No ISRC extraction possible!")
        printError2("Make sure that %s is installed." % options.backend)
        sys.exit(-1)

    return options


def getProgVersion(prog):
    if prog == "icedax":
        return Popen([prog, "--version"], stderr=PIPE).communicate()[1].strip()
    elif prog == "cdda2wav":
        outdata = Popen([prog, "-version"], stdout=PIPE).communicate()[0]
        return " ".join(outdata.splitlines()[0].split()[0:2])
    elif prog == "cdrdao":
        outdata = Popen([prog], stderr=PIPE).communicate()[1]
        return " ".join(outdata.splitlines()[0].split()[::2][0:2])
    elif prog == "cd-info":
        outdata = Popen([prog, "--version"], stdout=PIPE).communicate()[0]
        return " ".join(outdata.splitlines()[0].split()[::2][0:2])
    elif prog == "drutil":
        outdata = Popen([prog, "version"], stdout=PIPE).communicate()[0]
        version = prog
        for line in outdata.splitlines():
            if len(line) > 0: version += " " + line.split(":")[1].strip()
        return version
    else:
        return prog

def hasBackend(backend, strict=False):
    """When the backend is only a symlink to another backend,
       we will return False, unless we strictly want to use this backend.
    """
    devnull = open(os.devnull, "w")
    if saneWhich:
        p_which = Popen(["which", backend], stdout=PIPE, stderr=devnull)
        backend_path = p_which.communicate()[0].strip()
        if p_which.returncode == 0:
            # check if it is only a symlink to another backend
            real_backend = os.path.basename(os.path.realpath(backend_path))
            if backend != real_backend and real_backend in backends: 
                if strict:
                    print "WARNING: %s is a symlink to %s" % (backend,
                                                              real_backend)
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

def getRealMacDevice(optionDevice):
    """drutil takes numbers as drives.

    We ask drutil what device name corresponds to that drive
    in order so we can use it as a drive for libdiscid
    """
    p = Popen(["drutil", "status", "-drive", optionDevice], stdout=PIPE)
    try:
	given = p.communicate()[0].splitlines()[3].split("Name:")[1].strip()
    except IndexError:
        printError("could not find real device")
        printError2("maybe there is no disc in the drive?")
	sys.exit(-1)
    # libdiscid needs the "raw" version
    return given.replace("/disk", "/rdisk")

def askForOffset(discTrackCount, releaseTrackCount):
    limit = releaseTrackCount - discTrackCount
    while True:
        print
        print "How many tracks are on the previous (actual) discs altogether?"
        try:
            choice = raw_input("[0-%d] " % limit)
        except KeyboardInterrupt:
            print
            print "exiting.."
            sys.exit(1)
        try:
            num = int(choice)
        except ValueError:
            printError("Not a number")
        else:
            if num in range(0, limit + 1):
                return num

def printError(*args):
    stringArgs = tuple(map(str, args))
    msg = " ".join(("ERROR:",) + stringArgs)
    sys.stderr.write(msg + "\n")

def printError2(*args):
    stringArgs = tuple(map(str, args))
    msg = " ".join(("      ",) + stringArgs)
    sys.stderr.write(msg + "\n")

def backendError(backend, e):
    printError("Couldn't gather ISRCs with %s: %i - %s"
            % (backend, e.errno, e.strerror))
    sys.exit(1)

class DemandQuery():
    """A Query object that opens an actual query on first use

    We can setup the query beforehand and only ask for the password
    and username when we actually need them.
    """

    def __init__(self, username, agent):
        self._query = None
        self.auth = False
        self.username = username
        self.agent = agent

    def create(self, auth=False):
        """Creates the query object and possibly asks for username/password
        """
        if auth:
            print
            if self.username is None:
                print "Please input your MusicBrainz username:",
                self.username = raw_input()
            print "Please input your MusicBrainz password: ",
            password = getpass.getpass("")
            print
            if StrictVersion(musicbrainz2_version) >= "0.7.4":
                # There is a warning printed above, when < 0.7.4
                service = WebService(username=self.username, password=password,
                        userAgent=self.agent)
            else:
                # standard userAgent: python-musicbrainz/__version__
                service = WebService(username=self.username, password=password)
            self.auth = True
        else:
            if StrictVersion(musicbrainz2_version) >= "0.7.4":
                service = WebService(userAgent=self.agent)
            else:
                service = WebService()

        # This clientId is currently only used for submitPUIDs and submitCDStub
        # which we both don't do directly.
        self._query = Query(service, clientId=self.agent)

    def getReleases(self, filter):
        if self._query is None: self.create()
        return self._query.getReleases(filter=filter)

    def getReleaseById(self, releaseId, include):
        if self._query is None: self.create()
        return self._query.getReleaseById(releaseId, include=include)

    def submitISRCs(self, tracks2isrcs):
        """This will create a new authenticated query if none exists already.
        """
        if not self.auth: self.create(auth=True)
        self._query.submitISRCs(tracks2isrcs)


class Disc(object):
    def __init__(self, device, submit=False):
        try:
            # calculate disc ID from disc
            if os.name == "nt" and not debug:
                # libdiscid will print debug device names on stdout
                # we want to suppress this
                devnull = open(os.devnull, 'w')
                oldStdoutFd = os.dup(sys.stdout.fileno())
                os.dup2(devnull.fileno(), 1) # > /dev/null
                self._disc = readDisc(deviceName=device)
                os.dup2(oldStdoutFd, 1)      # restore stdout
            else:
                # no such debug output on other platforms
                self._disc = readDisc(deviceName=device)
            self._release = None
            self._submit = submit
        except DiscError, e:
            printError("DiscID calculation failed:", str(e))
            sys.exit(1)

    @property
    def id(self):
        return self._disc.getId()

    @property
    def trackCount(self):
        return len(self._disc.getTracks())

    @property
    def submissionUrl(self):
        return getSubmissionUrl(self._disc)

    @property
    def release(self):
        """The corresponding MusicBrainz release

        This will ask the user to choose if the discID is ambiguous.
        """
        if self._release is None:
            self._release = self.getRelease(self._submit)
            # can still be None
        return self._release

    def getRelease(self, submit=False):
        """Find the corresponding MusicBrainz release

        This will ask the user to choose if the discID is ambiguous.
        """
        discId_filter = ReleaseFilter(discId=self.id)
        try:
            results = query.getReleases(filter=discId_filter)
        except ConnectionError, e:
            printError("Couldn't connect to the server:", str(e))
            sys.exit(1)
        except WebServiceError, e:
            printError("Couldn't fetch release:", str(e))
            sys.exit(1)
        if len(results) == 0:
            print "This Disc ID is not in the database."
            self._release = None
        elif len(results) > 1:
            print "This Disc ID is ambiguous:"
            for i in range(len(results)):
                release = results[i].release
                print str(i)+":", release.getArtist().getName(),
                print "-", release.getTitle(),
                print "(" + release.getTypes()[1].rpartition('#')[2] + ")"
                events = release.getReleaseEvents()
                for event in events:
                    country = (event.getCountry() or "").ljust(2)
                    date = (event.getDate() or "").ljust(10)
                    barcode = (event.getBarcode() or "").rjust(13)
                    catnum = event.getCatalogNumber() or ""
                    print "\t", country, "\t", date, "\t", barcode,
                    print "\t", catnum
            try:
                num =  raw_input("Which one do you want? [0-%d] " % i)
                self._release = results[int(num)].getRelease()
            except (ValueError, IndexError):
                printError("Invalid Choice")
                sys.exit(1)
            except KeyboardInterrupt:
                print
                print "exiting.."
                sys.exit(1)
        else:
            self._release = results[0].getRelease()

        if self._release and self._release.getId() is None:
            # a "release" that is only a stub has no musicbrainz id
            print
            print "There is only a stub in the database:"
            print self._release.getArtist().getName(),
            print "-", self._release.getTitle()
            print
            self._release = None        # don't use stub
            submit = True               # the id is verified by the stub

        if self._release is None:
            if submit:
                url = self.submissionUrl
                print "Would you like to open the browser to submit the disc?",
                if raw_input("[y/N] ") == "y":
                    try:
                        os.execlp(options.browser, options.browser, url)
                    except OSError, e:
                        printError("Couldn't open the url in %s: %s"
                                    % (options.browser, str(e)))
                        printError2("Please submit it via:", url)
                        sys.exit(1)
                else:
                    print "Please submit the Disc ID with this url:"
                    print url
                    sys.exit(1)
            else:
                print "recalculating to re-check.."
                self.getRelease(submit=True)

        return self._release

def getDisc(device, submit=False):
    """This creates a Disc object, which also calculates the id of the disc
    """
    disc = Disc(device, submit)
    print
    print 'DiscID:\t\t', disc.id
    print 'Tracks on disc:\t', disc.trackCount
    return disc


def gatherIsrcs(backend, device):
    """read the disc in the device with the backend and extract the ISRCs
    """
    backend_output = []
    devnull = open(os.devnull, "w")

    # icedax is a fork of the cdda2wav tool
    if backend in ["cdda2wav", "icedax"]:
        pattern = \
            'T:\s+([0-9]+)\sISRC:\s+([A-Z]{2})-?([A-Z0-9]{3})-?(\d{2})-?(\d{5})'
        try:
            p1 = Popen([backend, '-J', '-H', '-D', device], stderr=PIPE)
            p2 = Popen(['grep', 'ISRC'], stdin=p1.stderr, stdout=PIPE)
            isrcout = p2.stdout
        except OSError, e:
            backendError(backend, e)
        for line in isrcout:
            # there are \n and \r in different places
            if debug: print line,
            for text in line.splitlines():
                if text.startswith("T:"):
                    m = re.search(pattern, text)
                    if m == None:
                        print "can't find ISRC in:", text
                        continue
                    trackNumber = int(m.group(1))
                    isrc = m.group(2) + m.group(3) + m.group(4) + m.group(5)
                    backend_output.append((trackNumber, isrc))

    elif backend == "cd-info":
        pattern = \
            'TRACK\s+([0-9]+)\sISRC:\s+([A-Z]{2})-?([A-Z0-9]{3})-?(\d{2})-?(\d{5})'
        try:
            p = Popen([backend, '-T', '-A', '--no-device-info', '--no-cddb',
                '-C', device], stdout=PIPE)
            isrcout = p.stdout
        except OSError, e:
            backendError(backend, e)
        for line in isrcout:
            if debug: print line,
            if line.startswith("TRACK"):
                m = re.search(pattern, line)
                if m == None:
                    print "can't find ISRC in:", line
                    continue
                trackNumber = int(m.group(1))
                isrc = m.group(2) + m.group(3) + m.group(4) + m.group(5)
                backend_output.append((trackNumber, isrc))

    # media_info is a preview version of mediatools, both are for Windows
    elif backend in ["mediatools", "media_info"]:
        pattern = \
            'ISRC\s+([0-9]+)\s+([A-Z]{2})-?([A-Z0-9]{3})-?(\d{2})-?(\d{5})'
        if backend == "mediatools":
            args = [backend, "drive", device, "isrc"]
        else:
            args = [backend, device]
        try:
            p = Popen(args, stdout=PIPE)
            isrcout = p.stdout
        except OSError, e:
            backendError(backend, e)
        for line in isrcout:
            if debug: print line,
            if line.startswith("ISRC") and not line.startswith("ISRCS"):
                m = re.search(pattern, line)
                if m == None:
                    print "can't find ISRC in:", line
                    continue
                trackNumber = int(m.group(1))
                isrc = m.group(2) + m.group(3) + m.group(4) + m.group(5)
                backend_output.append((trackNumber, isrc))

    # cdrdao will create a temp file and we delete it afterwards
    # cdrdao is also available for windows
    elif backend == "cdrdao":
        pattern = '[A-Z]{2}[A-Z0-9]{3}\d{2}\d{5}'
        tmpname = "cdrdao-%s.toc" % datetime.now()
        tmpname = tmpname.replace(":", "-")     # : is invalid on windows
        tmpfile = os.path.join(tempfile.gettempdir(), tmpname)
        if debug: print "Saving toc in %s.." % tmpfile
        if os.name == "nt" and device != "D:":
            print "warning: cdrdao uses the default device"
            args = [backend, "read-toc", "--fast-toc", "-v", "0", tmpfile]
        else:
            args = [backend, "read-toc", "--fast-toc", "--device", device,
                "-v", "0", tmpfile]
        try:
            p = Popen(args ,stdout=devnull, stderr=devnull)
            if p.wait() != 0:
                printError("%s returned with %i" % (backend, p.returncode))
                sys.exit(1)
        except OSError, e:
            backendError(backend, e)
        else:
            with open(tmpfile, "r") as toc:
                trackNumber = None
                for line in toc:
                    if debug: print line,
                    words = line.split()
                    if len(words) > 0:
                        if words[0] == "//":
                            trackNumber = int(words[2])
                        elif words[0] == "ISRC" and trackNumber is not None:
                            isrc = "".join(words[1:]).strip('"- ')
                            m = re.match(pattern, isrc)
                            if m is None:
                                print "no valid ISRC:", isrc
                            elif isrc:
                                backend_output.append((trackNumber, isrc))
                                # safeguard against missing trackNumber lines
                                # or duplicated ISRC tags (like in CD-Text)
                                trackNumber = None
        finally:
            try:
                os.unlink(tmpfile)
            except:
                pass

    # this is the backend included in Mac OS X
    # it will take a lot of time because it scans the whole disc
    elif backend == "drutil":
        pattern = \
        'Track\s+([0-9]+)\sISRC:\s+([A-Z]{2})-?([A-Z0-9]{3})-?(\d{2})-?(\d{5})'
        try:
            p1 = Popen([backend, 'subchannel', '-drive', device], stdout=PIPE)
            p2 = Popen(['grep', 'ISRC'], stdin=p1.stdout, stdout=PIPE)
            isrcout = p2.stdout
        except OSError, e:
            backendError(backend, e)
        for line in isrcout:
            if debug: print line,
            if line.startswith("Track") and line.find("block") > 0:
                m = re.search(pattern, line)
                if m == None:
                    print "can't find ISRC in:", line
                    continue
                trackNumber = int(m.group(1))
                isrc = m.group(2) + m.group(3) + m.group(4) + m.group(5)
                backend_output.append((trackNumber, isrc))

    return backend_output


def cleanupIsrcs(isrcs):
    """Show information about duplicate ISRCs

    Our attached ISRCs should be correct -> helps to delete from other tracks
    """
    for isrc in isrcs:
        tracks = isrcs[isrc].getTracks()
        if len(tracks) > 1:
            print
            print "ISRC", isrc, "attached to:"
            for track in tracks:
                print "\t",
                artist = track.getArtist()
                string = ""
                if artist:
                    string += artist.getName() + " - "
                string += track.getTitle()
                print string,
                # tab alignment
                if len(string) >= 32:
                    print
                    print " " * 40,
                else:
                    if len(string) < 7:
                        print "\t",
                    if len(string) < 15:
                        print "\t",
                    if len(string) < 23:
                        print "\t",
                    if len(string) < 31:
                        print "\t",

                # append track# and evaluation, if available
                if isinstance(track, NumberedTrack):
                    print "\t track", track.getNumber(),
                if isinstance(track, OwnTrack):
                    print "   [OUR EVALUATION]"
                else:
                    print

            url = "http://musicbrainz.org/isrc/" + isrc
            if raw_input("Open ISRC in the browser? [Y/n] ") != "n":
                Popen([options.browser, url])
                raw_input("(press <return> when done with this ISRC) ")


# "main" + + + + + + + + + + + + + + + + + + + + + + + + + + + + +

print scriptVersion()
print

# - - - - "global" variables - - - -
# gather chosen options
options = gatherOptions(sys.argv)
# we set the device after we know which backend we will use
backend = options.backend
debug = options.debug
# the actual query will be created when it is used the first time
query = DemandQuery(options.user, agentName)
disc = None

print "using python-musicbrainz2", musicbrainz2_version
if StrictVersion(musicbrainz2_version) < "0.7.0":
    printError("Your version of python-musicbrainz2 is outdated")
    printError2("You WILL NOT be able to even check ISRCs")
    printError2("Please use AT LEAST python-musicbrainz2 0.7.0")
    sys.exit(-1) # the script can't do anything useful
if StrictVersion(musicbrainz2_version) < "0.7.3":
    printError("Cannot use AUTH DIGEST")
    printError2("You WILL NOT be able to submit ISRCs -> check-only")
    printError2("Please use python-musicbrainz2 0.7.3 or higher")
    # do not exit, check-only is what happens most of the times anyways
# We print two warnings for clients between 0.7.0 and 0.7.3,
# because 0.7.4 is important. (-> no elif)
if StrictVersion(musicbrainz2_version) < "0.7.4":
    print "WARNING: Cannot set userAgent"
    print "         You WILL have random connection problems due to throttling"
    print "         Please use python-musicbrainz2 0.7.4 or higher"
    print

# There are some old/buggy "which" versions on Windows
# unxutils has a broken 2.4; which >= 2.16 should be fine
devnull = open(os.devnull, "w")
try:
    # "which" should at least find itself (even without searching which.exe)
    returnCode = call(["which", "which"], stdout=devnull, stderr=devnull)
except OSError:
    saneWhich = False        # no which at all
else:
    if (returnCode == 0):
        saneWhich = True
    else:
        saneWhich = False
        print 'warning: your version of the tool "which" is buggy/outdated'
        if os.name == "nt":
            print '         unxutils is old/broken, GnuWin32 is good.'


# search for backend
if backend is None:
    for prog in backends:
        if hasBackend(prog):
            backend = prog
            break

# (still) no backend available?
if backend is None:
    verbose_backends = []
    for program in backends:
        if program in packages:
            verbose_backends.append(program + " (" + packages[program] + ")")
        else:
            verbose_backends.append(program)
    printError("Cannot find a backend to extract the ISRCS!")
    printError2("Isrcsubmit can work with one of the following:")
    printError2("  " + ", ".join(verbose_backends))
    sys.exit(-1)
else:
    print "using", getProgVersion(backend)

if backend == "drutil":
    # drutil (Mac OS X) expects 1,2,..
    # convert linux default
    if options.device == "/dev/cdrom":
        options.device = "1"
    # libdiscid needs to know what disk that corresponds to
    # drutil will tell us
    device = getRealMacDevice(options.device)
    if debug:
        print "CD drive #%s corresponds to %s internally" % (
                                                options.device, device)
else:
    # for linux the real device is the same as given in the options
    device = options.device

disc = getDisc(device, submit=False)
releaseId = disc.release.getId()        # implicitly fetches release
include = ReleaseIncludes(artist=True, tracks=True, isrcs=True, discs=True)
try:
    release = query.getReleaseById(releaseId, include=include)
except ConnectionError, e:
    printError("Couldn't connect to the server:", str(e))
    sys.exit(1)
except WebServiceError, e:
    printError("Couldn't fetch release:", str(e))
    sys.exit(1)

tracks = release.getTracks()
releaseTrackCount = len(tracks)
discs = release.getDiscs()
# discCount is actually the count of DiscIDs
# there can be multiple DiscIDs for a single disc
discIdCount = len(discs)
print 'Artist:\t\t', release.getArtist().getName()
print 'Release:\t', release.getTitle()
if releaseTrackCount != disc.trackCount:
    # a track count mismatch probably due to
    # multiple discs in the release
    print "Tracks in release:", releaseTrackCount
    # Handling of multiple discs in the release:
    # We can only get the overall release from MB
    # and not the Medium itself.
    # This changed with NGS. Before there was one MB release per disc.
    print
    print "WARNING: Multi-disc-release given by web service."
    print "See '" + scriptname, "-h' for help"

    if discIdCount == 1:
        # This is actually a weird case
        # Having only 1 disc, but not matching trackCounts
        # Possibly some data/video track.
        # but also possible that there is a bonus DVD (no disc ID possible)
        print "Track count mismatch!"
        print "There are", disc.trackCount, "tracks on the disc,"
        print "but", releaseTrackCount,"tracks"
        print "given for just one DiscID."
        print
        discIdNumber = 1
    else:
        print "Discs (or disc IDs) in release: ", discIdCount
        for i in range(discIdCount):
            print "\t", discs[i].getId(),
            if discs[i].getId() == disc.id:
                discIdNumber = i + 1
                print "[THIS DISC]"
            else:
                print
    print "There might be multiple disc IDs per disc or none,"
    print "so the number of actual discs could be lower or even higher."
    print
    print "This is disc (ID)", discIdNumber, "of", discIdCount

    if discIdNumber == 1 and discIdCount > 1:
        # the first disc never needs an offset
        # unless we have a track count mismatch and only one disc id given
        trackOffset = 0
        print "Guessing track offset as", trackOffset
    elif discIdCount == 1 and disc.trackCount < releaseTrackCount:
        # bonus DVD (without disc ID) given in MB?
        # better handling in version 2 api
        trackOffset = 0
        print "This release probably has a bonus DVD without a discID."
        print "Guessing track offset as", trackOffset
    else:
        # cannot guess fully automatically
        if discIdCount > 1 and discIdNumber == discIdCount:
            # It is easy to guess the offset when this is the last disc,
            # because we have no unknown track counts after this.
            trackOffset = releaseTrackCount - disc.trackCount
            print "It looks like the last disc of the release."
            print "This might be wrong when a bonus DVD is part of the release."
            print "Our offset guess would be:", trackOffset
            print
        else:
            # For "middle" discs we have unknown track numbers
            # before and after the current disc.
            # The same when we have only one disc ID but a track mismatch
            # -> the user has to tell us an offset to use
            print "Cannot guess the track offset."

        # There can also be multiple discIds for one disc of the release
        # so we give a MB-link to help which IDs
        # belong to which disc of the release.
        # We can't provide that ourselves without making
        # many requests to MB or using the new web-api 2.
        url = releaseId + "/discids" # The "releaseId" is an url itself
        print "This url would provide some info about the disc IDs:"
        print url
        print "Would you like to open it in the browser?",
        if raw_input("[y/N] ") == "y":
            try:
                Popen([options.browser, url])
            except OSError, e:
                printError("Couldn't open the url with %s: %s"
                            % (options.browser, str(e)))

        trackOffset = askForOffset(disc.trackCount, releaseTrackCount)
else:
    # the track count matches
    trackOffset = 0


print
# Extract ISRCs
backend_output = gatherIsrcs(backend, options.device) # (track, isrc)

# prepare to add the ISRC we found to the corresponding track
# and check for local duplicates now and server duplicates later
isrcs = dict()          # isrcs found on disc
tracks2isrcs = dict()   # isrcs to be submitted
errors = 0
for (trackNumber, isrc) in backend_output:
    if isrc not in isrcs:
        isrcs[isrc] = Isrc(isrc)
        # check if we found this ISRC for multiple tracks
        with_isrc = filter(lambda item: item[1] == isrc, backend_output)
        if len(with_isrc) > 1:
            listOfTracks = map(str, map(lambda l: l[0], with_isrc))
            printError(backend + " gave the same ISRC for multiple tracks!")
            printError2("ISRC:", isrc, "\ttracks:", ", ".join(listOfTracks))
            errors += 1
    try:
        track = tracks[trackNumber + trackOffset - 1]
        ownTrack = OwnTrack(track, trackNumber)
        isrcs[isrc].addTrack(ownTrack)
        # check if the ISRC was already added to the track
        if isrc not in track.getISRCs():
            tracks2isrcs[track.getId()] = isrc
            print "found new ISRC for track",
            print str(trackNumber) + ":", isrc
        else:
            print isrc, "is already attached to track", trackNumber
    except IndexError, e:
        printError("ISRC", isrc, "found for unknown track", trackNumber)
        errors += 1
for isrc in isrcs:
    for track in isrcs[isrc].getTracks():
        trackNumber = track.getNumber()

print
# try to submit the ISRCs
update_intention = True
if len(tracks2isrcs) == 0:
    print "No new ISRCs could be found."
else:
    if errors > 0:
        printError(errors, "problems detected")
    if raw_input("Do you want to submit? [y/N] ") == "y":
        try:
            query.submitISRCs(tracks2isrcs)
            print "Successfully submitted", len(tracks2isrcs), "ISRCs."
        except RequestError, e:
            printError("Invalid request:", str(e))
        except AuthenticationError, e:
            printError("Invalid credentials:", str(e))
        except WebServiceError, e:
            printError("Couldn't send ISRCs:", str(e))
    else:
        update_intention = False
        print "Nothing was submitted to the server."

# check for overall duplicate ISRCs, including server provided
if update_intention:
    duplicates = 0
    # add already attached ISRCs
    for i in range(0, len(tracks)):
        track = tracks[i]
        if i in range(trackOffset, trackOffset + disc.trackCount):
            trackNumber = i - trackOffset + 1
            track = NumberedTrack(track, trackNumber)
        for isrc in track.getISRCs():
            # only check ISRCS we also found on our disc
            if isrc in isrcs:
                isrcs[isrc].addTrack(track)
    # check if we have multiple tracks for one ISRC
    for isrc in isrcs:
        if len(isrcs[isrc].getTracks()) > 1:
            duplicates += 1

    if duplicates > 0:
        print
        print "There were", duplicates, "ISRCs",
        print "that are attached to multiple tracks on this release."
        if raw_input("Do you want to help clean those up? [y/N] ") == "y":
            cleanupIsrcs(isrcs)


# vim:set shiftwidth=4 smarttab expandtab:
