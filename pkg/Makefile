version := 3.0.0-dev
current := isrcsubmit-$(version)

downloads := ../web/isrcsubmit.jonnyjd.net/downloads/
upload := ftp://isrcsubmit.jonnyjd.net/downloads/
musicbrainzngs := musicbrainzngs-0.6
discid := discid-1.1.1
libdiscid := libdiscid-0.6.2
libdiscid_mac := libdiscid-0.6.1
libdiscid_win32 := libdiscid-0.6.1
libdiscid_win64 := libdiscid-0.6.2
# tag must match above for the GitHub download
libdiscid_win64_tag := v0.6.2

scripts := isrcsubmit.py $(current).py
#scripts := $(current).py
tar := $(current)
win32 := $(current)-win32
win64 := $(current)-win64
mac := $(current)-mac
all := $(scripts) $(tar).tar.gz $(win32).zip $(win64).zip $(mac).zip

source_repo := ..
source_branch := main
source_dir := isrcsubmit

# TODO: make sure isrcsubmit.py is really updated!

tag_ref := $(source_repo)/.git/refs/tags/v$(version)
branch_ref := $(source_repo)/.git/refs/heads/$(source_branch)
ifeq ($(wildcard $(tag_ref)),)
	source_ref := $(branch_ref)
else
	source_ref := $(tag_ref)
endif

ifeq ($(shell cd $(source_repo) && git tag -l v$(version)),)
	source_checkout := cd $(source_repo); git checkout $(source_branch)
else
	source_checkout := cd $(source_repo); git checkout v$(version)
endif

define cp_source =
	cp -a $(source_dir)/ $(1)
	rm -rf $(1)/.git
endef

base_libs := $(musicbrainzngs) $(discid) $(libdiscid)
define cp_base_libs =
	mv $(1)/COPYING $(1)/COPYING.isrcsubmit
	mv $(1)/AUTHORS $(1)/AUTHORS.isrcsubmit
	mkdir $(1)/src
	cp -ar $(musicbrainzngs)/musicbrainzngs $(1)/
	cp -ar $(musicbrainzngs) $(1)/src/
	cp -ar $(discid)/discid $(1)/
	cp -ar $(discid) $(1)/src/
	cp -ar $(libdiscid) $(1)/src/
endef


all: $(all)


upload: $(all)
	cp -a $^ $(downloads)
	cd $(downloads) && ftpsync -cn . $(upload)


isrcsubmit.py: $(source_ref)
	cp -a $(source_dir)/isrcsubmit.py .

$(current).py: $(source_ref)
	cp -a $(source_dir)/isrcsubmit.py $(current).py

tar: $(tar).tar.gz
$(tar).tar.gz: $(source_ref)
	$(call cp_source, $(tar))
	tar --owner=root --group=root -czf $@ $(tar)
	rm -rf $(tar)

win32: $(win32).zip
$(win32).zip: $(source_ref) $(base_libs) $(libdiscid_win32)-win32.zip mediatools
	$(call cp_source, $(win32))
	$(call cp_base_libs, $(win32))
	unzip $(libdiscid_win32)-win32.zip
	cp -a $(libdiscid_win32)-win32/discid.dll $(win32)/
	cp -ar mediatools $(win32)/
	cp -a mediatools.exe $(win32)/
	zip -qr $@ $(win32)
	rm -rf $(libdiscid_win32)-win32
	rm -rf $(win32)

win64: $(win64).zip
$(win64).zip: $(source_ref) $(base_libs) $(libdiscid_win64)-win64.zip mediatools
	$(call cp_source, $(win64))
	$(call cp_base_libs, $(win64))
	unzip -d $(libdiscid_win64)-win64 $(libdiscid_win64)-win64.zip
	cp -a $(libdiscid_win64)-win64/discid.dll $(win64)/
	cp -ar mediatools $(win64)/
	cp -a mediatools.exe $(win64)/
	zip -qr $@ $(win64)
	rm -rf $(libdiscid_win64)-win64
	rm -rf $(win64)

mac: $(mac).zip
$(mac).zip: $(source_ref) $(base_libs) $(libdiscid_mac)-mac.zip
	$(call cp_source, $(mac))
	$(call cp_base_libs, $(mac))
	unzip $(libdiscid_mac)-mac.zip
	cp -a $(libdiscid_mac)-mac/universal/libdiscid.0.dylib $(mac)/
	zip -qr $@ $(mac)
	rm -rf $(libdiscid_mac)-mac
	rm -rf $(mac)

# sources:
#
$(source_dir):
	git clone -b $(source_branch) $(source_repo) $@

$(source_ref): $(source_dir)
	cd $^ && git pull
	$(source_checkout)


# libraries:
#
$(musicbrainzngs): $(musicbrainzngs).tar.gz
	tar -xzf $^
$(musicbrainzngs).tar.gz:
	wget https://pypi.python.org/packages/source/m/musicbrainzngs/$@

$(discid): $(discid).tar.gz
	tar -xzf $^
$(discid).tar.gz:
	wget https://pypi.python.org/packages/source/d/discid/$@

libdiscid: $(libdiscid)
$(libdiscid): $(libdiscid).tar.gz
	tar -xzf $^

$(libdiscid).tar.gz:
	wget http://ftp.musicbrainz.org/pub/musicbrainz/libdiscid/$@

$(libdiscid_mac)-mac.zip:
	wget http://ftp.musicbrainz.org/pub/musicbrainz/libdiscid/$@

$(libdiscid_win32)-win32.zip:
	wget http://ftp.musicbrainz.org/pub/musicbrainz/libdiscid/$@

$(libdiscid_win64)-win64.zip:
	wget https://github.com/metabrainz/libdiscid/releases/download/${libdiscid_win64_tag}/$@

mediatools: mediatools.zip
	unzip -o $^

mediatools.zip:
	wget http://www.flanagan-family.com/$@


clean:
	rm -rf $(source_dir)
	rm -f $(all)
	rm -rf $(base_libs)
	rm -rf mediatools mediatools.exe

.PHONY: $(source_ref)
