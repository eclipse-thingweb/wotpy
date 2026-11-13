#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2017 CTIC Centro Tecnologico
# Copyright (c) 2025 National Technical University of Athens
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

"""
Enumeration classes related to the various protocol servers.
"""

from wotpy.utils.enums import EnumListMixin


class Protocols(EnumListMixin):
    """Enumeration of protocol types."""

    HTTP = "HTTP"
    WEBSOCKETS = "WEBSOCKETS"
    COAP = "COAP"
    MQTT = "MQTT"
    RTSP = "RTSP"
    ZENOH = "ZENOH"
    MODBUS = "MODBUS"


class InteractionVerbs(EnumListMixin):
    """Interactions have one or more defined interaction verbs for each
    interaction pattern.  Form Relations allow an interaction to have
    separate protocol mechanisms to support different interaction verbs."""

    READ_PROPERTY = "readproperty"
    WRITE_PROPERTY = "writeproperty"
    OBSERVE_PROPERTY = "observeproperty"
    INVOKE_ACTION = "invokeaction"
    SUBSCRIBE_EVENT = "subscribeevent"
    UNSUBSCRIBE_EVENT = "unsubscribeevent"
    READ_ALL_PROPERTIES = "readallproperties"
    WRITE_ALL_PROPERTIES = "writeallproperties"
    READ_MULTIPLE_PROPERTIES = "readmultipleproperties"
    WRITE_MULTIPLE_PROPERTIES = "writemultipleproperties"
