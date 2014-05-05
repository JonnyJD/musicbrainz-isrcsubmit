branch := master
#branch := v1
version = $(shell git describe origin/$(branch) | sed -e 's/v\([0-9.]\+\).*/\1/')
old_version = $(shell git describe origin/v1 | sed -e 's/v\([0-9.]\+\).*/\1/')
current = isrcsubmit-$(version)
old = isrcsubmit-$(old_version)
changes := changes.markdown
changes_source := CHANGES.markdown
git := .git/refs/remote/origin/$(branch)


all: jekyll

jekyll: changes version
	jekyll build

version: $(git)
	# setting version
	sed -i -e 's/ version:\s[0-9a-z.-]\+/ version: $(version)/' _config.yml
	sed -i -e 's/current:\sisrcsubmit-[0-9a-z.-]\+/current: $(current)/g' \
		_config.yml
	# setting old version
	sed -i -e 's/ old_version:\s[0-9a-z.-]\+/ old_version: $(old_version)/'\
		_config.yml
	sed -i -e 's/old:\sisrcsubmit-[0-9a-z.-]\+/old: $(old)/g' \
		_config.yml

changes: $(changes)
$(changes): $(git)
	echo -e "---\nlayout: default\ntitle: changes\n---" > $@
	git show origin/$(branch):$(changes_source) \
	    | sed -e 's:\[#\([0-9]\+\)\]:\[#\1\]({{site.issues.url}}/\1)\::g' \
	    >> $@

$(git):
	git fetch origin
