version := isrcsubmit-0.5.1
scripts := isrcsubmit.py $(version).py
tar := $(version).tar.gz
win32 := $(version)-win32.zip
mac := $(version)-mac.zip
all := $(scripts) $(tar) $(win32) $(mac)

meta_files := $(shell echo ../{COPYRIGHT,AUTHORS,README.md,CHANGES.markdown})
files := $(meta_files) $(shell echo ../{isrcsubmit.{py,bat,sh},setup.py})

downloads := ../web/isrcsubmit.jonnyjd.net/downloads/
libdiscid := libdiscid-0.2.2
musicbrainz2 := python-musicbrainz2-0.7.4

define base-copy :=
	mkdir $(version)
	cp -d --preserve=all $(files) $(version)/
endef
define base-libs :=
	mv $(version)/COPYRIGHT $(version)/COPYRIGHT.isrcsubmit
	mv $(version)/AUTHORS $(version)/AUTHORS.isrcsubmit
	cp -ar $(musicbrainz2)/src/musicbrainz2 $(version)/
	cp -ar $(musicbrainz2) $(version)/
	cp -ar $(libdiscid) $(version)/libdiscid
endef


all: $(all)

upload: $(all)
	cp -a $^ $(downloads)
	cd $(downloads) && ftpsync -cn . ftp://isrcsubmit.jonnyjd.net/downloads/


isrcsubmit.py:
	cp -a ../isrcsubmit.py .

$(version).py:
	cp -a ../isrcsubmit.py $(version).py

tar: $(tar)
$(tar): $(files)
	$(base-copy)
	tar --owner=root --group=root -czf $@ $(version)/
	rm -rf $(version)

win32: $(win32)
$(win32): $(files)
	$(base-copy)
	$(base-libs)
	cp -a $(libdiscid)-win32/discid.dll $(version)/
	cp -ar mediatools $(version)/
	cp -a mediatools.exe $(version)/
	zip -qr $@ $(version)
	rm -rf $(version)

# universal library created with:
#     lipo -create */libdiscid.0.dylib -output libdiscid.0.dylib

mac: $(mac)
$(mac): $(files)
	$(base-copy)
	$(base-libs)
	cp -a $(libdiscid)-mac/universal/libdiscid.0.dylib $(version)/
	cp -a discisrc-mac/discisrc $(version)/
	zip -qr $@ $(version)
	rm -rf $(version)


clean:
	rm -rf $(version)
	#rm -rf $(version)-*.zip
