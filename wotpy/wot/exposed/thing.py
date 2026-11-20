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
Classes that represent Things exposed by a servient.
"""
import asyncio

import reactivex
from reactivex.scheduler.eventloop import IOLoopScheduler
from reactivex.subject import Subject
from reactivex import operators as ops
from tornado import ioloop

from wotpy.utils.enums import EnumListMixin
from wotpy.utils.utils import to_camel
from wotpy.wot.dictionaries.interaction import PropertyFragmentDict, ActionFragmentDict, EventFragmentDict
from wotpy.wot.enums import DefaultThingEvent, TDChangeMethod, TDChangeType
from wotpy.wot.events import (
    EmittedEvent,
    PropertyChangeEmittedEvent,
    ThingDescriptionChangeEmittedEvent,
    ActionInvocationEmittedEvent,
    PropertyChangeEventInit,
    ActionInvocationEventInit,
    ThingDescriptionChangeEventInit
)
from wotpy.wot.exposed.interaction_map import (
    ExposedThingEventDict,
    ExposedThingActionDict,
    ExposedThingPropertyDict
)
from wotpy.wot.interaction import Property, Action, Event
from wotpy.wot.td import ThingDescription
from wotpy.wot.thing import Thing


class ExposedThing:
    """An entity that serves to define the behavior of a Thing.
    An application uses this class when it acts as the Thing 'server'."""

    class HandlerKeys(EnumListMixin):
        """Enumeration of handler keys."""

        RETRIEVE_PROPERTY = "retrieve_property"
        UPDATE_PROPERTY = "update_property"
        INVOKE_ACTION = "invoke_action"
        OBSERVE = "observe"

    class InteractionStateKeys(EnumListMixin):
        """Enumeration of interaction state keys."""

        PROPERTY_VALUES = "property_values"

    def __init__(self, servient, thing):
        self._servient = servient
        self._thing = thing

        self._interaction_states = {self.InteractionStateKeys.PROPERTY_VALUES: {}}

        self._handlers_global = {
            self.HandlerKeys.RETRIEVE_PROPERTY: self._default_retrieve_property_handler,
            self.HandlerKeys.UPDATE_PROPERTY: self._default_update_property_handler,
            self.HandlerKeys.INVOKE_ACTION: self._default_invoke_action_handler
        }

        self._handlers = {
            self.HandlerKeys.RETRIEVE_PROPERTY: {},
            self.HandlerKeys.UPDATE_PROPERTY: {},
            self.HandlerKeys.INVOKE_ACTION: {}
        }

        self._events_stream = Subject()

    def __str__(self):
        return "<{}> {}".format(self.__class__.__name__, self.id)

    def __eq__(self, other):
        return self.servient == other.servient and self.thing == other.thing

    def __hash__(self):
        return hash((self.servient, self.thing))

    def __getattr__(self, name):
        """Search for members that raised an AttributeError in
        the private Thing instance before propagating the exception."""

        return getattr(self.thing, name)

    def __setattr__(self, name, value):
        """Setter for ThingFragment attributes."""

        name_camel = to_camel(name)

        if name_camel not in Thing.THING_FRAGMENT_WRITABLE_FIELDS:
            return super().__setattr__(name, value)

        return self._thing.__setattr__(name, value)

    def _set_property_value(self, prop, value):
        """Sets a Property value."""

        prop_values = self.InteractionStateKeys.PROPERTY_VALUES
        self._interaction_states[prop_values][prop] = value

    def _get_property_value(self, prop):
        """Returns a Property value."""

        prop_values = self.InteractionStateKeys.PROPERTY_VALUES
        return self._interaction_states[prop_values].get(prop, None)

    def _set_handler(self, handler_type, handler, interaction=None):
        """Sets the currently defined handler for the given handler type."""

        if interaction is None or handler_type not in self._handlers:
            self._handlers_global[handler_type] = handler
        else:
            self._handlers[handler_type][interaction] = handler

    def _get_handler(self, handler_type, interaction=None):
        """Returns the currently defined handler for the given handler type."""

        interaction_handler = self._handlers.get(handler_type, {}).get(
            interaction, None
        )

        return interaction_handler or self._handlers_global[handler_type]

    def _find_interaction(self, name):
        """Raises ValueError if the given interaction does not exist in this Thing."""

        interaction = self._thing.find_interaction(name=name)

        if not interaction:
            raise ValueError("Interaction not found: {}".format(name))

        return interaction

    def _default_retrieve_property_handler(self, property_name):
        """Default handler for property reads."""

        loop = asyncio.get_running_loop()
        future_read = loop.create_future()
        prop = self._find_interaction(name=property_name)
        prop_value = self._get_property_value(prop)
        future_read.set_result(prop_value)

        return future_read

    def _default_update_property_handler(self, property_name, value):
        """Default handler for onUpdateProperty."""

        loop = asyncio.get_running_loop()
        future_write = loop.create_future()
        prop = self._find_interaction(name=property_name)
        self._set_property_value(prop, value)
        future_write.set_result(None)

        return future_write

    def _default_invoke_action_handler(self, parameters):
        """Default handler for onInvokeAction."""

        loop = asyncio.get_running_loop()
        future_invoke = loop.create_future()
        future_invoke.set_exception(NotImplementedError("Undefined action handler"))

        return future_invoke

    @property
    def id(self):
        """Returns the ID of the Thing."""

        return self.thing.id

    @property
    def title(self):
        """Returns the title of the Thing."""

        return self.thing.title

    @property
    def servient(self):
        """Servient that contains this ExposedThing."""

        return self._servient

    @property
    def thing(self):
        """Returns the object that represents the Thing beneath this ExposedThing."""

        return self._thing

    @property
    def properties(self):
        """Returns a dictionary of ThingProperty items."""

        return ExposedThingPropertyDict(exposed_thing=self)

    @property
    def actions(self):
        """Returns a dictionary of ThingAction items."""

        return ExposedThingActionDict(exposed_thing=self)

    @property
    def events(self):
        """Returns a dictionary of ThingEvent items."""

        return ExposedThingEventDict(exposed_thing=self)

    def _emit_property_change_event(self, name, value):
        """Emits a property change event."""

        event_init = PropertyChangeEventInit(name=name, value=value)
        emitted_event = PropertyChangeEmittedEvent(init=event_init)

        self._events_stream.on_next(emitted_event)

    async def read_property(self, name):
        """Takes the Property name as the name argument, then requests from
        the underlying platform and the Protocol Bindings to retrieve the
        Property on the remote Thing and return the result. Returns a Future
        that resolves with the Property value or rejects with an Error."""

        proprty = self.thing.properties[name]

        handler = self._handlers.get(self.HandlerKeys.RETRIEVE_PROPERTY, {}).get(proprty, None)

        if handler:
            value = await handler()
        else:
            value = await self._default_retrieve_property_handler(name)

        return value

    async def read_all_properties(self):
        """Reads all properties of the Thing and returns a dictionary of property names and values."""

        return await self.handle_read_all_properties()

    async def handle_read_all_properties(self):
        """Reads every property that is exposed for external reading."""

        names = [
            name for name, prop in self.thing.properties.items()
            if not prop.data_schema.write_only
        ]
        return await self.handle_read_multiple_properties(names)

    async def handle_read_multiple_properties(self, property_names):
        """Reads a validated collection of externally readable properties."""

        if not isinstance(property_names, (list, tuple)):
            raise TypeError("Property names must be a list")

        names = list(property_names)
        if len(set(names)) != len(names):
            raise ValueError("Property names must be unique")

        properties = {}
        for name in names:
            prop = self.thing.properties.get(name)
            if prop is None:
                raise KeyError("Unknown property: {}".format(name))
            if prop.data_schema.write_only:
                raise PermissionError("Property is write-only: {}".format(name))
            properties[name] = await self.read_property(name)
        return properties

    async def handle_write_all_properties(self, values):
        """Updates all properties using values supplied by an external request."""

        if not isinstance(values, dict):
            raise TypeError("Property values must be a dictionary")

        names = [
            name for name, prop in self.thing.properties.items()
            if prop.writable
        ]
        if set(values) != set(names):
            raise ValueError("All writable property values are required")
        await self.handle_write_multiple_properties(values)

    async def handle_write_multiple_properties(self, values):
        """Updates a validated collection of externally writable properties."""

        if not isinstance(values, dict):
            raise TypeError("Property values must be a dictionary")
        for name, value in values.items():
            await self.handle_write_property(name, value)

    async def handle_write_property(self, name, value):
        """Function that gets called from protocol servers to handle external write
        requests. In contrast to internal writes that are allowed on readOnly properties,
        external property writes fail."""

        proprty = self.properties[name]

        if not proprty.writable:
            raise TypeError("Property is non-writable")

        await proprty.write(value)

    async def write_property(self, name, value):
        """Takes the Property name as the name argument and the new value as the
        value argument, then requests from the underlying platform and the Protocol
        Bindings to update the Property on the remote Thing and return the result.
        Returns a Future that resolves on success or rejects with an Error."""

        proprty = self.thing.properties[name]

        handler = self._handlers.get(self.HandlerKeys.UPDATE_PROPERTY, {}).get(proprty, None)

        if handler:
            await handler(value)
        else:
            await self._default_update_property_handler(name, value)

        self._emit_property_change_event(name, value)

    async def invoke_action(self, name, input_value=None):
        """Invokes an Action with the given parameters and yields with the invocation result."""

        action = self.thing.actions[name]

        handler = self._get_handler(
            handler_type=self.HandlerKeys.INVOKE_ACTION,
            interaction=action)

        result = await handler(input_value)

        event_init = ActionInvocationEventInit(action_name=name, return_value=result)
        emitted_event = ActionInvocationEmittedEvent(init=event_init)

        self._events_stream.on_next(emitted_event)

        return result

    def on_event(self, name):
        """Returns an Observable for the Event specified in the name argument,
        allowing subscribing to and unsubscribing from notifications."""

        if name not in self.thing.events:
            return reactivex.throw(Exception("Unknown event"))

        def event_filter(item):
            return item.name == name

        return self._events_stream.pipe(ops.filter(event_filter))

    def on_property_change(self, name):
        """Returns an Observable for the Property specified in the name argument,
        allowing subscribing to and unsubscribing from notifications."""

        try:
            interaction = self._find_interaction(name=name)
        except ValueError:
            return reactivex.throw(Exception("Unknown property"))

        if not interaction.observable:
            return reactivex.throw(Exception("Property is not observable"))

        def property_change_filter(item):
            return (
                item.name == DefaultThingEvent.PROPERTY_CHANGE
                and item.data.name == name
            )

        return self._events_stream.pipe(ops.filter(property_change_filter))

    def on_td_change(self):
        """Returns an Observable, allowing subscribing to and unsubscribing
        from notifications to the Thing Description."""

        def td_change_filter(item):
            return item.name == DefaultThingEvent.DESCRIPTION_CHANGE

        return self._events_stream.pipe(ops.filter(td_change_filter))

    def expose(self):
        """Start serving external requests for the Thing, so that
        WoT interactions using Properties, Actions and Events will be possible."""

        self._servient.enable_exposed_thing(self.thing.title)

    def destroy(self):
        """Stop serving external requests for the Thing and destroy the object.
        Note that eventual unregistering should be done before invoking this method."""

        self._servient.remove_exposed_thing(self.thing.title)

    def emit_event(self, event_name, payload):
        """Emits an the event initialized with the event name specified by
        the event_name argument and data specified by the payload argument."""

        if not self.thing.find_interaction(name=event_name):
            raise ValueError("Unknown event: {}".format(event_name))

        event = EmittedEvent(name=event_name, init=payload)

        self._events_stream.on_next(event)

    def add_property(self, name, property_init, value=None):
        """Adds a Property defined by the argument and updates the Thing Description.
        Takes an instance of ThingPropertyInit as argument."""

        if isinstance(property_init, dict):
            property_init = PropertyFragmentDict(property_init)

        prop = Property(thing=self._thing, name=name, init_dict=property_init)

        self._thing.add_interaction(prop)
        self._set_property_value(prop, value)

        event_data = ThingDescriptionChangeEventInit(
            td_change_type=TDChangeType.PROPERTY,
            method=TDChangeMethod.ADD,
            name=name,
            data=property_init.to_dict(),
            description=ThingDescription.from_thing(self.thing).to_dict()
        )

        event = ThingDescriptionChangeEmittedEvent(init=event_data)

        self._events_stream.on_next(event)

    def remove_property(self, name):
        """Removes the Property specified by the name argument,
        updates the Thing Description and returns the object."""

        self._thing.remove_interaction(name=name)

        event_data = ThingDescriptionChangeEventInit(
            td_change_type=TDChangeType.PROPERTY,
            method=TDChangeMethod.REMOVE,
            name=name
        )

        event = ThingDescriptionChangeEmittedEvent(init=event_data)

        self._events_stream.on_next(event)

    def add_action(self, name, action_init, action_handler=None):
        """Adds an Action to the Thing object as defined by the action
        argument of type ThingActionInit and updates the Thing Description."""

        if isinstance(action_init, dict):
            action_init = ActionFragmentDict(action_init)

        action = Action(thing=self._thing, name=name, init_dict=action_init)

        self._thing.add_interaction(action)

        event_data = ThingDescriptionChangeEventInit(
            td_change_type=TDChangeType.ACTION,
            method=TDChangeMethod.ADD,
            name=name,
            data=action_init.to_dict(),
            description=ThingDescription.from_thing(self.thing).to_dict()
        )

        event = ThingDescriptionChangeEmittedEvent(init=event_data)

        self._events_stream.on_next(event)

        if action_handler:
            self.set_action_handler(name, action_handler)

    def remove_action(self, name):
        """Removes the Action specified by the name argument,
        updates the Thing Description and returns the object."""

        self._thing.remove_interaction(name=name)

        event_data = ThingDescriptionChangeEventInit(
            td_change_type=TDChangeType.ACTION,
            method=TDChangeMethod.REMOVE,
            name=name
        )

        event = ThingDescriptionChangeEmittedEvent(init=event_data)

        self._events_stream.on_next(event)

    def add_event(self, name, event_init):
        """Adds an event to the Thing object as defined by the event argument
        of type ThingEventInit and updates the Thing Description."""

        if isinstance(event_init, dict):
            event_init = EventFragmentDict(event_init)

        event = Event(thing=self._thing, name=name, init_dict=event_init)

        self._thing.add_interaction(event)

        event_data = ThingDescriptionChangeEventInit(
            td_change_type=TDChangeType.EVENT,
            method=TDChangeMethod.ADD,
            name=name,
            data=event_init.to_dict(),
            description=ThingDescription.from_thing(self.thing).to_dict()
        )

        event = ThingDescriptionChangeEmittedEvent(init=event_data)

        self._events_stream.on_next(event)

    def remove_event(self, name):
        """Removes the event specified by the name argument,
        updates the Thing Description and returns the object."""

        self._thing.remove_interaction(name=name)

        event_data = ThingDescriptionChangeEventInit(
            td_change_type=TDChangeType.EVENT,
            method=TDChangeMethod.REMOVE,
            name=name
        )

        event = ThingDescriptionChangeEmittedEvent(init=event_data)

        self._events_stream.on_next(event)

    def set_action_handler(self, name, action_handler):
        """Takes name as string argument and action_handler as argument of type ActionHandler.
        Sets the handler function for the specified Action matched by name.
        Throws on error. Returns a reference to the same object for supporting chaining.
        """

        action = self.thing.actions[name]

        self._set_handler(
            handler_type=self.HandlerKeys.INVOKE_ACTION,
            handler=action_handler,
            interaction=action
        )

        return self

    def set_property_read_handler(self, name, read_handler):
        """Takes name as string argument and read_handler as argument of type PropertyReadHandler.
        Sets the handler function for reading the specified Property matched by name.
        Throws on error. Returns a reference to the same object for supporting chaining.
        """

        proprty = self.thing.properties[name]

        self._set_handler(
            handler_type=self.HandlerKeys.RETRIEVE_PROPERTY,
            handler=read_handler,
            interaction=proprty
        )

        return self

    def set_property_write_handler(self, name, write_handler):
        """Takes name as string argument and write_handler as argument of type PropertyWriteHandler.
        Sets the handler function for writing the specified Property matched by name.
        Throws on error. Returns a reference to the same object for supporting chaining.
        """

        proprty = self.thing.properties[name]

        self._set_handler(
            handler_type=self.HandlerKeys.UPDATE_PROPERTY,
            handler=write_handler,
            interaction=proprty
        )

        return self

    def subscribe(self, *args, **kwargs):
        """Subscribes to changes on the TD of this thing."""

        observable = self.on_td_change()
        loop = ioloop.IOLoop.current()
        scheduler = IOLoopScheduler(loop)
        kwargs["scheduler"] = scheduler

        return observable.subscribe(*args, **kwargs)
