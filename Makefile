version := $(shell git describe origin/master | sed -e 's/v\([0-9.]\+\).*/\1/')
current := isrcsubmit-$(version)
changes := changes.markdown
changes_source := CHANGES.markdown
git := .git/refs/remote/origin/master


all: jekyll

jekyll: changes version
	jekyll

version:
	sed -i -e 's/ version:\s[0-9.]\+/ version: $(version)/' _config.yml
	sed -i -e 's/current:\sisrcsubmit-[0-9.]\+/current: $(current)/g' \
		_config.yml

changes: $(changes)
$(changes): $(git)
	echo -e "---\nlayout: default\ntitle: changes\n---" > $@
	git show origin/master:$(changes_source) \
	    | sed -e 's:\[#\([0-9]\+\)\]:\[#\1\]({{site.issues.url}}/\1)\::g' \
	    >> $@

$(git):
	git fetch origin
