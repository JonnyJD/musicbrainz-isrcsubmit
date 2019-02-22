#version := 2.1.0-dev
version := 2.1.0

build:
	./setup.py build

check:
	./setup.py test

install:
	./setup.py install

register:
	# make sure setuptools is used for pypi interactions
	python -c "import setuptools"
	./setup.py register

upload:
	# make sure setuptools is used for pypi interactions
	python -c "import setuptools"
	./setup.py sdist upload

version:
	sed -i -e 's/\(Isrcsubmit\s\)[0-9.]\+[0-9a-z.-]*/\1$(version)/' README.rst
	sed -i -e 's/\(__version__\s=\s"\)[0-9.]\+[0-9a-z.-]*/\1$(version)/' \
		isrcsubmit.py
	sed -i -e 's/\(version="\)[0-9.]\+[0-9a-z.-]*/\1$(version)/' \
		setup.py

clean:
	rm -f *.pyc

.PHONY: build install version
