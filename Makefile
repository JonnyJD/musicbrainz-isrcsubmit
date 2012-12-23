version := isrcsubmit-0.5.1
changes := changes.markdown
changes_source := CHANGES.markdown
git := .git/refs/remote/origin/master

#TODO: update version automatically

all: jekyll

jekyll: changes
	jekyll

changes: $(changes)
$(changes): $(git)
	echo -e "---\nlayout: default\ntitle: changes\n---" > $@
	git show origin/master:$(changes_source) \
	    | sed -e 's:\[#\([0-9]\+\)\]:\[#\1\]({{site.issues.url}}/\1)\::g' \
	    >> $@

$(git):
	git fetch origin
