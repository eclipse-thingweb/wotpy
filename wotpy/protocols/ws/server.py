#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2017 CTIC Centro Tecnologico
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
Class that implements the WebSockets server.
"""

from tornado import web
from tornado.httpserver import HTTPServer

from wotpy.codecs.enums import MediaTypes
from wotpy.protocols.enums import Protocols
from wotpy.protocols.server import BaseProtocolServer
from wotpy.protocols.ws.enums import WebsocketSchemes
from wotpy.protocols.ws.handler import WebsocketHandler
from wotpy.wot.form import Form


class WebsocketServer(BaseProtocolServer):
    """WebSockets binding server implementation. Builds a Tornado application
    that uses the WebsocketHandler handler to process WebSockets messages."""

    DEFAULT_PORT = 8081

    def __init__(self, port=DEFAULT_PORT, ssl_context=None):
        super().__init__(port=port)
        self._server = None
        self._app = self._build_app()
        self._ssl_context = ssl_context
        self._servient = None

    @property
    def protocol(self):
        """Protocol of this server instance.
        A member of the Protocols enum."""

        return Protocols.WEBSOCKETS

    @property
    def scheme(self):
        """Returns the URL scheme for this server."""

        return WebsocketSchemes.WSS if self.is_secure else WebsocketSchemes.WS

    @property
    def is_secure(self):
        """Returns True if this server is configured to use SSL encryption."""

        return self._ssl_context is not None

    @property
    def app(self):
        """Tornado application property."""

        return self._app

    def _build_app(self):
        """Builds and returns the Tornado application for the WebSockets server."""

        return web.Application([(
            r"/(?P<name>[^\/]+)",
            WebsocketHandler,
            {"websocket_server": self}
        )])

    def build_forms(self, hostname, interaction):
        """Builds and returns a list with all Form that are
        linked to this server for the given Interaction."""

        exposed_thing = self.exposed_thing_set.find_by_interaction(interaction)

        if not exposed_thing:
            raise ValueError("Unknown Interaction")

        base_url = self.build_base_url(hostname=hostname, thing=exposed_thing.thing)

        return [
            Form(
                interaction=interaction,
                protocol=self.protocol,
                href=base_url,
                content_type=MediaTypes.JSON
            )
        ]

    def build_top_level_forms(self, hostname, thing):
        """Builds and returns a list with all top-level Forms."""

        return []

    def build_base_url(self, hostname, thing):
        """Returns the base URL for the given Thing in the context of this server."""

        if not self.exposed_thing_set.find_by_thing_title(thing.title):
            raise ValueError("Unknown Thing")

        hostname = hostname.rstrip("/")

        return "{}://{}:{}/{}".format(self.scheme, hostname, self.port, thing.url_name)

    async def start(self, servient=None):
        """Starts the WebSockets server."""

        self._servient = servient

        self._server = HTTPServer(self.app, ssl_options=self._ssl_context)
        self._server.listen(self.port)

    async def stop(self):
        """Stops the WebSockets server."""

        if not self._server:
            return

        self._server.stop()
        self._server = None
