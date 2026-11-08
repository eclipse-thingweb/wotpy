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
Classes that contain the client logic for the HTTP protocol.
"""

import asyncio
import json
import logging
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import tornado.httpclient
import reactivex
from tornado.simple_httpclient import HTTPTimeoutError

from wotpy.protocols.client import BaseProtocolClient
from wotpy.protocols.enums import Protocols, InteractionVerbs
from wotpy.protocols.exceptions import FormNotFoundException, ClientRequestTimeout
from wotpy.protocols.http.enums import HTTPSchemes
from wotpy.protocols.utils import is_scheme_form
from wotpy.utils.utils import handle_observer_finalization
from wotpy.wot.events import EmittedEvent, PropertyChangeEmittedEvent, PropertyChangeEventInit
from wotpy.protocols.http.credential import BaseCredential, OIDC4VPCredential


class HTTPClient(BaseProtocolClient):
    """Implementation of the protocol client interface for the HTTP protocol."""

    JSON_HEADERS = {"Content-Type": "application/json"}
    DEFAULT_CON_TIMEOUT = 60
    DEFAULT_REQ_TIMEOUT = 60

    def __init__(self, connect_timeout=DEFAULT_CON_TIMEOUT, request_timeout=DEFAULT_REQ_TIMEOUT):
        self._connect_timeout = connect_timeout
        self._request_timeout = request_timeout
        self._logr = logging.getLogger(__name__)
        self._credential = None
        super().__init__()

    @classmethod
    def _pick_http_form(cls, td, forms, op=None):
        """Picks the most appropriate HTTP form from the given list of forms."""

        def is_op_form(form):
            try:
                return op is None or op == form.op or op in form.op
            except TypeError:
                return False

        def find_form(scheme):
            try:
                return next(
                    form for form in forms
                    if is_scheme_form(form, td.base, scheme) and is_op_form(form))
            except StopIteration:
                return None

        form_https = find_form(HTTPSchemes.HTTPS)

        return form_https if form_https is not None else find_form(HTTPSchemes.HTTP)

    @classmethod
    def pick_http_href(cls, td, forms, op=None):
        """Picks the most appropriate HTTP form href from the given list of forms."""

        form = cls._pick_http_form(td, forms, op=op)
        return form.href if form is not None else None

    @property
    def protocol(self):
        """Protocol of this client instance.
        A member of the Protocols enum."""

        return Protocols.HTTP

    @property
    def connect_timeout(self):
        """Returns the default connection timeout for all HTTP requests."""

        return self._connect_timeout

    @property
    def request_timeout(self):
        """Returns the default request timeout for all HTTP requests."""

        return self._request_timeout

    def is_supported_interaction(self, td, name):
        """Returns True if the any of the Forms for the Interaction
        with the given name is supported in this Protocol Binding client."""

        forms = td.get_forms(name)

        forms_http = [
            form for form in forms
            if is_scheme_form(form, td.base, HTTPSchemes.list())
        ]

        return len(forms_http) > 0

    def set_security(self, security_scheme_dict, credentials):
        """Sets the security credentials for the given security scheme."""

        credential = BaseCredential.build(security_scheme_dict, credentials)
        self._credential = credential

    async def sign_request(self, request):
        """Adds the appropriate authorization header to the request
        and delegates the addition of the header to the credential class."""

        if self._credential:
            return await self._credential.sign(request)

        return request

    async def invoke_action(self, td, name, input_value, timeout=None):
        """Invokes an Action on a remote Thing.
        Returns a Future."""

        con_timeout = timeout if timeout else self._connect_timeout
        req_timeout = timeout if timeout else self._request_timeout

        now = time.time()

        href = self.pick_http_href(td, td.get_action_forms(name))

        if href is None:
            raise FormNotFoundException()

        body = json.dumps(input_value)
        http_client = tornado.httpclient.AsyncHTTPClient()

        try:
            http_request = tornado.httpclient.HTTPRequest(
                href, method="POST",
                body=body,
                headers=self.JSON_HEADERS,
                connect_timeout=con_timeout,
                request_timeout=req_timeout,
                validate_cert=False)
        except HTTPTimeoutError:
            raise ClientRequestTimeout

        response = await http_client.fetch(await self.sign_request(http_request))
        resp_body = json.loads(response.body)

        if "error" in resp_body:
            raise Exception(resp_body)
        else:
            return resp_body

    async def write_property(self, td, name, value, timeout=None):
        """Updates the value of a Property on a remote Thing.
        Returns a Future."""

        con_timeout = timeout if timeout else self._connect_timeout
        req_timeout = timeout if timeout else self._request_timeout

        href = self.pick_http_href(td, td.get_property_forms(name))

        if href is None:
            raise FormNotFoundException()

        http_client = tornado.httpclient.AsyncHTTPClient()
        body = json.dumps(value)

        try:
            http_request = tornado.httpclient.HTTPRequest(
                href, method="PUT", body=body,
                headers=self.JSON_HEADERS,
                connect_timeout=con_timeout,
                request_timeout=req_timeout,
                validate_cert=False)
        except HTTPTimeoutError:
            raise ClientRequestTimeout

        await http_client.fetch(http_request)

    async def read_property(self, td, name, timeout=None):
        """Reads the value of a Property on a remote Thing.
        Returns a Future."""

        con_timeout = timeout if timeout else self._connect_timeout
        req_timeout = timeout if timeout else self._request_timeout

        href = self.pick_http_href(td, td.get_property_forms(name))

        if href is None:
            raise FormNotFoundException()

        http_client = tornado.httpclient.AsyncHTTPClient()

        try:
            http_request = tornado.httpclient.HTTPRequest(
                href, method="GET",
                connect_timeout=con_timeout,
                request_timeout=req_timeout,
                validate_cert=False)
        except HTTPTimeoutError:
            raise ClientRequestTimeout

        try:
            response = await http_client.fetch(await self.sign_request(http_request))
        except Exception as exception:
            # If using OIDC4VP, the first request could use an expired token.
            # In that case catch the exception, get rid of the old token and retry
            if self._credential is not None and type(self._credential) is OIDC4VPCredential:
                self._credential._access_tokens.pop(http_request.url, None)
                response = await http_client.fetch(await self.sign_request(http_request))
            else:
                raise exception

        result = json.loads(response.body)

        return result

    async def read_multiple_properties(self, td, property_names, timeout=None, options=None, form=None):
        """Reads a collection of properties using a collection form."""

        href = form.href if form is not None else self.pick_http_href(
            td, td.forms, op=InteractionVerbs.READ_MULTIPLE_PROPERTIES
        )
        if href is None:
            raise FormNotFoundException()
        options = options or {}
        parts = urlsplit(href)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query.update(options.get("uri_variables", options.get("uriVariables", {})))
        query["properties"] = ",".join(property_names)
        href = urlunsplit((parts.scheme, parts.netloc, parts.path,
                           urlencode(query), parts.fragment))
        request = tornado.httpclient.HTTPRequest(
            href, method="GET", connect_timeout=timeout or self._connect_timeout,
            request_timeout=timeout or self._request_timeout, validate_cert=False)
        response = await tornado.httpclient.AsyncHTTPClient().fetch(
            await self.sign_request(request)
        )
        value = json.loads(response.body)
        if not isinstance(value, dict):
            raise ValueError("Collection response must be a JSON object")
        return value

    async def read_all_properties(self, td, timeout=None, options=None, form=None):
        """Reads all readable properties using an all-properties form."""

        form = form or self._pick_http_form(
            td, td.forms, op=InteractionVerbs.READ_ALL_PROPERTIES
        )
        if form is None:
            raise FormNotFoundException()
        return await self.read_multiple_properties(
            td, [name for name in td.properties
                 if not td.properties[name].write_only],
            timeout=timeout, options=options, form=form
        )

    async def write_multiple_properties(self, td, values, timeout=None, options=None, form=None):
        """Writes a collection of properties using a collection form."""

        href = form.href if form is not None else self.pick_http_href(
            td, td.forms, op=InteractionVerbs.WRITE_MULTIPLE_PROPERTIES
        )
        if href is None:
            raise FormNotFoundException()
        request = tornado.httpclient.HTTPRequest(
            href, method="PUT", body=json.dumps(values), headers=self.JSON_HEADERS,
            connect_timeout=timeout or self._connect_timeout,
            request_timeout=timeout or self._request_timeout, validate_cert=False)
        await tornado.httpclient.AsyncHTTPClient().fetch(await self.sign_request(request))

    async def write_all_properties(self, td, values, timeout=None, options=None, form=None):
        """Writes all writable properties using an all-properties form."""

        form = form or self._pick_http_form(
            td, td.forms, op=InteractionVerbs.WRITE_ALL_PROPERTIES
        )
        if form is None:
            raise FormNotFoundException()
        return await self.write_multiple_properties(
            td, values, timeout=timeout, options=options, form=form
        )

    def on_event(self, td, name):
        """Subscribes to an event on a remote Thing.
        Returns an Observable."""

        href = self.pick_http_href(td, td.get_event_forms(name))

        if href is None:
            raise FormNotFoundException()

        def subscribe(observer, scheduler):
            """Subscription function to observe events using the HTTP protocol."""

            state = {"active": True}

            @handle_observer_finalization(observer)
            async def callback():
                http_client = tornado.httpclient.AsyncHTTPClient()
                http_request = tornado.httpclient.HTTPRequest(href, method="GET", validate_cert=False)

                while state["active"]:
                    try:
                        response = await http_client.fetch(await self.sign_request(http_request))
                        payload = json.loads(response.body)
                        observer.on_next(EmittedEvent(init=payload, name=name))
                    except HTTPTimeoutError:
                        pass

            def unsubscribe():
                state["active"] = False

            loop = asyncio.get_running_loop()
            loop.create_task(callback())

            return unsubscribe

        return reactivex.create(subscribe)

    def on_property_change(self, td, name):
        """Subscribes to property changes on a remote Thing.
        Returns an Observable"""

        href = self.pick_http_href(td, td.get_property_forms(name), op=InteractionVerbs.OBSERVE_PROPERTY)

        if href is None:
            raise FormNotFoundException()

        def subscribe(observer, scheduler):
            """Subscription function to observe property updates using the HTTP protocol."""

            state = {"active": True}

            @handle_observer_finalization(observer)
            async def callback():
                http_client = tornado.httpclient.AsyncHTTPClient()
                http_request = tornado.httpclient.HTTPRequest(href, method="GET", validate_cert=False)

                while state["active"]:
                    try:
                        response = await http_client.fetch(await self.sign_request(http_request))
                        value = json.loads(response.body)
                        init = PropertyChangeEventInit(name=name, value=value)
                        observer.on_next(PropertyChangeEmittedEvent(init=init))
                    except HTTPTimeoutError:
                        pass

            def unsubscribe():
                state["active"] = False

            loop = asyncio.get_running_loop()
            loop.create_task(callback())

            return unsubscribe

        return reactivex.create(subscribe)

    def on_td_change(self, url):
        """Subscribes to Thing Description changes on a remote Thing.
        Returns an Observable."""

        raise NotImplementedError
