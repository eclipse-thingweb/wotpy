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

import asyncio
import uuid

from faker import Faker
import pytest
from reactivex.scheduler.eventloop import IOLoopScheduler
from tornado import ioloop

from tests.utils import find_free_port, run_test_coroutine
from wotpy.protocols.http.client import HTTPClient
from wotpy.protocols.http.server import HTTPServer
from wotpy.protocols.ws.client import WebsocketClient
from wotpy.protocols.ws.server import WebsocketServer
from wotpy.wot.constants import WOT_TD_CONTEXT_URL_V1_1
from wotpy.wot.servient import Servient
from wotpy.wot.td import ThingDescription


async def _test_property_change_events(exposed_thing, subscribe_func):
    """Helper function to test client subscriptions to property change events."""

    async def test_coroutine():
        td = ThingDescription.from_thing(exposed_thing.thing)
        prop_name = next(iter(td.properties.keys()))

        loop = asyncio.get_running_loop()
        future_conn = loop.create_future()
        future_change = loop.create_future()

        prop_value = Faker().sentence()

        def on_next(ev):
            if not future_conn.done():
                future_conn.set_result(True)
                return

            if ev.data.value == prop_value:
                future_change.set_result(True)

        subscription = subscribe_func(prop_name, on_next)

        while not future_conn.done():
            await asyncio.sleep(0)
            await exposed_thing.write_property(prop_name, Faker().sentence())

        await exposed_thing.write_property(prop_name, prop_value)

        await future_change

        assert future_change.result()

        subscription.dispose()

    await run_test_coroutine(test_coroutine)


async def _test_event_emission_events(exposed_thing, subscribe_func):
    """Helper function to test client subscription to event emissions."""

    async def test_coroutine():
        td = ThingDescription.from_thing(exposed_thing.thing)
        event_name = next(iter(td.events.keys()))

        loop = asyncio.get_running_loop()
        future_conn = loop.create_future()
        future_event = loop.create_future()

        payload = Faker().sentence()

        def on_next(ev):
            if not future_conn.done():
                future_conn.set_result(True)
                return

            if ev.data == payload:
                future_event.set_result(True)

        subscription = subscribe_func(event_name, on_next)

        while not future_conn.done():
            await asyncio.sleep(0)
            exposed_thing.emit_event(event_name, Faker().sentence())

        exposed_thing.emit_event(event_name, payload)

        await future_event

        assert future_event.result()

        subscription.dispose()

    await run_test_coroutine(test_coroutine)


def test_thing_template_getters(consumed_exposed_pair):
    """ThingTemplate properties can be accessed from the ConsumedThing."""

    consumed_thing = consumed_exposed_pair.pop("consumed_thing")
    thing_template = consumed_thing.td.to_thing_fragment()

    assert consumed_thing.id == thing_template.id
    assert consumed_thing.title == thing_template.title
    assert consumed_thing.description == thing_template.description


@pytest.mark.asyncio
async def test_read_property(consumed_exposed_pair):
    """A ConsumedThing is able to read properties."""

    consumed_thing = consumed_exposed_pair.pop("consumed_thing")
    exposed_thing = consumed_exposed_pair.pop("exposed_thing")

    async def test_coroutine():
        prop_name = next(iter(consumed_thing.td.properties.keys()))

        result_exposed = await exposed_thing.read_property(prop_name)
        result_consumed = await consumed_thing.read_property(prop_name)

        assert result_consumed == result_exposed

    await run_test_coroutine(test_coroutine)


@pytest.mark.asyncio
async def test_read_property_collections(consumed_exposed_pair):
    """A ConsumedThing can read all or selected properties."""

    consumed_thing = consumed_exposed_pair.pop("consumed_thing")
    exposed_thing = consumed_exposed_pair.pop("exposed_thing")

    async def test_coroutine():
        names = list(consumed_thing.td.properties)
        assert await consumed_thing.read_all_properties() == (
            await exposed_thing.read_all_properties()
        )
        assert await consumed_thing.read_multiple_properties(names) == {
            name: await exposed_thing.read_property(name) for name in names
        }

    await run_test_coroutine(test_coroutine)


@pytest.mark.asyncio
async def test_write_property(consumed_exposed_pair):
    """A ConsumedThing is able to write properties."""

    consumed_thing = consumed_exposed_pair.pop("consumed_thing")
    exposed_thing = consumed_exposed_pair.pop("exposed_thing")

    async def test_coroutine():
        prop_name = next(iter(consumed_thing.td.properties.keys()))

        val_01 = Faker().sentence()
        val_02 = Faker().sentence()

        await exposed_thing.write_property(prop_name, val_01)
        value = await exposed_thing.read_property(prop_name)

        assert value == val_01

        await consumed_thing.write_property(prop_name, val_02)
        value = await exposed_thing.read_property(prop_name)

        assert value == val_02

    await run_test_coroutine(test_coroutine)


@pytest.mark.asyncio
async def test_write_property_collections(consumed_exposed_pair):
    """A ConsumedThing can write all or selected properties."""

    consumed_thing = consumed_exposed_pair.pop("consumed_thing")
    exposed_thing = consumed_exposed_pair.pop("exposed_thing")

    async def test_coroutine():
        names = [
            name for name, prop in consumed_thing.td.properties.items()
            if not prop.read_only
        ]
        initial_values = await exposed_thing.read_all_properties()
        values = {name: Faker().sentence() for name in names}
        await consumed_thing.write_multiple_properties(values)
        assert await exposed_thing.read_all_properties() == {
            **initial_values,
            **values,
        }

        initial_values = await exposed_thing.read_all_properties()
        values = {name: Faker().sentence() for name in names}
        await consumed_thing.write_all_properties(values)
        assert await exposed_thing.read_all_properties() == {
            **initial_values,
            **values,
        }

    await run_test_coroutine(test_coroutine)


@pytest.mark.asyncio
async def test_invoke_action(consumed_exposed_pair):
    """A ConsumedThing is able to invoke actions."""

    consumed_thing = consumed_exposed_pair.pop("consumed_thing")
    exposed_thing = consumed_exposed_pair.pop("exposed_thing")

    async def test_coroutine():
        action_name = next(iter(consumed_thing.td.actions.keys()))

        input_value = Faker().pystr()
        result = await consumed_thing.invoke_action(action_name, input_value)
        result_expected = await exposed_thing.invoke_action(action_name, input_value)

        assert result == result_expected

    await run_test_coroutine(test_coroutine)


@pytest.mark.asyncio
async def test_on_event(consumed_exposed_pair):
    """A ConsumedThing is able to observe events."""

    consumed_thing = consumed_exposed_pair.pop("consumed_thing")
    exposed_thing = consumed_exposed_pair.pop("exposed_thing")

    def subscribe_func(event_name, on_next):
        observable = consumed_thing.on_event(event_name)
        loop = ioloop.IOLoop.current()
        scheduler = IOLoopScheduler(loop)
        return observable.subscribe(on_next, scheduler=scheduler)

    await _test_event_emission_events(exposed_thing, subscribe_func)


@pytest.mark.asyncio
async def test_on_property_change(consumed_exposed_pair):
    """A ConsumedThing is able to observe property updates."""

    consumed_thing = consumed_exposed_pair.pop("consumed_thing")
    exposed_thing = consumed_exposed_pair.pop("exposed_thing")

    def subscribe_func(prop_name, on_next):
        observable = consumed_thing.on_property_change(prop_name)
        loop = ioloop.IOLoop.current()
        scheduler = IOLoopScheduler(loop)
        return observable.subscribe(on_next, scheduler=scheduler)

    await _test_property_change_events(exposed_thing, subscribe_func)


@pytest.mark.asyncio
async def test_thing_property_get(consumed_exposed_pair):
    """Property values can be retrieved on ConsumedThings using the map-like interface."""

    consumed_thing = consumed_exposed_pair.pop("consumed_thing")
    exposed_thing = consumed_exposed_pair.pop("exposed_thing")

    async def test_coroutine():
        prop_name = next(iter(consumed_thing.td.properties.keys()))

        result_exposed = await exposed_thing.read_property(prop_name)
        result_consumed = await consumed_thing.properties[prop_name].read()

        assert result_consumed == result_exposed

    await run_test_coroutine(test_coroutine)


@pytest.mark.asyncio
async def test_thing_property_set(consumed_exposed_pair):
    """Property values can be updated on ConsumedThings using the map-like interface."""

    consumed_thing = consumed_exposed_pair.pop("consumed_thing")
    exposed_thing = consumed_exposed_pair.pop("exposed_thing")

    async def test_coroutine():
        prop_name = next(iter(consumed_thing.td.properties.keys()))
        updated_value = Faker().sentence()
        curr_value = await exposed_thing.read_property(prop_name)

        assert consumed_thing.td.properties[prop_name].writable
        assert curr_value != updated_value

        await consumed_thing.properties[prop_name].write(updated_value)
        result_exposed = await exposed_thing.read_property(prop_name)

        assert result_exposed == updated_value

    await run_test_coroutine(test_coroutine)


@pytest.mark.asyncio
async def test_thing_property_subscribe(consumed_exposed_pair):
    """Property updates can be observed on ConsumedThings using the map-like interface."""

    consumed_thing = consumed_exposed_pair.pop("consumed_thing")
    exposed_thing = consumed_exposed_pair.pop("exposed_thing")

    def subscribe_func(prop_name, on_next):
        return consumed_thing.properties[prop_name].subscribe(on_next)

    await _test_property_change_events(exposed_thing, subscribe_func)


@pytest.mark.asyncio
async def test_thing_property_getters(consumed_exposed_pair):
    """ThingProperty retrieved from ConsumedThing expose the attributes
    from the Interaction, InteractionFragment and PropertyFragment interfaces."""

    consumed_thing = consumed_exposed_pair.pop("consumed_thing")
    exposed_thing = consumed_exposed_pair.pop("exposed_thing")

    async def test_coroutine():
        prop_name = next(iter(consumed_thing.td.properties.keys()))
        thing_prop_con = consumed_thing.properties[prop_name]
        thing_prop_exp = exposed_thing.properties[prop_name]

        assert len(thing_prop_con.forms) == 0
        assert thing_prop_con.title == thing_prop_exp.title
        assert thing_prop_con.description == thing_prop_exp.description
        assert thing_prop_con.observable == thing_prop_exp.observable
        assert thing_prop_con.type == thing_prop_exp.type

    await run_test_coroutine(test_coroutine)


@pytest.mark.asyncio
async def test_thing_action_run(consumed_exposed_pair):
    """Actions can be invoked on ConsumedThings using the map-like interface."""

    consumed_thing = consumed_exposed_pair.pop("consumed_thing")
    exposed_thing = consumed_exposed_pair.pop("exposed_thing")

    async def test_coroutine():
        action_name = next(iter(consumed_thing.td.actions.keys()))

        input_value = Faker().pystr()
        result = await consumed_thing.actions[action_name].invoke(input_value)
        result_expected = await exposed_thing.invoke_action(action_name, input_value)

        assert result == result_expected

    await run_test_coroutine(test_coroutine)


@pytest.mark.asyncio
async def test_thing_action_getters(consumed_exposed_pair):
    """ThingAction retrieved from ConsumedThing expose the attributes
    from the Interaction, InteractionFragment and ActionFragment interfaces."""

    consumed_thing = consumed_exposed_pair.pop("consumed_thing")
    exposed_thing = consumed_exposed_pair.pop("exposed_thing")

    async def test_coroutine():
        action_name = next(iter(consumed_thing.td.actions.keys()))
        thing_action_con = consumed_thing.actions[action_name]
        thing_action_exp = exposed_thing.actions[action_name]

        assert len(thing_action_con.forms) == 0
        assert thing_action_con.title == thing_action_exp.title
        assert thing_action_con.description == thing_action_exp.description
        assert thing_action_con.input.type == thing_action_exp.input.type
        assert thing_action_con.output.type == thing_action_exp.output.type

    await run_test_coroutine(test_coroutine)


@pytest.mark.asyncio
async def test_thing_event_subscribe(consumed_exposed_pair):
    """Property updates can be observed on ConsumedThings using the map-like interface."""

    consumed_thing = consumed_exposed_pair.pop("consumed_thing")
    exposed_thing = consumed_exposed_pair.pop("exposed_thing")

    def subscribe_func(event_name, on_next):
        return consumed_thing.events[event_name].subscribe(on_next)

    await _test_event_emission_events(exposed_thing, subscribe_func)


@pytest.mark.asyncio
async def test_thing_event_getters(consumed_exposed_pair):
    """ThingEvent retrieved from ConsumedThing expose the attributes
    from the Interaction, InteractionFragment and EventFragment interfaces."""

    consumed_thing = consumed_exposed_pair.pop("consumed_thing")
    exposed_thing = consumed_exposed_pair.pop("exposed_thing")

    async def test_coroutine():
        event_name = next(iter(consumed_thing.td.events.keys()))
        thing_event_con = consumed_thing.events[event_name]
        thing_event_exp = exposed_thing.events[event_name]

        assert len(thing_event_con.forms) == 0
        assert thing_event_con.title == thing_event_exp.title
        assert thing_event_con.description == thing_event_exp.description
        assert thing_event_con.data.type == thing_event_exp.data.type

    await run_test_coroutine(test_coroutine)


def test_thing_interaction_dict_behaviour(consumed_exposed_pair):
    """The Interactions dict-like interface of a ConsumedThing behaves like a dict."""

    consumed_thing = consumed_exposed_pair.pop("consumed_thing")

    prop_name = next((key for key in consumed_thing.properties), None)

    assert prop_name
    assert len(consumed_thing.properties) > 0
    assert prop_name in consumed_thing.properties


@pytest.mark.asyncio
async def test_consumed_client_protocols_preference():
    """The Servient selects different protocol clients to consume Things
    depending on the protocol choices displayed on the Thing Description."""

    servient = Servient(catalogue_port=None)

    async def servient_start():
        return (await servient.start())

    async def servient_shutdown():
        await servient.shutdown()

    http_port = find_free_port()
    http_server = HTTPServer(port=http_port)

    servient.add_server(http_server)

    ws_port = find_free_port()
    ws_server = WebsocketServer(port=ws_port)

    servient.add_server(ws_server)

    client_server_map = {
        HTTPClient: http_server,
        WebsocketClient: ws_server
    }

    wot = await servient_start()

    prop_name = uuid.uuid4().hex

    td_produce = ThingDescription({
        "@context": [
            WOT_TD_CONTEXT_URL_V1_1,
        ],
        "id": uuid.uuid4().urn,
        "title": uuid.uuid4().hex,
        "securityDefinitions": {
            "nosec_sc":{
                "scheme":"nosec"
            }
        },
        "security": "nosec_sc",
        "properties": {
            prop_name: {
                "observable": True,
                "type": "string"
            }
        }
    })

    exposed_thing = wot.produce(td_produce.to_str())
    exposed_thing.expose()

    td_forms_all = ThingDescription.from_thing(exposed_thing.thing)

    client_01 = servient.select_client(td_forms_all, prop_name)
    client_01_class = client_01.__class__

    assert client_01_class in client_server_map.keys()

    await servient_shutdown()
    servient.remove_server(client_server_map[client_01_class].protocol)
    await servient_start()

    td_forms_removed = ThingDescription.from_thing(exposed_thing.thing)

    client_02 = servient.select_client(td_forms_removed, prop_name)
    client_02_class = client_02.__class__

    assert client_02_class != client_01_class
    assert client_02_class in client_server_map.keys()

    await servient_shutdown()
