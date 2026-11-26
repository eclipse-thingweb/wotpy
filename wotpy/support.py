#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2018 CTIC Centro Tecnologico
# Copyright (c) 2025 National Technical University of Athens
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

"""
Functions to check if some functionalities are enabled in the current platform.
"""

import logging
import platform
import sys

FEATURE_COAP = "COAP"
FEATURE_MQTT = "MQTT"

FEATURE_REQUISITES = {
    FEATURE_COAP: {
        "max_version_exclusive": (3, 16),
        "min_version_inclusive": (3, 9),
        "platforms": ["Linux"],
    },
    FEATURE_MQTT: {
        "max_version_exclusive": (3, 16),
        "min_version_inclusive": (3, 9),
        "platforms": ["Linux", "Darwin"],
    },
}

_logger = logging.getLogger(__name__)


def _is_version_gte(version_a, version_b):
    """Returns True if version_a is greater or equal than version_b."""

    if version_a[0] > version_b[0]:
        return True

    if version_a[0] < version_b[0]:
        return False

    if version_a[1] > version_b[1]:
        return True

    if version_a[1] < version_b[1]:
        return False

    return True


def is_supported(feature):
    """Returns True if the given feature is supported in this platform."""

    reqs = FEATURE_REQUISITES.get(feature)

    if not reqs:
        raise ValueError("Unknown feature: {}".format(feature))

    vinfo = sys.version_info

    min_version = reqs.get("min_version_inclusive")

    if min_version and not _is_version_gte((vinfo.major, vinfo.minor), min_version):
        return False

    max_version = reqs.get("max_version_exclusive")

    if max_version and _is_version_gte((vinfo.major, vinfo.minor), max_version):
        return False

    platforms = reqs.get("platforms")

    if platforms and platform.system() not in platforms:
        return False

    return True


def is_coap_supported():
    """Returns True if the CoAP binding is supported in this platform."""

    return is_supported(FEATURE_COAP)


def is_mqtt_supported():
    """Returns True if the MQTT binding is supported in this platform."""

    return is_supported(FEATURE_MQTT)
