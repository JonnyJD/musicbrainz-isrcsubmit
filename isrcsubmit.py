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
and the script is als available on
http://kraehen.org/isrcsubmit.py
"""

isrcsubmitVersion = "0.2.5"
agentName="isrcsubmit-jonnyjd-" + isrcsubmitVersion

import getpass
import sys
import os
import re
from subprocess import Popen, PIPE
from distutils.version import StrictVersion
from musicbrainz2 import __version__ as musicbrainz2_version
from musicbrainz2.disc import readDisc, DiscError, getSubmissionUrl
from musicbrainz2.webservice import WebService, Query
from musicbrainz2.webservice import ReleaseFilter, ReleaseIncludes
from musicbrainz2.webservice import RequestError, AuthenticationError
from musicbrainz2.webservice import ConnectionError, WebServiceError

scriptname = os.path.basename(sys.argv[0])

def print_usage():
    print
    print "usage:", scriptname, "[-d] username [device]"
    print
    print " -d, --debug\tenable debug messages"
    print " -h, --help\tprint usage and multi-disc information"
    print

multidisc_info = \
"""A note on Multi-disc-releases:

Isrcsubmit uses the MB web service version 1.
This api is not tailored for MB NGS and expects to have one release per disc. So it does not know which tracks are on a specific disc and lists all tracks in the overall release.
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

Please report bugs on https://github.com/JonnyJD/musicbrainz-isrcsubmit"""

def askForOffset():
    print
    print "How many tracks are on the previous (actual) discs altogether?"
    num = raw_input("[0-%d] " % (releaseTrackCount - discTrackCount))
    return int(num)

def printError(*args):
    stringArgs = tuple(map(str, args))
    msg = " ".join(("ERROR:",) + stringArgs)
    sys.stderr.write(msg + "\n")

print "isrcsubmit", isrcsubmitVersion, "by JonnyJD"
print "using python-musicbrainz2", musicbrainz2_version, "and icedax"

# print warnings/errors if python-musicbrainz2 is outdated
if StrictVersion(musicbrainz2_version) < "0.7.0":
    printError("Your version of python-musicbrainz2 is outdated")
    printError("You WILL NOT be able to even check ISRCs")
    printError("Please use AT LEAST python-musicbrainz2 0.7.0")
    sys.exit(-1) # the script can't do anything useful
if StrictVersion(musicbrainz2_version) < "0.7.3":
    printError("Cannot use AUTH DIGEST")
    printError("You WILL NOT be able to submit ISRCs -> check-only")
    printError("Please use python-musicbrainz2 0.7.3 or higher")
    # do not exit, check-only is what happens most of the times anyways
# We print two warnings for clients between 0.7.0 and 0.7.3,
# because 0.7.4 is important. (-> no elif)
if StrictVersion(musicbrainz2_version) < "0.7.4":
    print "WARNING: Cannot set userAgent"
    print "WARNING: You WILL have random connection problems due to throttling"
    print "WARNING: Please use python-musicbrainz2 0.7.4 or higher"
    print

# gather arguments
if len(sys.argv) < 2 or len(sys.argv) > 4:
    print_usage()
    sys.exit(1)
else:
    # defaults
    debug = False
    username = None
    device = "/dev/cdrom"
    for i in range(1, len(sys.argv)):
        arg = sys.argv[i]
        if arg == "-d" or arg == "--debug":
            debug = True
        elif arg == "-h" or arg == "--help":
            print_usage()
            print
            print multidisc_info
            sys.exit(0)
        elif username == None:
            username = arg
        else:
            device = arg

try:
    # get disc ID
    disc = readDisc(deviceName=device)
except DiscError, e:
    printError("DiscID calculation failed:", str(e))
    sys.exit(1)

discId = disc.getId()
discTrackCount = len(disc.getTracks())

print 'DiscID:\t\t', discId
print 'Tracks on Disc:\t', discTrackCount

print
print "Please input your Musicbrainz password"
password = getpass.getpass('Password: ')
print

# connect to the server
if StrictVersion(musicbrainz2_version) >= "0.7.4":
    # There is a warning printed above, when < 0.7.4
    service = WebService(username=username, password=password,
            userAgent=agentName)
else:
    # standard userAgent: python-musicbrainz/__version__
    service = WebService(username=username, password=password)

# This clientId is currently only used for submitPUIDs and submitCDStub
# which we both don't do directly.
q = Query(service, clientId=agentName)

# searching for release
filter = ReleaseFilter(discId=discId)
try:
    results = q.getReleases(filter=filter)
except ConnectionError, e:
    printError("Couldn't connect to the Server:", str(e))
    sys.exit(1)
except WebServiceError, e:
    printError("Couldn't fetch release:", str(e))
    sys.exit(1)
if len(results) == 0:
    print "This Disc ID is not in the Database."
    url = getSubmissionUrl(disc)
    print "Would you like to open Firefox to submit it?",
    if raw_input("[y/N] ") == "y":
        try:
            os.execlp('firefox', 'firefox', url)
        except OSError, e:
            printError("Couldn't open the url in firefox:", str(e))
            printError("Please submit it via:", url)
            sys.exit(1)
    else:
        print "Please submit the Disc ID it with this url:"
        print url
        sys.exit(1)

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
            print "\t", country, "\t", date, "\t", barcode
    num =  raw_input("Which one do you want? [0-%d] " % i)
    result = results[int(num)]
else:
    result = results[0]

# getting release details
releaseId = result.getRelease().getId()
include = ReleaseIncludes(artist=True, tracks=True, isrcs=True, discs=True)
try:
    release = q.getReleaseById(releaseId, include=include)
except ConnectionError, e:
    printError("Couldn't connect to the Server:", str(e))
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
if releaseTrackCount != discTrackCount:
    # a track count mismatch due to:
    # a) multiple discs in the release
    # b) multiple DiscIDs for a single disc
    # c) a)+b)
    # d) unknown (see CRITICAL below)
    print "Tracks in Release:", releaseTrackCount
    if discIdCount > 1:
        # Handling of multiple discs in the release:
        # We can only get the overall release from MB
        # and not the Medium itself.
        # This changed with NGS. Before there was one MB release per disc.
        print
        print "WARNING: Multi-disc-release given by web service."
        print "See '" + scriptname, "-h' for help"
        print "Discs (or disc IDs) in Release: ", discIdCount
        for i in range(discIdCount):
            print "\t", discs[i].getId(),
            if discs[i].getId() == discId:
                discIdNumber = i + 1
                print "[THIS DISC]"
            else:
                print
        print "There might be multiple disc IDs per disc"
        print "so the number of actual discs could be lower."
        print
        print "This is disc (ID)", discIdNumber, "of", discIdCount
        if discIdNumber == 1:
            # the first disc never needs an offset
            trackOffset = 0
            print "Guessing track offset as", trackOffset
        elif discIdNumber == discIdCount:
            # It is easy to guess the offset when this is the last disc,
            # because we have no unknown track counts after this.
            trackOffset = releaseTrackCount - discTrackCount
            print "Guessing track offset as", trackOffset
        else:
            # For "middle" discs we have unknown track numbers
            # before and after the current disc.
            # -> the user has to tell us an offset to use
            print "Cannot guess the track offset."

            # There can also be multiple discIds for one disc of the release
            # so we give a MB-link to help which IDs
            # belong to which disc of the release.
            # We can't provide that ourselfes without making
            # many requests to MB or using the new web-api 2.
            url = releaseId + "/discids" # The "releaseId" is an url itself
            print "This url would provide some info about the disc IDs:"
            print url
            print "Would you like to open it in Firefox?",
            if raw_input("[y/N] ") == "y":
                try:
                    os.spawnlp(os.P_NOWAIT, 'firefox', 'firefox', url)
                except OSError, e:
                    printError("Couldn't open the url in firefox:", str(e))

            trackOffset = askForOffset()
    else:
        # This is actually a weird case
        # Having only 1 disc, but not matching trackCounts
        # Possibly some data/video track,
        # but these should be suppressed on both ends the same
        print "CRITICAL: track count mismatch!"
        print "CRITICAL: There are", discTrackCount, "tracks on the disc,"
        print "CRITICAL: but", releaseTrackCount,
        print "tracks on a SINGLE-disc-release."
        print "CRITICAL: This is not supposed to happen."
        sys.exit(-1)
else:
    # the track count matches
    trackOffset = 0

# getting the ISRCs with icedax
print
try:
    p1 = Popen(['icedax', '-J', '-H', '-D', device], stderr=PIPE)
    p2 = Popen(['grep', 'ISRC'], stdin=p1.stderr, stdout=PIPE)
    isrcout = p2.communicate()[0]
except:
    printError("Couldn't gather ISRCs with icedax and grep!")
    sys.exit(1)

tracks2isrcs = dict()
isrcs2tracks = dict()
pattern = 'T:\s+([0-9]+)\sISRC:\s+([A-Z]{2})-?([A-Z0-9]{3})-?(\d{2})-?(\d{5})'
for line in isrcout.splitlines():
    if debug: print line
    for text in line.splitlines():
        if text.startswith("T:"):
            m = re.search(pattern, text)
            if m == None:
                print "can't find ISRC in:", text
                continue
            trackNumber = int(m.group(1))
            isrc = m.group(2) + m.group(3) + m.group(4) + m.group(5)
            # prepare to add the ISRC we found to the corresponding track
            try:
                track = tracks[trackNumber + trackOffset - 1]
                # check if we found this ISRC for another track already
                if isrc in isrcs2tracks:
                    isrcs2tracks[isrc].add(trackNumber)
                    listOfTracks = ", ".join(map(str,isrcs2tracks[isrc]))
                    printError("Icefox gave the same ISRC for two tracks!")
                    printError("ISRC:", isrc, "\ttracks:", listOfTracks)
                else:
                    isrcs2tracks[isrc] = set([trackNumber])
                # check if the ISRC was already added to the track
                if isrc not in (track.getISRCs()):
                    tracks2isrcs[track.getId()] = isrc
                    print "found new ISRC for track",
                    print str(trackNumber) + ":", isrc
                else:
                    print isrc, "is already attached to track", trackNumber
            except IndexError, e:
                printError("ISRC", isrc, "found for unknown track", trackNumber)

print
if len(tracks2isrcs) == 0:
    print "No new ISRCs could be found."
else:
    if raw_input("Is this correct? [y/N] ") == "y":
        try:
            q.submitISRCs(tracks2isrcs)
            print "Successfully submitted", len(tracks2isrcs), "ISRCs."
        except RequestError, e:
            printError("Invalid Request:", str(e))
        except AuthenticationError, e:
            printError("Invalid Credentials:", str(e))
        except WebServiceError, e:
            printError("Couldn't send ISRCs:", str(e))
    else:
        print "Nothing was submitted to the server."

# vim:set shiftwidth=4 smarttab expandtab:
