#version := 2.0.0-dev
version := 2.0.0-beta.5

build:
	./setup.py build

install:
	./setup.py install

version:
	sed -i -e 's/\(Isrcsubmit\s\)[0-9.]\+[0-9a-z.-]*/\1$(version)/' README.rst
	sed -i -e 's/\(__version__\s=\s"\)[0-9.]\+[0-9a-z.-]*/\1$(version)/' \
		isrcsubmit.py

.PHONY: build install version
