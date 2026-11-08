#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
Class that implements the Zenoh server (router).
"""

import asyncio
import copy
import json
import logging
import re

import zenoh
from slugify import slugify

from wotpy.codecs.enums import MediaTypes
from wotpy.protocols.enums import Protocols, InteractionVerbs
from wotpy.protocols.zenoh.handlers.action import ActionZenohHandler
from wotpy.protocols.zenoh.handlers.event import EventZenohHandler
from wotpy.protocols.zenoh.handlers.ping import PingZenohHandler
from wotpy.protocols.zenoh.handlers.property import PropertyZenohHandler
from wotpy.protocols.zenoh.runner import ZenohHandlerRunner
from wotpy.protocols.zenoh.utils import build_zenoh_config
from wotpy.protocols.server import BaseProtocolServer
from wotpy.wot.enums import InteractionTypes
from wotpy.wot.form import Form


class ZenohServer(BaseProtocolServer):
    """Zenoh binding server implementation."""

    DEFAULT_SERVIENT_ID = 'wotpy'
    DEFAULT_TRANSPORT = 'tcp'
    SCHEME_PREFIX = 'zenoh'

    def __init__(self, router_url, property_callback_ms=None,
                 event_callback_ms=None, servient_id=None):
        super().__init__(port=None)
        self._transport, self._router_netloc = self._split_locator(router_url)
        self._scheme = "{}+{}".format(self.SCHEME_PREFIX, self._transport)
        self._router_url = "{}/{}".format(self._transport, self._router_netloc)
        self._server_lock = asyncio.Lock()
        self._lock_conn = asyncio.Lock()
        self._servient_id = servient_id
        self._servient = None
        self._session = None
        self._logr = logging.getLogger(__name__)

        def build_runner(handler):
            return ZenohHandlerRunner(router_url=self._router_url, zenoh_handler=handler)

        self._handler_runners = [
            build_runner(PingZenohHandler(zenoh_server=self)),
            build_runner(PropertyZenohHandler(zenoh_server=self, callback_ms=property_callback_ms)),
            build_runner(EventZenohHandler(zenoh_server=self, callback_ms=event_callback_ms)),
            build_runner(ActionZenohHandler(zenoh_server=self)),
        ]

    def _split_locator(self, router_url):
        """Splits a Zenoh locator..."""
        match = re.match(r"^(?P<transport>[a-z][a-z0-9-]*)/(?P<netloc>.+)$", router_url.strip())

        if not match:
            return self.DEFAULT_TRANSPORT, router_url.strip().rstrip("/")

        return match.group("transport"), match.group("netloc").rstrip("/")

    async def _connect(self):
        """Zenoh connection helper function."""

        config = build_zenoh_config(self._router_url)

        self._logr.debug("Zenoh client config: {}".format(config))
        self._logr.info("Connecting Zenoh client to broker: {}".format(self._router_url))

        self._session = zenoh.open(config)

    async def _disconnect(self):
        """Zenoh disconnection helper function."""

        try:
            self._logr.debug("Disconnecting Zenoh client")

            self._session.close()
        except Exception as ex:
            self._logr.debug("Error disconnecting Zenoh client: {}".format(ex), exc_info=True)
        finally:
            self._session = None

    async def connect(self, force_reconnect=False):
        """Connects to the Zenoh broker."""

        async with self._lock_conn:
            if self._session is not None and force_reconnect:
                self._logr.debug("Forcing reconnection")
                await self._disconnect()
            elif self._session is not None:
                return

            await self._connect()

    async def disconnect(self):
        """Disconnects from the Zenoh broker."""

        async with self._lock_conn:
            if self._session is None:
                return

            await self._disconnect()

    @property
    def scheme(self):
        """Returns the URL scheme for this server."""

        return self._scheme

    @property
    def servient_id(self):
        """Servient ID that is used to avoid topic collisions
        when multiple Servients are connected to the same broker."""

        return slugify(self._servient_id) if self._servient_id else self.DEFAULT_SERVIENT_ID

    @property
    def protocol(self):
        """Protocol of this server instance.
        A member of the Protocols enum."""

        return Protocols.ZENOH

    def _build_forms_property(self, proprty):
        """Builds and returns the Zenoh Form instances for the given Property interaction."""

        href_rw = "{}://{}/{}/property/requests/{}/{}".format(
            self.scheme,
            self._router_netloc,
            self.servient_id,
            proprty.thing.url_name,
            proprty.url_name)

        form_read = Form(
            interaction=proprty,
            protocol=self.protocol,
            href=href_rw,
            content_type=MediaTypes.JSON,
            op=InteractionVerbs.READ_PROPERTY)

        form_write = Form(
            interaction=proprty,
            protocol=self.protocol,
            href=href_rw,
            content_type=MediaTypes.JSON,
            op=InteractionVerbs.WRITE_PROPERTY)

        href_observe = "{}://{}/{}/property/updates/{}/{}".format(
            self.scheme,
            self._router_netloc,
            self.servient_id,
            proprty.thing.url_name,
            proprty.url_name)

        form_observe = Form(
            interaction=proprty,
            protocol=self.protocol,
            href=href_observe,
            content_type=MediaTypes.JSON,
            op=InteractionVerbs.OBSERVE_PROPERTY)

        return [form_read, form_write, form_observe]

    def _build_forms_action(self, action):
        """Builds and returns the Zenoh Form instances for the given Action interaction."""

        href = "{}://{}/{}/action/invocation/{}/{}".format(
            self.scheme,
            self._router_netloc,
            self.servient_id,
            action.thing.url_name,
            action.url_name)

        form = Form(
            interaction=action,
            protocol=self.protocol,
            href=href,
            content_type=MediaTypes.JSON,
            op=InteractionVerbs.INVOKE_ACTION)

        return [form]

    def _build_forms_event(self, event):
        """Builds and returns the Zenoh Form instances for the given Event interaction."""

        href = "{}://{}/{}/event/{}/{}".format(
            self.scheme,
            self._router_netloc,
            self.servient_id,
            event.thing.url_name,
            event.url_name)

        form = Form(
            interaction=event,
            protocol=self.protocol,
            href=href,
            content_type=MediaTypes.JSON,
            op=InteractionVerbs.SUBSCRIBE_EVENT)

        return [form]

    def build_forms(self, hostname, interaction):
        """Builds and returns a list with all Forms that are
        linked to this server for the given Interaction."""

        intrct_type_map = {
            InteractionTypes.PROPERTY: self._build_forms_property,
            InteractionTypes.ACTION: self._build_forms_action,
            InteractionTypes.EVENT: self._build_forms_event
        }

        if interaction.interaction_type not in intrct_type_map:
            raise ValueError("Unsupported interaction")

        return intrct_type_map[interaction.interaction_type](interaction)

    def build_base_url(self, hostname, thing):
        """Returns the base URL for the given Thing in the context of this server."""

        return self._router_url

    async def start(self, servient=None):
        """Starts the Zenoh broker and all the Zenoh clients
        that handle the WoT clients requests."""

        self._servient = servient

        await self.connect(force_reconnect=True)

        async with self._server_lock:
            for runner in self._handler_runners:
                await runner.start()

    async def stop(self):
        """Stops the Zenoh broker and the Zenoh clients."""

        async with self._server_lock:
            for runner in self._handler_runners:
                await runner.stop()

        await self.disconnect()
