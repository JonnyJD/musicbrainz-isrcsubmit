version := 3.0.0-dev
#version := 3.0.0

build:
	./setup.py build

check:
	./setup.py test

install:
	./setup.py install

upload:
	./setup.py sdist
	twine3 upload -s dist/isrcsubmit-$(version).tar.gz

version:
	sed -i -e 's/\(Isrcsubmit\s\)[0-9.]\+[0-9a-z.-]*/\1$(version)/' README.rst
	sed -i -e 's/\(__version__\s=\s"\)[0-9.]\+[0-9a-z.-]*/\1$(version)/' \
		isrcsubmit.py
	sed -i -e 's/\(version="\)[0-9.]\+[0-9a-z.-]*/\1$(version)/' \
		setup.py
	sed -i -e 's/\(version\s:=\s\)[0-9.]\+[0-9a-z.-]*/\1$(version)/' \
		pkg/Makefile

clean:
	rm -f *.pyc

.PHONY: build install version
