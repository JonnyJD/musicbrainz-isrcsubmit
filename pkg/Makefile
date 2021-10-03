version := 2.2.0
current := isrcsubmit-$(version)

downloads := ../web/isrcsubmit.jonnyjd.net/downloads/
upload := ftp://isrcsubmit.jonnyjd.net/downloads/
musicbrainzngs := musicbrainzngs-0.6
discid := discid-1.1.1
libdiscid := libdiscid-0.6.1
unidecode := unidecode-1.2.0
mutagen_ver := 1.45.1
mutagen := mutagen-$(mutagen_ver)

scripts := isrcsubmit.py isrcsubmit-$(version).py \
	isrcDigitalSubmit.py isrcDigitalSubmit-$(version).py
#scripts := $(current).py
tar := $(current)
win32 := $(current)-win32
mac := $(current)-mac
all := $(scripts) $(tar).tar.gz $(win32).zip $(mac).zip

source_repo := ..
source_branch := master
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

base_libs := $(musicbrainzngs) $(discid) $(libdiscid) $(unidecode) $(mutagen)
define cp_base_libs =
	mv $(1)/COPYING $(1)/COPYING.isrcsubmit
	mv $(1)/AUTHORS $(1)/AUTHORS.isrcsubmit
	mkdir $(1)/src
	cp -ar $(musicbrainzngs)/musicbrainzngs $(1)/
	cp -ar $(musicbrainzngs) $(1)/src/
	cp -ar $(discid)/discid $(1)/
	cp -ar $(discid) $(1)/src/
	cp -ar $(libdiscid) $(1)/src/
	cp -ar $(mutagen)/mutagen $(1)/
	cp -ar $(mutagen) $(1)/src/
	cp -ar unidecode-$(unidecode)/unidecode $(1)/
	cp -ar unidecode-$(unidecode) $(1)/src/
endef


all: $(all)


upload: $(all)
	cp -a $^ $(downloads)
	cd $(downloads) && ftpsync -cn . $(upload)


isrcsubmit.py: $(source_ref)
	cp -a $(source_dir)/isrcsubmit.py .

isrcsubmit-$(version).py: $(source_ref)
	cp -a $(source_dir)/isrcsubmit.py isrcsubmit-$(version).py

isrcDigitalSubmit.py: $(source_ref)
	cp -a $(source_dir)/isrcDigitalSubmit.py .

isrcDigitalSubmit-$(version).py: $(source_ref)
	cp -a $(source_dir)/isrcDigitalSubmit.py isrcDigitalSubmit-$(version).py

tar: $(tar).tar.gz
$(tar).tar.gz: $(source_ref)
	$(call cp_source, $(tar))
	tar --owner=root --group=root -czf $@ $(tar)
	rm -rf $(tar)

win32: $(win32).zip
$(win32).zip: $(source_ref) $(base_libs) $(libdiscid)-win32.zip
	$(call cp_source, $(win32))
	$(call cp_base_libs, $(win32))
	unzip $(libdiscid)-win32.zip
	cp -a $(libdiscid)-win32/discid.dll $(win32)/
	zip -qr $@ $(win32)
	rm -rf $(libdiscid)-win32
	rm -rf $(win32)

mac: $(mac).zip
$(mac).zip: $(source_ref) $(base_libs) $(libdiscid)-mac.zip
	$(call cp_source, $(mac))
	$(call cp_base_libs, $(mac))
	unzip $(libdiscid)-mac.zip
	cp -a $(libdiscid)-mac/universal/libdiscid.0.dylib $(mac)/
	zip -qr $@ $(mac)
	rm -rf $(libdiscid)-mac
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

$(libdiscid)-%.zip:
	wget http://ftp.musicbrainz.org/pub/musicbrainz/libdiscid/$@

$(unidecode).tar.gz:
	wget https://github.com/avian2/unidecode/archive/refs/tags/$@

unidecode: $(unidecode)
$(unidecode): $(unidecode).tar.gz
	tar xfz $^

$(mutagen).tar.gz:
	wget https://github.com/quodlibet/mutagen/releases/download/release-$(mutagen_ver)/$@

mutagen: $(mutagen)
$(mutagen): $(mutagen).tar.gz
	tar xfz $^

clean:
	rm -rf $(source_dir)
	rm -f $(all)
	rm -rf $(base_libs)

.PHONY: $(source_ref)
