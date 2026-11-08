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

import asyncio
import json
import time
import uuid
from asyncio import TimeoutError
from urllib import parse
import random

import pytest
import zenoh
from faker import Faker

from tests.protocols.zenoh.router import is_test_router_online, ROUTER_SKIP_REASON, get_test_router_url
from tests.utils import run_test_coroutine
from wotpy.protocols.enums import InteractionVerbs
from wotpy.protocols.zenoh.handlers.action import ActionZenohHandler
from wotpy.protocols.zenoh.server import ZenohServer
from wotpy.protocols.zenoh.utils import build_zenoh_config
from wotpy.wot.dictionaries.interaction import PropertyFragmentDict, ActionFragmentDict

pytestmark = pytest.mark.skipif(asyncio.run(is_test_router_online()) is False, reason=ROUTER_SKIP_REASON)


def build_topic(server, interaction, interaction_verb):
    """Returns the topic for the given interaction and verb."""

    forms = server.build_forms(None, interaction)
    form = next(item for item in forms if interaction_verb == item.op)
    return parse.urlparse(form.href).path.strip("/")


def connect_router():
    """Connects to the test Zenoh broker."""

    config = build_zenoh_config(get_test_router_url())
    zenoh_session = zenoh.open(config)

    return zenoh_session


async def _create_listener(message_queue):
    """Returns a listener callback function that instead of blocking the main thread
    or running on a separate thread, puts messages on an asyncio Queue shared with the main
    asyncio loop."""

    loop = asyncio.get_running_loop()

    async def put_message_queue(sample):
        message_queue.put_nowait(sample)

    def listener(sample):
        coro = put_message_queue(sample)
        asyncio.run_coroutine_threadsafe(coro, loop)

    return listener


async def _ping(zenoh_server, timeout=None):
    """Returns True if the given Zenoh server has answered to a PING request."""

    topic_ping = "{}/ping".format(zenoh_server.servient_id)
    topic_pong = "{}/pong".format(zenoh_server.servient_id)

    message_queue = asyncio.Queue()

    try:
        zenoh_session = connect_router()
        listener = await _create_listener(message_queue)
        subscriber = zenoh_session.declare_subscriber(topic_pong, listener)
        bytes_payload = bytes(uuid.uuid4().hex, "utf8")
        zenoh_session.put(topic_ping, bytes_payload)
        reply = await asyncio.wait_for(message_queue.get(), timeout=timeout)
        assert reply.payload == bytes_payload
    except TimeoutError:
        return False
    finally:
        subscriber.undeclare()
        zenoh_session.close()

    return True


DEFAULT_PING_TIMEOUT = 1.0


@pytest.mark.asyncio
async def test_start_stop():
    """The Zenoh server may be started and stopped."""

    zenoh_server = ZenohServer(router_url=get_test_router_url())

    async def test_coroutine():
        assert not (await _ping(zenoh_server, timeout=DEFAULT_PING_TIMEOUT))

        await zenoh_server.start()

        assert (await _ping(zenoh_server))
        assert (await _ping(zenoh_server))

        await zenoh_server.stop()
        await zenoh_server.start()
        await zenoh_server.stop()

        assert not (await _ping(zenoh_server, timeout=DEFAULT_PING_TIMEOUT))

        await zenoh_server.stop()
        await zenoh_server.start()
        await zenoh_server.start()

        assert (await _ping(zenoh_server))

        await zenoh_server.stop()

    await run_test_coroutine(test_coroutine)


@pytest.mark.asyncio
async def test_servient_id():
    """A Zenoh server may be identified by a unique Servient ID to avoid topic collisions."""

    router_url = get_test_router_url()

    zenoh_srv_01 = ZenohServer(router_url=router_url)
    zenoh_srv_02 = ZenohServer(router_url=router_url)
    zenoh_srv_03 = ZenohServer(router_url=router_url, servient_id=Faker().pystr())

    assert zenoh_srv_01.servient_id and zenoh_srv_02.servient_id and zenoh_srv_03.servient_id
    assert zenoh_srv_01.servient_id == zenoh_srv_02.servient_id
    assert zenoh_srv_01.servient_id != zenoh_srv_03.servient_id

    async def assert_ping_loop(srv, num_iters=10):
        for _ in range(num_iters):
            assert (await _ping(srv, timeout=DEFAULT_PING_TIMEOUT))
            await asyncio.sleep(random.uniform(0.1, 0.3))

    async def test_coroutine():
        await zenoh_srv_01.start()
        await zenoh_srv_03.start()

        await assert_ping_loop(zenoh_srv_01)
        await assert_ping_loop(zenoh_srv_03)

        await zenoh_srv_01.stop()
        await zenoh_srv_03.stop()

    await run_test_coroutine(test_coroutine)


@pytest.mark.asyncio
async def test_property_read(zenoh_server):
    """Current Property values may be requested using the Zenoh binding."""

    exposed_thing = next(zenoh_server.exposed_things)
    prop_name = next(iter(exposed_thing.thing.properties.keys()))
    prop = exposed_thing.thing.properties[prop_name]
    topic_read = build_topic(zenoh_server, prop, InteractionVerbs.READ_PROPERTY)

    read_timeout_secs = 5.0

    async def test_coroutine():
        prop_value = await exposed_thing.properties[prop_name].read()

        zenoh_session = connect_router()
        loop = asyncio.get_running_loop()

        # The queryable replies on this same loop, so the blocking get must be offloaded
        def do_get():
            return list(zenoh_session.get(
                topic_read,
                zenoh.handlers.FifoChannel(1),
                timeout=read_timeout_secs))

        try:
            replies = await loop.run_in_executor(None, do_get)
        finally:
            zenoh_session.close()

        assert len(replies) > 0

        reply = replies[0]

        assert reply.ok is not None
        assert json.loads(reply.ok.payload.to_string()).get("value") == prop_value

    await run_test_coroutine(test_coroutine)


@pytest.mark.asyncio
async def test_property_write(zenoh_server):
    """Property values may be updated using the Zenohj binding."""

    exposed_thing = next(zenoh_server.exposed_things)
    prop_name = next(iter(exposed_thing.thing.properties.keys()))
    prop = exposed_thing.thing.properties[prop_name]
    topic_write = build_topic(zenoh_server, prop, InteractionVerbs.WRITE_PROPERTY)
    topic_observe = build_topic(zenoh_server, prop, InteractionVerbs.OBSERVE_PROPERTY)

    async def test_coroutine():
        message_queue = asyncio.Queue()

        updated_value = Faker().sentence()

        zenoh_session = connect_router()
        publisher = zenoh_session.declare_publisher(topic_write)
        listener = await _create_listener(message_queue)
        subscriber = zenoh_session.declare_subscriber(topic_observe, listener)

        loop = asyncio.get_running_loop()
        future_observe = loop.create_future()

        async def resolve_future_on_update():
            msg_observe = await message_queue.get()
            assert json.loads(msg_observe.payload.to_string()).get("value") == updated_value
            future_observe.set_result(True)

        asyncio.create_task(resolve_future_on_update())

        async def publish_write():
            while True:
                payload = json.dumps({"action": "write", "value": updated_value}).encode()
                publisher.put(payload)
                await asyncio.sleep(0.05)

        task = asyncio.create_task(publish_write())

        await future_observe

        assert future_observe.result() is True

        task.cancel()
        subscriber.undeclare()
        zenoh_session.close()

    await run_test_coroutine(test_coroutine)


CALLBACK_MS = 50


@pytest.mark.parametrize("zenoh_server", [{"property_callback_ms": CALLBACK_MS}], indirect=True)
@pytest.mark.asyncio
async def test_property_add_remove(zenoh_server):
    """The Zenoh binding reacts appropriately to Properties
    being added and removed from ExposedThings."""

    exposed_thing = next(zenoh_server.exposed_things)
    prop_names = list(exposed_thing.thing.properties.keys())

    for name in prop_names:
        exposed_thing.remove_property(name)

    def add_prop(pname):
        exposed_thing.add_property(pname, PropertyFragmentDict({
            "type": "number",
            "observable": True
        }), value=Faker().pyint())

    def del_prop(pname):
        exposed_thing.remove_property(pname)

    async def is_prop_active(prop, timeout_secs=1.0):
        message_queue = asyncio.Queue()

        topic_observe = build_topic(zenoh_server, prop, InteractionVerbs.OBSERVE_PROPERTY)
        topic_write = build_topic(zenoh_server, prop, InteractionVerbs.WRITE_PROPERTY)

        zenoh_session = connect_router()
        publisher = zenoh_session.declare_publisher(topic_write)
        listener = await _create_listener(message_queue)
        subscriber = zenoh_session.declare_subscriber(topic_observe, listener)

        value = Faker().pyint()

        async def publish_write():
            while True:
                payload = json.dumps({"action": "write", "value": value}).encode()
                publisher.put(payload)
                await asyncio.sleep(timeout_secs / 4)

        task = asyncio.create_task(publish_write())

        try:
            msg = await asyncio.wait_for(message_queue.get(), timeout=timeout_secs)
            assert json.loads(msg.payload.to_string()).get("value") == value
            return True
        except TimeoutError:
            return False
        finally:
            subscriber.undeclare()
            zenoh_session.close()
            task.cancel()

    async def test_coroutine():
        sleep_secs = (CALLBACK_MS / 1000.0) * 4

        prop_01_name = uuid.uuid4().hex
        prop_02_name = uuid.uuid4().hex
        prop_03_name = uuid.uuid4().hex

        add_prop(prop_01_name)
        add_prop(prop_02_name)
        add_prop(prop_03_name)

        prop_01 = exposed_thing.thing.properties[prop_01_name]
        prop_02 = exposed_thing.thing.properties[prop_02_name]
        prop_03 = exposed_thing.thing.properties[prop_03_name]

        await asyncio.sleep(sleep_secs)

        assert (await is_prop_active(prop_01))
        assert (await is_prop_active(prop_02))
        assert (await is_prop_active(prop_03))

        del_prop(prop_01_name)

        assert not (await is_prop_active(prop_01))
        assert (await is_prop_active(prop_02))
        assert (await is_prop_active(prop_03))

        del_prop(prop_03_name)

        assert not (await is_prop_active(prop_01))
        assert (await is_prop_active(prop_02))
        assert not (await is_prop_active(prop_03))

        add_prop(prop_01_name)

        prop_01 = exposed_thing.thing.properties[prop_01_name]

        assert (await is_prop_active(prop_01))
        assert (await is_prop_active(prop_02))
        assert not (await is_prop_active(prop_03))

    await run_test_coroutine(test_coroutine)


@pytest.mark.asyncio
async def test_observe_property_changes(zenoh_server):
    """Property updates may be observed using the Zenoh binding."""

    exposed_thing = next(zenoh_server.exposed_things)
    prop_name = next(iter(exposed_thing.thing.properties.keys()))
    prop = exposed_thing.thing.properties[prop_name]
    topic_observe = build_topic(zenoh_server, prop, InteractionVerbs.OBSERVE_PROPERTY)

    async def test_coroutine():
        message_queue = asyncio.Queue()
        zenoh_session = connect_router()
        listener = await _create_listener(message_queue)
        subscriber = zenoh_session.declare_subscriber(topic_observe, listener)

        updated_value = Faker().sentence()

        async def write_value():
            while True:
                await exposed_thing.properties[prop_name].write(updated_value)
                await asyncio.sleep(0.05)

        task = asyncio.create_task(write_value())

        msg = await message_queue.get()

        assert json.loads(msg.payload.to_string()).get("value") == updated_value

        task.cancel()
        subscriber.undeclare()
        zenoh_session.close()

    await run_test_coroutine(test_coroutine)


@pytest.mark.asyncio
async def test_observe_event(zenoh_server):
    """Events may be observed using the Zenoh binding."""

    now_ms = int(time.time() * 1000)

    exposed_thing = next(zenoh_server.exposed_things)
    event_name = next(iter(exposed_thing.thing.events.keys()))
    event = exposed_thing.thing.events[event_name]
    topic = build_topic(zenoh_server, event, InteractionVerbs.SUBSCRIBE_EVENT)

    async def test_coroutine():
        message_queue = asyncio.Queue()
        zenoh_session = connect_router()
        listener = await _create_listener(message_queue)
        subscriber = zenoh_session.declare_subscriber(topic, listener)

        emitted_value = Faker().pyint()

        async def emit_value():
            while True:
                exposed_thing.events[event_name].emit(emitted_value)
                await asyncio.sleep(0.05)

        task = asyncio.create_task(emit_value())

        msg = await message_queue.get()

        event_data = json.loads(msg.payload.to_string())

        assert event_data.get("name") == event_name
        assert event_data.get("data") == emitted_value
        assert event_data.get("timestamp") >= now_ms

        task.cancel()
        subscriber.undeclare()
        zenoh_session.close()

    await run_test_coroutine(test_coroutine)


@pytest.mark.asyncio
async def test_action_invoke(zenoh_server):
    """Actions can be invoked using the Zenoh binding."""

    exposed_thing = next(zenoh_server.exposed_things)
    action_name = next(iter(exposed_thing.thing.actions.keys()))
    action = exposed_thing.thing.actions[action_name]

    topic_invoke = build_topic(zenoh_server, action, InteractionVerbs.INVOKE_ACTION)
    topic_result = ActionZenohHandler.to_result_topic(topic_invoke)

    async def test_coroutine():
        message_queue = asyncio.Queue()
        zenoh_session = connect_router()
        publisher = zenoh_session.declare_publisher(topic_invoke)
        listener = await _create_listener(message_queue)
        subscriber = zenoh_session.declare_subscriber(topic_result, listener)

        data = {
            "id": uuid.uuid4().hex,
            "input": Faker().pyint()
        }

        now_ms = int(time.time() * 1000)

        publisher.put(json.dumps(data).encode())

        msg = await message_queue.get()
        msg_data = json.loads(msg.payload.to_string())

        assert msg_data.get("id") == data.get("id")
        assert msg_data.get("result") == "{:f}".format(data.get("input"))
        assert msg_data.get("timestamp") >= now_ms

        subscriber.undeclare()
        zenoh_session.close()

    await run_test_coroutine(test_coroutine)


@pytest.mark.asyncio
async def test_action_invoke_error(zenoh_server):
    """Action errors are handled appropriately by the Zenoh binding."""

    exposed_thing = next(zenoh_server.exposed_things)

    action_name = uuid.uuid4().hex
    err_message = Faker().sentence()

    def handler(parameters):
        raise TypeError(err_message)

    router_url = zenoh_server._router_url
    servient_id = zenoh_server.servient_id
    thing_name = exposed_thing.thing.title
    exposed_thing.add_action(action_name, ActionFragmentDict({
        "input": {"type": "string"},
        "output": {"type": "string"}
    }), handler)

    action = exposed_thing.thing.actions[action_name]

    topic_invoke = build_topic(zenoh_server, action, InteractionVerbs.INVOKE_ACTION)
    topic_result = ActionZenohHandler.to_result_topic(topic_invoke)

    async def test_coroutine():
        message_queue = asyncio.Queue()

        zenoh_session = connect_router()
        publisher = zenoh_session.declare_publisher(topic_invoke)
        listener = await _create_listener(message_queue)
        subscriber = zenoh_session.declare_subscriber(topic_result, listener)

        data = {
            "id": uuid.uuid4().hex,
            "input": Faker().pyint()
        }

        publisher.put(json.dumps(data).encode())

        msg = await message_queue.get()
        msg_data = json.loads(msg.payload.to_string())

        assert msg_data.get("id") == data.get("id")
        assert msg_data.get("error") == err_message
        assert msg_data.get("result", None) is None

        subscriber.undeclare()
        zenoh_session.close()

    await run_test_coroutine(test_coroutine)


@pytest.mark.asyncio
async def test_action_invoke_parallel(zenoh_server):
    """Multiple Actions can be invoked in parallel using the Zenoh binding."""

    exposed_thing = next(zenoh_server.exposed_things)
    action_name = next(iter(exposed_thing.thing.actions.keys()))
    action = exposed_thing.thing.actions[action_name]

    topic_invoke = build_topic(zenoh_server, action, InteractionVerbs.INVOKE_ACTION)
    topic_result = ActionZenohHandler.to_result_topic(topic_invoke)

    num_requests = 10

    async def test_coroutine():
        message_queue = asyncio.Queue()

        zenoh_session = connect_router()
        publisher = zenoh_session.declare_publisher(topic_invoke)
        listener = await _create_listener(message_queue)
        subscriber = zenoh_session.declare_subscriber(topic_result, listener)

        requests = []

        for idx in range(num_requests):
            requests.append({
                "id": uuid.uuid4().hex,
                "input": Faker().pyint()
            })

        now_ms = int(time.time() * 1000)

        for idx in range(num_requests):
            publisher.put(json.dumps(requests[idx]).encode())

        for idx in range(num_requests):
            msg = await message_queue.get()
            msg_data = json.loads(msg.payload.to_string())
            expected = next(item for item in requests if item.get("id") == msg_data.get("id"))

            assert msg_data.get("id") == expected.get("id")
            assert msg_data.get("result") == "{:f}".format(expected.get("input"))
            assert msg_data.get("timestamp") >= now_ms

        subscriber.undeclare()
        zenoh_session.close()

    await run_test_coroutine(test_coroutine)
