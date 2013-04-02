#branch := master
branch := v1
version := $(shell git describe origin/$(branch) | sed -e 's/v\([0-9.]\+\).*/\1/')
pre_version := $(shell git describe origin/master | sed -e 's/v\([0-9.]\+-[0-9a-z.]\+\).*/\1/')
current := isrcsubmit-$(version)
pre := isrcsubmit-$(pre_version)
changes := changes.markdown
changes_source := CHANGES.markdown
git := .git/refs/remote/origin/$(branch)


all: jekyll

jekyll: changes version
	jekyll

version:
	# setting version
	sed -i -e 's/ version:\s[0-9.]\+/ version: $(version)/' _config.yml
	sed -i -e 's/current:\sisrcsubmit-[0-9.]\+/current: $(current)/g' \
		_config.yml
	# setting pre-release version
	sed -i -e 's/ pre_version:\s[0-9a-z.-]\+/ pre_version: $(pre_version)/'\
		_config.yml
	sed -i -e 's/pre:\sisrcsubmit-[0-9a-z.-]\+/pre: $(pre)/g' \
		_config.yml

changes: $(changes)
$(changes): $(git)
	echo -e "---\nlayout: default\ntitle: changes\n---" > $@
	git show origin/$(branch):$(changes_source) \
	    | sed -e 's:\[#\([0-9]\+\)\]:\[#\1\]({{site.issues.url}}/\1)\::g' \
	    >> $@

$(git):
	git fetch origin
