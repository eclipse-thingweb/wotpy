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
Request handler for All Properties interactions.
"""

import json

from tornado.web import HTTPError, RequestHandler

import wotpy.protocols.http.handlers.utils as handler_utils


class AllPropertiesReadWriteHandler(RequestHandler):
    """Handler for All Properties get/set requests."""

    def initialize(self, http_server):
        self._server = http_server

    async def get(self, thing_name):
        """Reads and returns all Property values."""

        exposed_thing = handler_utils.get_exposed_thing(self._server, thing_name)
        valid_creds = await self._server._check_credentials(exposed_thing.title, self.request)
        if not valid_creds:
            handler_utils.request_auth(self, self._server.security_scheme, thing_name)
        else:
            names = self.get_query_argument("properties", None)
            value = (
                await exposed_thing.handle_read_multiple_properties(names.split(","))
                if names else await exposed_thing.handle_read_all_properties()
            )
            self.write(json.dumps(value))
            self.set_header('Content-Type', 'application/json')

    async def put(self, thing_name):
        """Updates all Property values."""

        if self.request.headers.get("Content-Type", "").split(";")[0] != "application/json":
            raise HTTPError(status_code=415, reason="Expected application/json")

        exposed_thing = handler_utils.get_exposed_thing(self._server, thing_name)
        valid_creds = await self._server._check_credentials(exposed_thing.title, self.request)
        if not valid_creds:
            handler_utils.request_auth(self, self._server.security_scheme, thing_name)
        else:
            try:
                values = json.loads(self.request.body)
            except (TypeError, json.JSONDecodeError) as ex:
                raise HTTPError(status_code=400, reason=f"Error decoding JSON: {str(ex)}")

            try:
                await exposed_thing.handle_write_multiple_properties(values)
            except KeyError as ex:
                raise HTTPError(status_code=404, reason=str(ex))
            except PermissionError as ex:
                raise HTTPError(status_code=403, reason=str(ex))
            except (TypeError, ValueError) as ex:
                raise HTTPError(status_code=400, reason=str(ex))
    