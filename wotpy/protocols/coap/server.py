#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2018 CTIC Centro Tecnologico
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
Class that implements the CoAP server.
"""

import asyncio
import json
import logging

import aiocoap
import aiocoap.resource
from aiocoap.oscore_sitewrapper import OscoreSiteWrapper

from wotpy.codecs.enums import MediaTypes
from wotpy.protocols.coap.authenticator import BaseAuthenticator
from wotpy.protocols.coap.enums import CoAPSchemes
from wotpy.protocols.coap.resources.action import ActionResource
from wotpy.protocols.coap.resources.event import EventResource
from wotpy.protocols.coap.resources.property import PropertyResource
from wotpy.protocols.coap.resources.properties import PropertiesResource
from wotpy.protocols.enums import Protocols, InteractionVerbs
from wotpy.protocols.server import BaseProtocolServer
from wotpy.utils.utils import get_main_ipv4_address
from wotpy.wot.enums import InteractionTypes, SecuritySchemeType
from wotpy.wot.form import Form


class CoAPServer(BaseProtocolServer):
    """CoAP binding server implementation."""

    DEFAULT_PORT = 5683
    DEFAULT_SECURITY_SCHEME = {"scheme": SecuritySchemeType.NOSEC}

    def __init__(self, port=DEFAULT_PORT, ssl_context=None, oscore_credentials_map=None,
                 security_scheme=DEFAULT_SECURITY_SCHEME):
        super().__init__(port=port)
        self._server = None
        self._server_lock = asyncio.Lock()
        self._ssl_context = ssl_context
        self._oscore_credentials_map = oscore_credentials_map
        self._logr = logging.getLogger(__name__)
        self._servient = None
        self._security_scheme = security_scheme if security_scheme.get("scheme", None) in\
            SecuritySchemeType.list() else self.DEFAULT_SECURITY_SCHEME

    @property
    def protocol(self):
        """Protocol of this server instance.
        A member of the Protocols enum."""

        return Protocols.COAP

    @property
    def scheme(self):
        """Returns the URL scheme for this server."""

        return CoAPSchemes.COAPS if self.is_secure else CoAPSchemes.COAP

    @property
    def is_secure(self):
        """Returns True if this server is configured to use SSL encryption."""

        return self._ssl_context is not None

    def _build_forms_property(self, proprty, hostname):
        """Builds and returns the CoAP Form instances for the given Property interaction."""

        href_prop = "{}://{}:{}/property?thing={}&name={}".format(
            self.scheme, hostname.rstrip("/").lstrip("/"), self.port,
            proprty.thing.url_name, proprty.url_name)

        forms = []
        if not proprty.data_schema.write_only:
            forms.append(Form(
                interaction=proprty,
                protocol=self.protocol,
                href=href_prop,
                content_type=MediaTypes.JSON,
                op=InteractionVerbs.READ_PROPERTY
            ))
        if not proprty.data_schema.read_only:
            forms.append(Form(
                interaction=proprty,
                protocol=self.protocol,
                href=href_prop,
                content_type=MediaTypes.JSON,
                op=InteractionVerbs.WRITE_PROPERTY
            ))

        form_observe = Form(
            interaction=proprty,
            protocol=self.protocol,
            href=href_prop,
            content_type=MediaTypes.JSON,
            op=InteractionVerbs.OBSERVE_PROPERTY
        )

        return forms + [form_observe]

    def _build_forms_action(self, action, hostname):
        """Builds and returns the CoAP Form instances for the given Action interaction."""

        href_invoke = "{}://{}:{}/action?thing={}&name={}".format(
            self.scheme,
            hostname.rstrip("/").lstrip("/"),
            self.port,
            action.thing.url_name,
            action.url_name
        )

        form_invoke = Form(
            interaction=action,
            protocol=self.protocol,
            href=href_invoke,
            content_type=MediaTypes.JSON,
            op=InteractionVerbs.INVOKE_ACTION
        )

        return [form_invoke]

    def _build_forms_event(self, event, hostname):
        """Builds and returns the CoAP Form instances for the given Event interaction."""

        href = "{}://{}:{}/event?thing={}&name={}".format(
            self.scheme,
            hostname.rstrip("/").lstrip("/"),
            self.port,
            event.thing.url_name,
            event.url_name
        )

        form = Form(
            interaction=event,
            protocol=self.protocol,
            href=href,
            content_type=MediaTypes.JSON,
            op=InteractionVerbs.SUBSCRIBE_EVENT
        )

        return [form]

    def build_forms(self, hostname, interaction):
        """Builds and returns a list with all Form that are
        linked to this server for the given Interaction."""

        intrct_type_map = {
            InteractionTypes.PROPERTY: self._build_forms_property,
            InteractionTypes.ACTION: self._build_forms_action,
            InteractionTypes.EVENT: self._build_forms_event
        }

        if interaction.interaction_type not in intrct_type_map:
            raise ValueError("Unsupported interaction")

        return intrct_type_map[interaction.interaction_type](interaction, hostname)

    def build_top_level_forms(self, hostname, thing):
        """Builds and returns a list with all top-level Forms
        that are linked to this server for all exposed Things."""

        href_all_properties = "{}://{}:{}/properties?thing={}".format(
            self.scheme, hostname.rstrip("/").lstrip("/"), self.port, thing.url_name)

        readable = any(not prop.data_schema.write_only for prop in thing.properties.values())
        writable = any(not prop.data_schema.read_only for prop in thing.properties.values())
        operations = []
        if readable:
            operations.extend([
                InteractionVerbs.READ_ALL_PROPERTIES,
                InteractionVerbs.READ_MULTIPLE_PROPERTIES
            ])
        if writable:
            operations.extend([
                InteractionVerbs.WRITE_ALL_PROPERTIES,
                InteractionVerbs.WRITE_MULTIPLE_PROPERTIES
            ])
        if not operations:
            return []

        form_all_properties = Form(
            interaction=None,
            protocol=self.protocol,
            href=href_all_properties,
            content_type=MediaTypes.JSON,
            op=operations)

        return [form_all_properties]

    def build_base_url(self, hostname, thing):
        """Returns the base URL for the given Thing in the context of this server."""

        if not self.exposed_thing_set.find_by_thing_title(thing.title):
            raise ValueError("Unknown Thing")

        return "{}://{}:{}".format(
            self.scheme,
            hostname.rstrip("/").lstrip("/"),
            self.port)

    def _build_root_site(self):
        """Builds and returns the root CoAP Site."""

        root = aiocoap.resource.Site()

        root.add_resource(
            (".well-known", "core"),
            aiocoap.resource.WKCResource(root.get_resources_as_linkheader))

        root.add_resource(
            ("property",),
            PropertyResource(self))

        root.add_resource(
            ("properties",),
            PropertiesResource(self))

        root.add_resource(
            ("action",),
            ActionResource(self))

        root.add_resource(
            ("event",),
            EventResource(self))

        return root

    def _get_bind_address(self):
        """Returns the bind address for the CoAP server.
        By default it will try to bind to all addresses,
        although this does not work outside Linux.
        When the full-featured UDP6 transport is not available it
        will try to guess the main IPv4 address and bind to that."""

        # TODO: Check if this is needed in this version of aiocoap.
        # Keep in mind that "get_default_servertransports" is only intented for internal use.

        # transports = list(aiocoap.defaults.get_default_servertransports())

        # if not (len(transports) == 1 and transports[0] == "udp6"):
        #     self._logr.warning("Platform does not support aiocoap udp6 transport: {}".format(transports))
        #     return get_main_ipv4_address(), self.port
        # else:
        #     return "::", self.port

        return "::", self.port

    async def _check_credentials(self, exposed_thing_name, request):
        """Checks the credentials of a request for a specific thing."""

        if self._servient:
            creds = self._servient.retrieve_credentials(exposed_thing_name)
            authenticator = BaseAuthenticator.build(self._security_scheme)
            return authenticator.authenticate(creds, request)
        else:
            #TODO: If the server is created without a servient should it try to check credentials in some other way?
            return True

    async def start(self, servient=None):
        """Starts the CoAP server."""

        self._servient = servient

        async with self._server_lock:
            if self._server is not None:
                return

            root = self._build_root_site()
            bind_address = self._get_bind_address()
            self._logr.info("Binding CoAP server to: {}".format(bind_address))

            if self._oscore_credentials_map:
                server_credentials = aiocoap.credentials.CredentialsMap()
                with open(self._oscore_credentials_map, "rb") as file:
                    server_credentials.load_from_dict(json.load(file))

                root = OscoreSiteWrapper(root, server_credentials)
            else:
                server_credentials = None

            coap_server = await aiocoap.Context.create_server_context(
                root, bind=bind_address, _ssl_context=self._ssl_context,
                server_credentials=server_credentials)
            self._server = coap_server

    async def stop(self):
        """Stops the CoAP server."""

        async with self._server_lock:
            if self._server is None:
                return

            await self._server.shutdown()
            self._server = None
