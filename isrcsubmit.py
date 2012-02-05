#!/usr/bin/env python2
# Copyright 2010-2012 Johannes Dewender
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

import getpass
import sys
import os
import re
from subprocess import Popen, PIPE
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

isrcsubmit uses the MB webservice version 1.
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

isrcsubmit only knows how many tracks the current disc has and the total number of tracks on the release given by the webservice. So the offset must be between 0 and 53 (= 72 - 19), which is the range isrcsubmit lets you choose from.

Please report bugs on https://github.com/JonnyJD/musicbrainz-isrcsubmit"""

def askForOffset():
    print "Cannot guess the track offset."
    print "How many tracks are on the previous discs altogether?"
    num = raw_input("[0-%d] " % (releaseTrackCount - discTrackCount))
    trackOffset = int(num)

print "isrcsubmit using icedax for Linux, version", isrcsubmitVersion

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
    print "DiscID calculation failed:", str(e)
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
service = WebService(username=username, password=password)
q = Query(service)

# searching for release
filter = ReleaseFilter(discId=discId)
try:
    results = q.getReleases(filter=filter)
except ConnectionError, e:
    print "Couldn't connect to the Server:", str(e)
    sys.exit(1)
except WebServiceError, e:
    print "Couldn't fetch release:", str(e)
    sys.exit(1)
if len(results) == 0:
    print "This Disc ID is not in the Database."
    url = getSubmissionUrl(disc)
    print "Would you like to open Firefox to submit it? [y/N] ",
    if sys.stdin.read(1) == "y":
        try:
            os.execlp('firefox', 'firefox', url)
        except OSError, e:
            print "Couldn't open the url in firefox:", str(e)
            print "Please submit it via:", url
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
    num =  raw_input("Which one do you want? [0-%d] " % i)
    result = results[int(num)]
else:
    result = results[0]

# getting release details
include = ReleaseIncludes(artist=True, tracks=True, isrcs=True, discs=True)
try:
    release = q.getReleaseById(result.getRelease().getId(), include=include)
except ConnectionError, e:
    print "Couldn't connect to the Server:", str(e)
    sys.exit(1)
except WebServiceError, e:
    print "Couldn't fetch release:", str(e)
    sys.exit(1)

tracks = release.getTracks()
releaseTrackCount = len(tracks)
discs = release.getDiscs()
discCount = len(discs)
print 'Artist:\t\t', release.getArtist().getName()
print 'Release:\t', release.getTitle()
if releaseTrackCount != discTrackCount:
    print "Tracks in Release:", releaseTrackCount

if discCount > 1:
    # Handling of multiple discs in the release:
    # We can only get the overall Release from MB
    # and not the Medium itself.
    # This changed with NGS. Before there was one release per disc.
    print
    print "WARNING: Multi-disc-release given by webservice."
    print "See '" + scriptname, "-h' for help"
    print "Discs in Release: ", discCount
    for i in range(discCount):
        print "\t", discs[i].getId(),
        if discs[i].getId() == discId:
            discNumber = i + 1
            print "[THIS DISC]"
        else:
            print
    print
    print "This is disc", discNumber, "of", discCount
    if discNumber == 1:
        # the first disc never needs an offset
        trackOffset = 0
        print "Guessing track offset as", trackOffset
    elif discNumber == discCount:
        # It is easy to guess the offset when this is the last disc,
        # because we have no unknown track counts after this.
        trackOffset = releaseTrackCount - discTrackCount
        print "Guessing track offset as", trackOffset
    else:
        # for "middle" discs we have unknown track numbers
        # before and after -> the user has to tell us an offset to use
        trackOffset = askForOffset()
else:
    trackOffset = 0

# getting the ISRCs with icedax
print
try:
    p1 = Popen(['icedax', '-J', '-H', '-D', device], stderr=PIPE)
    p2 = Popen(['grep', 'ISRC'], stdin=p1.stderr, stdout=PIPE)
    isrcout = p2.communicate()[0]
except:
    print "Couldn't gather ISRCs with icedax and grep!"
    sys.exit(1)

tracks2isrcs =dict()
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
            try:
                track = tracks[trackNumber + trackOffset - 1]
                if isrc not in (track.getISRCs()):
                    tracks2isrcs[track.getId()] = isrc
                    print "found new ISRC for track",
                    print str(trackNumber) + ":", isrc
                else:
                    print isrc, "is already attached to track", trackNumber
            except IndexError, e:
                print "ISRC", isrc, "fuer unbekannten Track ",
                print trackNumber, "gefunden!"

print
if len(tracks2isrcs) == 0:
    print "No new ISRCs could be found."
else:
    if raw_input("Is this correct? [y/N] ") == "y":
        try:
            q.submitISRCs(tracks2isrcs)
            print "Successfully submitted", len(tracks2isrcs), "ISRCs."
        except RequestError, e:
            print "Invalid Request:", str(e)
        except AuthenticationError, e:
            print "Invalid Credentials:", str(e)
        except WebServiceError, e:
            print "Couldn't send ISRCs:", str(e)
    else:
        print "Nothing was submitted to the server."

# vim:set shiftwidth=4 smarttab expandtab:
