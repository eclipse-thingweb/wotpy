#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
CoAP resources to deal with Property interactions.
"""

import json
import logging

import aiocoap
import aiocoap.error
import aiocoap.resource

from wotpy.protocols.coap.resources.utils import parse_request_opt_query

JSON_CONTENT_FORMAT = 50


async def _build_property_value_response(server, request):
    """Takes a CoAP request and returns all Thing Property values."""

    query = parse_request_opt_query(request)
    url_name_thing = query.get("thing")

    if not url_name_thing:
        raise aiocoap.error.BadRequest("Missing query arguments")

    exposed_thing = server.exposed_thing_set.find_by_thing_title(url_name_thing)

    if not exposed_thing:
        raise aiocoap.error.NotFound("Thing not found")

    valid_creds = await server._check_credentials(exposed_thing.title, request)
    if not valid_creds:
        raise aiocoap.error.Unauthorized("Authentication required")

    property_names = query.get("properties")
    if property_names:
        value = await exposed_thing.handle_read_multiple_properties(
            property_names.split(",")
        )
    else:
        value = await exposed_thing.handle_read_all_properties()
    payload = json.dumps(value).encode("utf-8")
    response = aiocoap.Message(code=aiocoap.Code.CONTENT, payload=payload)
    response.opt.content_format = JSON_CONTENT_FORMAT
    return response


async def _write_property_values(server, request):
    """Updates all Thing Property values from a CoAP request."""

    query = parse_request_opt_query(request)
    url_name_thing = query.get("thing")

    if not url_name_thing:
        raise aiocoap.error.BadRequest("Missing query arguments")

    exposed_thing = server.exposed_thing_set.find_by_thing_title(url_name_thing)
    if not exposed_thing:
        raise aiocoap.error.NotFound("Thing not found")

    valid_creds = await server._check_credentials(exposed_thing.title, request)
    if not valid_creds:
        raise aiocoap.error.Unauthorized("Authentication required")

    try:
        values = json.loads(request.payload)
    except (TypeError, json.JSONDecodeError) as ex:
        raise aiocoap.error.BadRequest(str(ex))

    try:
        await exposed_thing.handle_write_multiple_properties(values)
    except (KeyError, TypeError) as ex:
        raise aiocoap.error.MethodNotAllowed(str(ex))


class PropertiesResource(aiocoap.resource.ObservableResource):
    """CoAP resource that implements the All Properties read and write verbs."""

    def __init__(self, server):
        super().__init__()
        self._server = server
        self._logr = logging.getLogger(__name__)

    async def render_get(self, request):
        """Returns a CoAP response with the current property value."""

        response = await _build_property_value_response(self._server, request)
        return response

    async def render_put(self, request):
        """Updates all properties with values from the CoAP request payload."""

        await _write_property_values(self._server, request)
        return aiocoap.Message(code=aiocoap.Code.CHANGED)
