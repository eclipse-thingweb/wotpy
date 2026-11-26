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
import random
import uuid

from faker import Faker
from reactivex.scheduler.eventloop import IOLoopScheduler
from tornado import ioloop

from tests.utils import run_test_coroutine
from wotpy.wot.dictionaries.interaction import PropertyFragmentDict, EventFragmentDict, ActionFragmentDict
from wotpy.wot.td import ThingDescription


async def client_test_on_property_change(servient, protocol_client_cls):
    """Helper function to test observation of Property updates on bindings clients."""

    exposed_thing = next(servient.exposed_things)
    prop_name = uuid.uuid4().hex

    exposed_thing.add_property(
        prop_name,
        PropertyFragmentDict({"type": "string", "observable": True}),
        value=Faker().sentence()
    )

    servient.refresh_forms()

    td = ThingDescription.from_thing(exposed_thing.thing)

    async def test_coroutine():
        protocol_client = protocol_client_cls()

        values = [Faker().sentence() for _ in range(10)]
        loop = asyncio.get_running_loop()
        values_observed = {value: loop.create_future() for value in values}

        async def periodic_write_next():
            while True:
                try:
                    next_value = next(val for val, fut in values_observed.items() if not fut.done())
                    await exposed_thing.properties[prop_name].write(next_value)
                except StopIteration:
                    break
                await asyncio.sleep(0.01)

        def on_next(ev):
            prop_value = ev.data.value
            if prop_value in values_observed and not values_observed[prop_value].done():
                values_observed[prop_value].set_result(True)

        observable = protocol_client.on_property_change(td, prop_name)

        loop = ioloop.IOLoop.current()
        scheduler = IOLoopScheduler(loop)
        subscription = observable.subscribe(on_next, scheduler=scheduler)

        task = asyncio.create_task(periodic_write_next())

        await asyncio.gather(*values_observed.values())

        task.cancel()
        subscription.dispose()

    await run_test_coroutine(test_coroutine)


async def client_test_on_event(servient, protocol_client_cls):
    """Helper function to test observation of Events on bindings clients."""

    exposed_thing = next(servient.exposed_things)
    event_name = uuid.uuid4().hex
    exposed_thing.add_event(event_name, EventFragmentDict({"type": "number"}))
    servient.refresh_forms()
    td = ThingDescription.from_thing(exposed_thing.thing)

    async def test_coroutine():
        protocol_client = protocol_client_cls()

        payloads = [Faker().pyint() for _ in range(10)]
        loop = asyncio.get_running_loop()
        future_payloads = {key: loop.create_future() for key in payloads}

        async def periodic_emit_next():
            while True:
                try:
                    next_value = next(val for val, fut in future_payloads.items() if not fut.done())
                    exposed_thing.events[event_name].emit(next_value)
                except StopIteration:
                    break
                await asyncio.sleep(0.01)

        def on_next(ev):
            if ev.data in future_payloads and not future_payloads[ev.data].done():
                future_payloads[ev.data].set_result(True)

        observable = protocol_client.on_event(td, event_name)

        loop = ioloop.IOLoop.current()
        scheduler = IOLoopScheduler(loop)
        subscription = observable.subscribe(on_next, scheduler=scheduler)

        task = asyncio.create_task(periodic_emit_next())

        await asyncio.gather(*future_payloads.values())

        task.cancel()
        subscription.dispose()

    await run_test_coroutine(test_coroutine)


async def client_test_read_property(servient, protocol_client_cls, timeout=None):
    """Helper function to test Property reads on bindings clients."""

    exposed_thing = next(servient.exposed_things)
    prop_name = uuid.uuid4().hex

    exposed_thing.add_property(
        prop_name,
        PropertyFragmentDict({"type": "string", "observable": True}),
        value=Faker().sentence()
    )

    servient.refresh_forms()
    td = ThingDescription.from_thing(exposed_thing.thing)

    async def test_coroutine():
        protocol_client = protocol_client_cls()
        prop_value = Faker().sentence()

        curr_prop_value = await protocol_client.read_property(td, prop_name, timeout=timeout)

        assert curr_prop_value != prop_value

        await exposed_thing.properties[prop_name].write(prop_value)

        curr_prop_value = await protocol_client.read_property(td, prop_name, timeout=timeout)

        assert curr_prop_value == prop_value

    await run_test_coroutine(test_coroutine)


async def client_test_read_all_properties(servient, protocol_client_cls, timeout=None):
    """Helper function to test all Property reads on binding clients."""

    exposed_thing = next(servient.exposed_things)
    servient.refresh_forms()
    td = ThingDescription.from_thing(exposed_thing.thing)

    async def test_coroutine():
        protocol_client = protocol_client_cls()
        result = await protocol_client.read_all_properties(td, timeout=timeout)
        assert result == await exposed_thing.read_all_properties()

    await run_test_coroutine(test_coroutine)


async def client_test_read_multiple_properties(servient, protocol_client_cls, timeout=None):
    """Helper function to test multiple Property reads on binding clients."""

    exposed_thing = next(servient.exposed_things)
    property_names = [uuid.uuid4().hex for _ in range(2)]
    for name in property_names:
        exposed_thing.add_property(
            name,
            PropertyFragmentDict({"type": "string", "observable": True}),
            value=Faker().sentence()
        )
    servient.refresh_forms()
    td = ThingDescription.from_thing(exposed_thing.thing)

    async def test_coroutine():
        protocol_client = protocol_client_cls()
        all_values = await exposed_thing.read_all_properties()
        selected_values = {name: all_values[name] for name in property_names}

        result = await protocol_client.read_multiple_properties(
            td, property_names, timeout=timeout
        )
        assert result == selected_values

    await run_test_coroutine(test_coroutine)


async def client_test_write_all_properties(servient, protocol_client_cls, timeout=None):
    """Helper function to test all Property writes on binding clients."""

    exposed_thing = next(servient.exposed_things)
    servient.refresh_forms()
    td = ThingDescription.from_thing(exposed_thing.thing)

    async def test_coroutine():
        protocol_client = protocol_client_cls()
        initial_values = await exposed_thing.read_all_properties()
        writable_names = [
            name for name, prop in td.properties.items() if not prop.read_only
        ]
        values = {
            name: "{} updated".format(initial_values[name])
            for name in writable_names
        }
        await protocol_client.write_all_properties(td, values, timeout=timeout)
        assert await exposed_thing.read_all_properties() == {
            **initial_values,
            **values,
        }

    await run_test_coroutine(test_coroutine)


async def client_test_write_multiple_properties(servient, protocol_client_cls, timeout=None):
    """Helper function to test multiple Property writes on binding clients."""

    exposed_thing = next(servient.exposed_things)
    property_names = [uuid.uuid4().hex for _ in range(2)]
    for name in property_names:
        exposed_thing.add_property(
            name,
            PropertyFragmentDict({"type": "string", "observable": True}),
            value=Faker().sentence()
        )
    servient.refresh_forms()
    td = ThingDescription.from_thing(exposed_thing.thing)
    initial_values = await exposed_thing.read_all_properties()

    async def test_coroutine():
        protocol_client = protocol_client_cls()
        values = {
            name: "{} updated".format(initial_values[name])
            for name in property_names
        }
        await protocol_client.write_multiple_properties(td, values, timeout=timeout)
        assert await exposed_thing.read_all_properties() == {
            **initial_values,
            **values,
        }

    await run_test_coroutine(test_coroutine)


async def client_test_write_property(servient, protocol_client_cls, timeout=None):
    """Helper function to test Property writes on bindings clients."""

    exposed_thing = next(servient.exposed_things)

    prop_name = uuid.uuid4().hex

    exposed_thing.add_property(
        prop_name,
        PropertyFragmentDict({"type": "string", "observable": True}),
        value=Faker().sentence()
    )

    servient.refresh_forms()
    td = ThingDescription.from_thing(exposed_thing.thing)

    async def test_coroutine():
        protocol_client = protocol_client_cls()
        prop_value = Faker().sentence()

        prev_value = await exposed_thing.properties[prop_name].read()
        assert prev_value != prop_value

        await protocol_client.write_property(td, prop_name, prop_value, timeout=timeout)

        curr_value = await exposed_thing.properties[prop_name].read()
        assert curr_value == prop_value

    await run_test_coroutine(test_coroutine)


async def client_test_invoke_action(servient, protocol_client_cls, timeout=None):
    """Helper function to test Action invocations on bindings clients."""

    exposed_thing = next(servient.exposed_things)
    action_name = uuid.uuid4().hex

    async def action_handler(input_value):
        await asyncio.sleep(random.random() * 0.1)
        return("{:f}".format(input_value))

    exposed_thing.add_action(
        action_name,
        ActionFragmentDict({"input": {"type": "number"}, "output": {"type": "string"}}),
        action_handler
    )

    servient.refresh_forms()
    td = ThingDescription.from_thing(exposed_thing.thing)

    async def test_coroutine():
        protocol_client = protocol_client_cls()

        input_value = Faker().pyint()

        result = await protocol_client.invoke_action(td, action_name, input_value, timeout=timeout)
        result_expected = await action_handler(input_value)

        assert result == result_expected

    await run_test_coroutine(test_coroutine)


async def client_test_invoke_action_error(servient, protocol_client_cls):
    """Helper function to test Action invocations that raise errors on bindings clients."""

    exposed_thing = next(servient.exposed_things)
    action_name = uuid.uuid4().hex
    err_message = Faker().sentence()

    def action_handler(parameters):
        raise ValueError(err_message)

    exposed_thing.add_action(action_name, ActionFragmentDict({
        "input": {"type": "number"},
        "output": {"type": "string"}
    }), action_handler)

    servient.refresh_forms()

    td = ThingDescription.from_thing(exposed_thing.thing)

    async def test_coroutine():
        protocol_client = protocol_client_cls()

        try:
            await protocol_client.invoke_action(td, action_name, Faker().pyint())
            raise AssertionError("Did not raise Exception")
        except Exception as ex:
            assert err_message in str(ex)

    await run_test_coroutine(test_coroutine)


async def client_test_on_property_change_error(servient, protocol_client_cls):
    """Helper function to test propagation of errors raised
    during observation of Property updates on bindings clients."""

    exposed_thing = next(servient.exposed_things)

    prop_name = uuid.uuid4().hex

    exposed_thing.add_property(
        prop_name,
        PropertyFragmentDict({"type": "string", "observable": True}),
        value=Faker().sentence()
    )

    servient.refresh_forms()
    td = ThingDescription.from_thing(exposed_thing.thing)

    async def test_coroutine():
        protocol_client = protocol_client_cls()

        await servient.shutdown()

        loop = asyncio.get_running_loop()
        future_err = loop.create_future()

        def on_next(item):
            future_err.set_exception(Exception("Should not have emitted any items"))

        def on_error(err):
            future_err.set_result(err)

        observable = protocol_client.on_property_change(td, prop_name)

        loop = ioloop.IOLoop.current()
        scheduler = IOLoopScheduler(loop)
        subscribe_kwargs = {
            "on_next": on_next,
            "on_error": on_error,
            "scheduler": scheduler
        }

        subscription = observable.subscribe(**subscribe_kwargs)

        observe_err = await future_err

        assert isinstance(observe_err, Exception)

        subscription.dispose()

    await run_test_coroutine(test_coroutine)
