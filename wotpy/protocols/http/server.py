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
Class that implements the HTTP server.
"""

import logging

import tornado.httpserver
import tornado.web

from wotpy.codecs.enums import MediaTypes
from wotpy.protocols.enums import Protocols, InteractionVerbs
from wotpy.protocols.http.authenticator import BaseAuthenticator
from wotpy.protocols.http.enums import HTTPSchemes
from wotpy.protocols.http.handlers.action import ActionInvokeHandler
from wotpy.protocols.http.handlers.event import EventObserverHandler
from wotpy.protocols.http.handlers.property import PropertyObserverHandler, PropertyReadWriteHandler
from wotpy.protocols.http.handlers.properties import AllPropertiesReadWriteHandler
from wotpy.protocols.server import BaseProtocolServer
from wotpy.wot.enums import InteractionTypes, SecuritySchemeType
from wotpy.wot.form import Form


class HTTPServer(BaseProtocolServer):
    """HTTP binding server implementation."""

    DEFAULT_PORT = 8080
    DEFAULT_SECURITY_SCHEME = {"scheme": SecuritySchemeType.NOSEC}

    def __init__(self, port=DEFAULT_PORT, ssl_context=None, action_ttl_secs=300,
                 security_scheme=DEFAULT_SECURITY_SCHEME, form_port=None, externalCertificate=None):
        super().__init__(port=port, form_port=form_port)
        self._server = None
        self._servient = None
        self._app = self._build_app()
        self._ssl_context = ssl_context
        self._scheme = HTTPSchemes.HTTPS if ssl_context is not None\
            or externalCertificate is True else HTTPSchemes.HTTP
        self._logr = logging.getLogger(__name__)
        self._action_ttl_secs = action_ttl_secs
        self._pending_actions = {}
        self._invocation_check_times = {}
        self._security_scheme = security_scheme if security_scheme.get("scheme", None) in\
            SecuritySchemeType.list() else self.DEFAULT_SECURITY_SCHEME

    @property
    def protocol(self):
        """Protocol of this server instance.
        A member of the Protocols enum."""

        return Protocols.HTTP

    @property
    def security_scheme(self):
        """Returns the configured security scheme of this server."""

        return self._security_scheme

    @property
    def scheme(self):
        """Returns the URL scheme for this server."""

        return self._scheme

    @property
    def app(self):
        """Tornado application."""

        return self._app

    @property
    def action_ttl(self):
        """Returns the Action invocations Time-To-Live (seconds)."""

        return self._action_ttl_secs

    @property
    def pending_actions(self):
        """Dict of pending action invocations represented as Futures."""

        return self._pending_actions

    @property
    def invocation_check_times(self):
        """Dict that contains the timestamp of the last time an invocation was checked by a client."""

        return self._invocation_check_times

    async def _check_credentials(self, exposed_thing_name, request):
        """Checks the credentials of a request for a specific thing."""

        if self._servient:
            creds = self._servient.retrieve_credentials(exposed_thing_name)
            authenticator = BaseAuthenticator.build(self._security_scheme)
            return authenticator.authenticate(creds, request)
        else:
            #TODO: If the server is created without a servient should it try to check credentials in some other way?
            return True

    def _build_app(self):
        """Builds and returns the Tornado application for the WebSockets server."""

        return tornado.web.Application(
            [
                (
                    r"/(?P<thing_name>[^\/]+)/property/(?P<name>[^\/]+)",
                    PropertyReadWriteHandler,
                    {"http_server": self}
                ),
                (
                    r"/(?P<thing_name>[^\/]+)/property/(?P<name>[^\/]+)/subscription",
                    PropertyObserverHandler,
                    {"http_server": self}
                ),
                (
                    r"/(?P<thing_name>[^\/]+)/properties",
                    AllPropertiesReadWriteHandler,
                    {"http_server": self}
                ),
                (
                    r"/(?P<thing_name>[^\/]+)/action/(?P<name>[^\/]+)",
                    ActionInvokeHandler,
                    {"http_server": self}
                ),
                (
                    r"/(?P<thing_name>[^\/]+)/event/(?P<name>[^\/]+)/subscription",
                    EventObserverHandler,
                    {"http_server": self}
                )
            ]
        )

    def _build_forms_property(self, proprty, hostname):
        """Builds and returns the HTTP Form instances for the given Property interaction."""

        href_read_write = "{}://{}:{}/{}/property/{}".format(
            self.scheme,
            hostname.rstrip("/").lstrip("/"),
            self.form_port,
            proprty.thing.url_name,
            proprty.url_name
        )

        forms = []
        if not proprty.data_schema.write_only:
            forms.append(Form(
                interaction=proprty,
                protocol=self.protocol,
                href=href_read_write,
                content_type=MediaTypes.JSON,
                op=InteractionVerbs.READ_PROPERTY
            ))
        if not proprty.data_schema.read_only:
            forms.append(Form(
                interaction=proprty,
                protocol=self.protocol,
                href=href_read_write,
                content_type=MediaTypes.JSON,
                op=InteractionVerbs.WRITE_PROPERTY
            ))

        form_read_write = forms

        href_observe = "{}/subscription".format(href_read_write)

        form_observe = Form(
            interaction=proprty,
            protocol=self.protocol,
            href=href_observe,
            content_type=MediaTypes.JSON,
            op=[InteractionVerbs.OBSERVE_PROPERTY]
        )

        return form_read_write + [form_observe]

    def _build_forms_action(self, action, hostname):
        """Builds and returns the HTTP Form instances for the given Action interaction."""

        href_invoke = "{}://{}:{}/{}/action/{}".format(
            self.scheme,
            hostname.rstrip("/").lstrip("/"),
            self.form_port,
            action.thing.url_name,
            action.url_name
        )

        form_invoke = Form(
            interaction=action,
            protocol=self.protocol,
            href=href_invoke,
            content_type=MediaTypes.JSON,
            op=[InteractionVerbs.INVOKE_ACTION]
        )

        return [form_invoke]

    def _build_forms_event(self, event, hostname):
        """Builds and returns the HTTP Form instances for the given Event interaction."""

        href_observe = "{}://{}:{}/{}/event/{}/subscription".format(
            self.scheme,
            hostname.rstrip("/").lstrip("/"),
            self.form_port,
            event.thing.url_name,
            event.url_name
        )

        form_observe = Form(
            interaction=event,
            protocol=self.protocol,
            href=href_observe,
            content_type=MediaTypes.JSON,
            op=[InteractionVerbs.SUBSCRIBE_EVENT]
        )

        return [form_observe]

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

        href_all_properties = "{}://{}:{}/{}/properties".format(
            self.scheme, hostname.rstrip("/").lstrip("/"), self.form_port, thing.url_name)

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

        return "{}://{}:{}/{}".format(
            self.scheme, hostname.rstrip("/").lstrip("/"),
            self.form_port, thing.url_name)

    async def start(self, servient=None):
        """Starts the HTTP server."""

        self._servient = servient

        self._logr.info("Starting HTTP server on: {}".format(self.port))

        self._server = tornado.httpserver.HTTPServer(self.app, ssl_options=self._ssl_context)
        self._server.listen(self.port)

    async def stop(self):
        """Stops the HTTP server."""

        if not self._server:
            return

        self._server.stop()
        self._server = None
