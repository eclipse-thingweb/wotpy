#!/usr/bin/env bash

# Copyright (c) 2021 CTIC Centro Tecnologico
# Copyright (c) 2026 Contributors to the Eclipse Foundation
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# SPDX-License-Identifier: MIT

set -euo pipefail

usage() {
    echo "Usage:"
    echo "  $0 prepare <major|minor|patch>  # Creates a release branch and bumps version for PR"
    echo "  $0 release                      # Merges latest develop to master, tags and triggers release"
    exit 1
}

if [[ -n "$(git status --porcelain)" ]]; then
    echo "Git working directory should be clean"
    exit 1
fi

if [[ $# -lt 1 || $# -gt 2 ]]; then
    usage
fi

MODE="$1"

case "$MODE" in
    prepare)
        if [[ $# -ne 2 ]]; then
            usage
        fi
        PART="$2"
        if [[ !("$PART" =~ ^(major|minor|patch)$) ]]; then
            echo "Error: Part must be one of: major, minor, patch"
            usage
        fi

        git checkout develop
        git pull upstream develop

        NEW_VERSION=$(bump2version --dry-run --list "$PART" | grep '^new_version=' | cut -d= -f2)
        BRANCH_NAME="release/v${NEW_VERSION}"

        git checkout -b "$BRANCH_NAME"
        bump2version --no-tag "$PART"
        git push -u origin "$BRANCH_NAME"

        echo ""
        echo "Release branch '${BRANCH_NAME}' pushed successfully"
        echo "Please open and merge a Pull Request from '${BRANCH_NAME}' into 'develop'"
        ;;

    release)
        if [[ $# -ne 1 ]]; then
            usage
        fi
        git checkout develop
        git pull upstream develop

        CURRENT_VERSION=$(bump2version --dry-run --list patch | grep '^current_version=' | cut -d= -f2)
        TAG_NAME="v${CURRENT_VERSION}"

        if git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
            echo "Error: Tag '$TAG_NAME' already exists locally or remotely"
            exit 1
        fi

        git checkout master
        git pull upstream master
        git merge develop -m "Release ${TAG_NAME}"

        git tag -a "$TAG_NAME" -m "Release ${TAG_NAME}"

        git push upstream master
        git push upstream "$TAG_NAME"

        echo ""
        echo "Successfully released and tagged '${TAG_NAME}'"
        ;;

    *)
        usage
        ;;
esac
