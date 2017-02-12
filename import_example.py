#!/usr/bin/python

import isrcsubmit

if __name__ == "__main__":
    options = isrcsubmit.gather_options([])

    print("isrcsubmit %s" % isrcsubmit.__version__)
    print("backends: %s" % ", ".join(isrcsubmit.BACKENDS))
    device = "/dev/cdrom"
    #backend = isrcsubmit.find_backend()
    #print(isrcsubmit.get_prog_version(options.backend))
    disc = isrcsubmit.get_disc(device, options.backend)
    print(isrcsubmit.gather_isrcs(disc, options.backend, device))
