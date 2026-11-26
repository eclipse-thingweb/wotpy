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
Class that represents a Thing consumed by a servient.
"""

import asyncio

from reactivex.scheduler.eventloop import IOLoopScheduler
from tornado import ioloop

from wotpy.protocols.enums import InteractionVerbs
from wotpy.wot.consumed.interaction_map import (
    ConsumedThingActionDict,
    ConsumedThingEventDict,
    ConsumedThingPropertyDict
)


class ConsumedThing:
    """An entity that serves to interact with a Thing.
    An application uses this class when it acts as a *client* of the Thing."""

    def __init__(self, servient, td):
        self._servient = servient
        self._td = td

    def __str__(self):
        return "<{}> {}".format(self.__class__.__name__, self.td.id)

    def __getattr__(self, name):
        """Search for members that raised an AttributeError in
        the private ThingFragment instance before propagating the exception."""

        return getattr(self.td.to_thing_fragment(), name)

    @property
    def servient(self):
        """Returns the Servient that contains this Consumed Thing."""

        return self._servient

    @property
    def td(self):
        """Returns the ThingDescription instance that represents
        the TD that this Consumed Thing is based on."""

        return self._td

    async def invoke_action(
        self, name, input_value=None, timeout=None, client_kwargs=None
    ):
        """Takes the Action name from the name argument and the list of parameters,
        then requests from the underlying platform and the Protocol Bindings to invoke
        the Action on the remote Thing and return the result.
        Returns a Future that resolves with the return value or rejects with an Error.
        """

        client = self.servient.select_client(self.td, name)
        client_kwargs = client_kwargs if client_kwargs else {}

        result = await client.invoke_action(
            self.td,
            name,
            input_value,
            timeout=timeout,
            **client_kwargs.get(client.protocol, {})
        )

        return result

    async def write_property(self, name, value, timeout=None, client_kwargs=None):
        """Takes the Property name as the name argument and the new value as the value
        argument, then requests from the underlying platform and the Protocol Bindings
        to update the Property on the remote Thing and return the result.
        Returns a Future that resolves on success or rejects with an Error."""

        client = self.servient.select_client(self.td, name)
        client_kwargs = client_kwargs if client_kwargs else {}

        await client.write_property(
            self.td,
            name,
            value,
            timeout=timeout,
            **client_kwargs.get(client.protocol, {})
        )

    async def read_property(self, name, timeout=None, client_kwargs=None):
        """Takes the Property name as the name argument, then requests from the
        underlying platform and the Protocol Bindings to retrieve the Property
        on the remote Thing and return the result.
        Returns a Future that resolves with the Property value or rejects with an Error.
        """

        client = self.servient.select_client(self.td, name)
        client_kwargs = client_kwargs if client_kwargs else {}

        value = await client.read_property(
            self.td, name, timeout=timeout, **client_kwargs.get(client.protocol, {})
        )

        return value

    def _find_form(self, operation):
        """Returns the first Thing form supporting the given operation."""

        return next(
            (
                form for form in (self.td.forms or [])
                if operation in (
                    form.op if isinstance(form.op, (list, tuple)) else [form.op]
                )
            ),
            None
        )

    async def read_all_properties(self, options=None):
        """Reads all readable Properties and returns their values by name."""

        names = [
            name for name, prop in self.td.properties.items() if not prop.write_only
        ]
        if not names:
            return {}
        client = self.servient.select_client(self.td, names[0])
        form = self._find_form(InteractionVerbs.READ_ALL_PROPERTIES)
        method = getattr(client, "read_all_properties", None)
        if form and method:
            return await method(
                self.td, timeout=(options or {}).get("timeout"),
                options=options, form=form
            )

        form = self._find_form(InteractionVerbs.READ_MULTIPLE_PROPERTIES)
        method = getattr(client, "read_multiple_properties", None)
        if form and method:
            return await method(
                self.td, names, timeout=(options or {}).get("timeout"),
                options=options, form=form
            )

        return await self._read_properties_individually(names, options)

    async def read_multiple_properties(self, property_names, options=None):
        """Reads the named Properties and returns their values by name."""

        names = list(property_names)
        if any(name not in self.td.properties for name in names):
            raise KeyError("Unknown property")
        if any(self.td.properties[name].write_only for name in names):
            raise PermissionError("Cannot read a write-only property")
        if not names:
            return {}

        client = self.servient.select_client(self.td, names[0])
        form = self._find_form(InteractionVerbs.READ_MULTIPLE_PROPERTIES)
        method = getattr(client, "read_multiple_properties", None)
        if form and method:
            return await method(
                self.td, names, timeout=(options or {}).get("timeout"),
                options=options, form=form
            )

        return await self._read_properties_individually(names, options)

    async def _read_properties_individually(self, names, options):
        """Reads Properties individually when the client has no collection form."""

        values = await asyncio.gather(
            *(self.read_property(name, timeout=(options or {}).get("timeout"),
                                 client_kwargs=options) for name in names)
        )
        return dict(zip(names, values))

    async def write_multiple_properties(self, values, options=None):
        """Writes the supplied Property values."""

        if not isinstance(values, dict):
            raise TypeError("Property values must be a dictionary")
        if any(name not in self.td.properties for name in values):
            raise KeyError("Unknown property")
        if any(self.td.properties[name].read_only for name in values):
            raise PermissionError("Cannot write a read-only property")

        names = list(values)
        if not values:
            return
        client = self.servient.select_client(self.td, names[0])
        form = self._find_form(InteractionVerbs.WRITE_MULTIPLE_PROPERTIES)
        method = getattr(client, "write_multiple_properties", None)
        if form and method:
            return await method(
                self.td, values, timeout=(options or {}).get("timeout"),
                options=options, form=form
            )
        await asyncio.gather(
            *(self.write_property(name, value, timeout=(options or {}).get("timeout"),
                                 client_kwargs=options)
              for name, value in values.items())
        )

    async def write_all_properties(self, values, options=None):
        """Writes values for all writable Properties."""

        if not isinstance(values, dict):
            raise TypeError("Property values must be a dictionary")
        expected = {
            name for name, prop in self.td.properties.items() if not prop.read_only
        }
        if set(values) != expected:
            raise ValueError("All writable property values are required")
        if not values:
            return

        names = list(values)
        client = self.servient.select_client(self.td, names[0])
        form = self._find_form(InteractionVerbs.WRITE_ALL_PROPERTIES)
        method = getattr(client, "write_all_properties", None)
        if form and method:
            return await method(
                self.td, values, timeout=(options or {}).get("timeout"),
                options=options, form=form
            )

        form = self._find_form(InteractionVerbs.WRITE_MULTIPLE_PROPERTIES)
        method = getattr(client, "write_multiple_properties", None)
        if form and method:
            return await method(
                self.td, values, timeout=(options or {}).get("timeout"),
                options=options, form=form
            )

        await asyncio.gather(
            *(self.write_property(
                name, value, timeout=(options or {}).get("timeout"),
                client_kwargs=options
            ) for name, value in values.items())
        )

    def on_event(self, name, client_kwargs=None):
        """Returns an Observable for the Event specified in the name argument,
        allowing subscribing to and unsubscribing from notifications."""

        client = self.servient.select_client(self.td, name)
        client_kwargs = client_kwargs if client_kwargs else {}

        return client.on_event(self.td, name, **client_kwargs.get(client.protocol, {}))

    def on_property_change(self, name, client_kwargs=None):
        """Returns an Observable for the Property specified in the name argument,
        allowing subscribing to and unsubscribing from notifications."""

        client = self.servient.select_client(self.td, name)
        client_kwargs = client_kwargs if client_kwargs else {}

        return client.on_property_change(
            self.td, name, **client_kwargs.get(client.protocol, {})
        )

    def on_td_change(self):
        """Returns an Observable, allowing subscribing to and unsubscribing
        from notifications to the Thing Description."""

        raise NotImplementedError()

    @property
    def properties(self):
        """Returns a dictionary of ThingProperty items."""

        return ConsumedThingPropertyDict(consumed_thing=self)

    @property
    def actions(self):
        """Returns a dictionary of ThingAction items."""

        return ConsumedThingActionDict(consumed_thing=self)

    @property
    def events(self):
        """Returns a dictionary of ThingEvent items."""

        return ConsumedThingEventDict(consumed_thing=self)

    @property
    def links(self):
        """Represents a dictionary of WebLink items."""

        raise NotImplementedError()

    def subscribe(self, *args, **kwargs):
        """Subscribes to changes on the TD of this thing."""

        observable = self.on_td_change()
        loop = ioloop.IOLoop.current()
        scheduler = IOLoopScheduler(loop)
        kwargs["scheduler"] = scheduler

        return observable.subscribe(*args, **kwargs)
