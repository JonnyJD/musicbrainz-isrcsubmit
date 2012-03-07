#!/bin/sh

for python in {python2,python2.7,python2.6,python2.5}; do
	which $python 2>&1 > /dev/null
	if [ $? == 0 ]; then
		exec $python isrcsubmit.py $@
	fi
done
