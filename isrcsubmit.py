#!/usr/bin/python
# Copyright 2010 Johannes Dewender ( brainz at JonnyJD.net ) 
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
#
#
# This is a tool to submit ISRCs from a disc to MusicBrainz.
# icedax is used to gather the ISRCs and python-musicbrainz2 to submit them.
# Version 0.2.4 from September 15th 2010
#
# usage: ./isrcsubmit.py [-d] username [device]

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

def print_usage():
    print
    print "usage:", os.path.basename(sys.argv[0]), "[-d] username [device]"
    print
    print " -d, --debug\tenable debug messages"
    print " -h, --help\tprint this usage info"
    print

print "isrcsubmit using icedax for Linux, version 0.2.4"
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
            sys.exit(0)
        elif username == None:
            username = arg
        else:
            device = arg

# get disc ID
try:
    disc = readDisc(deviceName=device)
except DiscError, e:
    print "DiscID calculation failed:", str(e)
    sys.exit(1)

print 'DiscID:\t\t', disc.id
password = getpass.getpass('Password: ')

# connect to the server
service = WebService(username=username, password=password)
q = Query(service)

filter = ReleaseFilter(discId=disc.id)
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

include = ReleaseIncludes(artist=True, tracks=True, isrcs=True)
try:
    release = q.getReleaseById(result.getRelease().getId(), include=include)
except ConnectionError, e:
    print "Couldn't connect to the Server:", str(e)
    sys.exit(1)
except WebServiceError, e:
    print "Couldn't fetch release:", str(e)
    sys.exit(1)
print 'Artist:\t\t', release.getArtist().getName()
print 'Release:\t', release.getTitle()
tracks = release.getTracks()

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
            isrc = m.group(2) + m.group(3) + m.group(4) + m.group(5)
            try:
                track = tracks[int(m.group(1))-1]
                if isrc not in (track.getISRCs()):
                    tracks2isrcs[track.getId()] = isrc
                    print "found new ISRC for track", m.group(1) + ":", isrc
                else:
                    print isrc, "is already attached to track", m.group(1)
            except IndexError, e:
                num = int(m.group(1))
                print "ISRC", isrc, "fuer unbekannten Track ", num, "gefunden!"

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
