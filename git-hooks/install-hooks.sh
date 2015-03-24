#!/usr/bin/env bash

# List of the hooks we will install for that project
HOOK_NAMES="pre-commit"

# Directory where the hooks will be installed
HOOK_DIR=$(git rev-parse --show-toplevel)/.git/hooks

# Directory where the project's hooks are
PROJECT_HOOK_DIR=$(git rev-parse --show-toplevel)/git-hooks

# For each hook
for hook in $HOOK_NAMES
do
	# If the hook already exists, is executable, and is not a symlink
	if [ ! -h $HOOK_DIR/$hook -a -x $HOOK_DIR/$hook ]; then
		mv $HOOK_DIR/$hook $HOOK_DIR/$hook.local
	fi

	# create the symlink, overwriting the file if it exists
	ln -s -f $PROJECT_HOOK_DIR/$hook $HOOK_DIR
done
