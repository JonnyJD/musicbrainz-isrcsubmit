### Changes in 0.5.2 (2013-01-26)
 * [#43] fix: global name 'saneWhich' is not defined

### Changes in 0.5.1 (2012-12-23)
 * [#40] support and use unicode codepage on Windows (cp65001)

   Use isrcsubmit.bat for unicode output or set `chcp cp65001`
   before using isrcsubmit.py.
   Don't forget to change back later, that codepage is buggy!
   You can display your current codepage with `chcp`.
   This only works with the `Lucida Console` font set in `cmd`.
 * add CHANGELOG
 * [#41] fix: exception on browser error
 * [#33] fix: device debug output on Windows
 * [#30] fix: detect broken "which" tool

## Changes in 0.5 (2012-12-02)
 * [#24] Windows support with the mediatools backend
 * [#22] add libcdio backend (Linux)
 * [#15] add --browser parameter
 * [#28] make username an optional argument


### Changes in 0.4.4 (2012-11-30)
 * [#27] fix: only submit non-empty ISRCs (cdrdao)
 * [#26] fix: exception on wrong input at release selection
 * [#25] fix: last CD is mistaken for DVD (=last disc)

### Changes in 0.4.3 (2012-11-17)
 * [#23] fix: recognize stubs and ignore them

### Changes in 0.4.2 (2012-10-15)
 * [#19] only ask for password when necessary
 * [#14] verify discId when the id is new to MusicBrainz
 * [#18],[#17] fix: also recognize ISRCs in CD-TEXT (cdrdao)

### Changes in 0.4.1 (2012-04-24)
 * [#16] fix: handle releases with bonus DVDs correctly

## Changes in 0.4 (2012-03-06)
 * [#12] Mac support with the drutil backend

   The drutil backen is *very* slow.
   It will take minutes!
 * [#11] add cdrdao backend
 * [#10] add cdda2wav backend again
 * [#13] optional --backend parameter to choose a backend manually


### Changes in 0.3.1 (2012-02-22)
 * [#9] show information about all tracks on the release in duplicate-find

## Changes in 0.3 (2012-02-20)
 * [#3] prevent duplicate ISRCs; cleanup duplicate ISRCs on the server
 * [#5] show release events on release choice
 * [#2] add user agent
 * [#4] warn if python-musicbrainz2 is too old
 * [#1] Multidisc-release support (with offsets; due to NGS changes)

### Changes in 0.2.4 (2010-09-15)
 * Added debug switch (--debug)

### Changes in 0.2.3 (2009-11-26)
 * fix: catch more exceptions

### Changes in 0.2.1 (2009-10-03)
 * list release type for release choice

## Changes in 0.2 (2009-10-03)
 * handle missing dashes in ISRCs
 * give a choice if multiple releases match the discID
