#!/usr/bin/env bash

# Copyright (c) 2021 CTIC Centro Tecnologico
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

set -e
set -x

# trunk-ignore(shellcheck/SC2312)
if [[ -n "$(git status --porcelain)" ]]; then
    echo "Git working directory should be clean"
    exit 1
fi

# trunk-ignore(shellcheck/SC1035)
if [[ !("$1" =~ ^(major|minor|patch)$) ]]; then
    echo "Part should be one of major, minor or patch"
    exit 1
fi

# trunk-ignore(shellcheck/SC2312)
if [[ "develop" != $(git branch --show-current) ]]; then
    echo "Current branch is not develop"
    exit 1
fi

bump-my-version bump "$1"

git checkout master &&
    git merge develop &&
    git checkout develop &&
    git push origin --all &&
    git push origin --tags
