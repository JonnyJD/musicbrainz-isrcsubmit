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

# This module contains shared functionality used by both
# the CD based tool isrcsubmit
# and the audio file tool isrcDigitalSubmit.
import logging
import os
import sys
import codecs
import webbrowser
import getpass
from subprocess import Popen, PIPE, call

import musicbrainzngs
from musicbrainzngs import AuthenticationError, WebServiceError

DEFAULT_SERVER = "musicbrainz.org"
BROWSERS = ["xdg-open", "x-www-browser",
            "firefox", "chromium", "chrome", "opera"]
# The webbrowser module is used when nothing is found in this list.
# This especially happens on Windows and Mac OS X (browser mostly not in PATH)

options = None

try:
    import keyring
except ImportError:
    keyring = None

# make code run on Python 2 and 3
try:
    user_input = raw_input
except NameError:
    user_input = input

try:
    unicode_string = unicode
except NameError:
    unicode_string = str

logger = logging.getLogger("isrcsubmit")

def cp65001(name):
    """This might be buggy, but better than just a LookupError
    """
    if name.lower() == "cp65001":
        return codecs.lookup("utf-8")


codecs.register(cp65001)

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


def has_program(program, choices, strict=False):
    """When the backend is only a symlink to another backend,
       we will return False, unless we strictly want to use this backend.
    """
    if not hasattr(has_program, "sane_which"):
        has_program.sane_which = test_which()
    with open(os.devnull, "w") as devnull:
        if has_program.sane_which:
            p_which = Popen(["which", program], stdout=PIPE, stderr=devnull)
            program_path = p_which.communicate()[0].strip()
            if p_which.returncode == 0:
                # check if it is only a symlink to another backend
                real_program = os.path.basename(os.path.realpath(program_path))
                if program != real_program and (
                        real_program in choices):
                    if strict:
                        print("WARNING: %s is a symlink to %s"
                              % (program, real_program))
                        return True
                    else:
                        return False # use real program (target) instead
                return True
            else:
                return False
        elif program in choices:
            try:
                # we just try to start these non-interactive console apps
                call([program], stdout=devnull, stderr=devnull)
            except OSError:
                return False
            else:
                return True
        else:
            return False


class WebService2():
    """A web service wrapper that asks for a password when first needed.

    This uses musicbrainzngs as a wrapper itself.
    """

    def __init__(self, username=None):
        self.auth = False
        self.keyring_failed = False
        self.username = username
        self.server = options.server
        self.keyring = options.keyring
        musicbrainzngs.set_hostname(options.server)

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
            password = None
            if keyring is not None and self.keyring and not self.keyring_failed:
                password = keyring.get_password(self.server, self.username)
            if password is None:
                password = getpass.getpass(
                                    "Please input your MusicBrainz password: ")
            print("")
            musicbrainzngs.auth(self.username, password)
            self.auth = True
            self.keyring_failed = False
            if keyring is not None and self.keyring:
                keyring.set_password(self.server, self.username, password)

    def get_release_by_id(self, release_id, includes=[]):
        try:
            return musicbrainzngs.get_release_by_id(release_id,
                                                    includes=includes)
        except WebServiceError as err:
            print_error("Couldn't fetch release: %s" % err)
            sys.exit(1)

    def get_recordings_by_isrc(self, isrc, includes=[]):
        try:
           response = musicbrainzngs.get_recordings_by_isrc(isrc, includes)
        except WebServiceError as err:
           print_error("Couldn't fetch recordings for isrc %s: %s" % (isrc, err))
           sys.exit(1)
        return response.get('isrc')['recording-list']

    def submit_isrcs(self, tracks2isrcs):
        logger.info("tracks2isrcs: %s", tracks2isrcs)
        while True:
            try:
                self.authenticate()
                musicbrainzngs.submit_isrcs(tracks2isrcs)
            except AuthenticationError as err:
                print_error("Invalid credentials: %s" % err)
                self.auth = False
                self.keyring_failed = True
                self.username = None
                continue
            except WebServiceError as err:
                print_error("Couldn't send ISRCs: %s" % err)
                sys.exit(1)
            else:
                print("Successfully submitted %d ISRCS." % len(tracks2isrcs))
                break



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
    label_list = release.get("label-info-list") or []
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
    logger.error("\n       ".join(string_args))


def setDefaultOptions(config, options):
    # If an option is set in the config and not overriden on the command line,
    # assign them to options.
    if options.keyring is None and config.has_option("general", "keyring"):
        options.keyring = config.getboolean("general", "keyring")
    if options.browser is None and config.has_option("general", "browser"):
        options.browser = config.get("general", "browser")
    if options.server is None and config.has_option("musicbrainz", "server"):
        options.server = config.get("musicbrainz", "server")
    if options.user is None and config.has_option("musicbrainz", "user"):
        options.user = config.get("musicbrainz", "user")
    options.sane_which = test_which()
    if options.browser is None:
        options.browser = find_browser()
    if options.server is None:
        options.server = DEFAULT_SERVER
    if options.keyring is None:
        options.keyring = True


def get_config_home(tool="isrcsubmit"):
    """Returns the base directory for isrcsubmit's configuration files."""

    if os.name == "nt":
        default_location = os.environ.get("APPDATA")
    else:
        default_location = os.path.expanduser("~/.config")

    xdg_config_home = os.environ.get("XDG_CONFIG_HOME", default_location)
    return os.path.join(xdg_config_home, tool)


def config_path(tool="isrcsubmit"):
    """Returns isrsubmit's config file location."""
    return os.path.join(get_config_home(tool), "config")


def find_browser():
    """search for an available browser
    """
    for browser in BROWSERS:
        if has_program(browser, BROWSERS):
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
                error = ["Couldn't open the url in %s: %s"
                         % (options.browser, str(err))]
                if submit:
                    error.append("Please submit via: %s" % url)
                print_error(*error)
                sys.exit(1)
        else:
            try:
                if options.debug:
                    Popen([options.browser, url])
                else:
                    with open(os.devnull, "w") as devnull:
                        Popen([options.browser, url], stdout=devnull)
            except OSError as err:
                error = ["Couldn't open the url in %s: %s"
                            % (options.browser, str(err))]
                if submit:
                    error.append("Please submit via: %s" % url)
                print_error(*error)
    else:
        try:
            if options.debug:
                webbrowser.open(url)
            else:
                # this supresses stdout
                webbrowser.get().open(url)
        except webbrowser.Error as err:
            error = ["Couldn't open the url: %s" % str(err)]
            if submit:
                error.append("Please submit via: %s" % url)
            print_error(*error)
        if exit:
            sys.exit(1)
