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
Zenoh handler for Property reads, writes and subscriptions to value updates.
"""

import asyncio
import json
import random
import time
from json import JSONDecodeError

from wotpy.protocols.zenoh.handlers.base import BaseZenohHandler
from wotpy.protocols.zenoh.handlers.subs import InteractionsSubscriber
from wotpy.utils.utils import to_json_obj
from wotpy.wot.enums import InteractionTypes


class PropertyZenohHandler(BaseZenohHandler):
    """Zenoh handler for Property reads, writes and subscriptions to value updates."""

    KEY_ACTION = "action"
    KEY_VALUE = "value"
    KEY_ACK = "ack"
    ACTION_WRITE = "write"
    DEFAULT_CALLBACK_MS = 2000
    DEFAULT_JITTER = 0.2

    def __init__(self, zenoh_server, callback_ms=None):
        super().__init__(zenoh_server)

        callback_ms = self.DEFAULT_CALLBACK_MS if callback_ms is None else callback_ms

        self._callback_ms = callback_ms
        self._subs = {}
        self._periodic_refresh_subs = None
        self._queryable = None

        self._interaction_subscriber = InteractionsSubscriber(
            interaction_type=InteractionTypes.PROPERTY,
            server=self.zenoh_server,
            on_next_builder=self._build_on_next)

    @property
    def topic_wildcard_requests(self):
        """Wildcard topic to subscribe to all Property requests."""

        return "{}/property/requests/**".format(self.servient_id)

    def build_property_updates_topic(self, thing, prop):
        """Returns the Zenoh topic for Property updates."""

        return "{}/property/updates/{}/{}".format(
            self.servient_id,
            thing.url_name,
            prop.url_name)

    @classmethod
    def to_write_ack_topic(cls, requests_topic):
        """Takes a Property requests topic and returns the related write ACK topic."""

        topic_split = requests_topic.split("/")
        servient_id, thing_name, prop_name = topic_split[-5], topic_split[-2], topic_split[-1]

        return "{}/property/ack/{}/{}".format(
            servient_id,
            thing_name,
            prop_name)

    @property
    def topics(self):
        """List of topics that this Zenoh handler wants to subscribe to."""

        return [(self.topic_wildcard_requests)]

    async def handle_message(self, sample):
        """Listens to all Property request topics and responds to read and write requests."""

        try:
            parsed_msg = json.loads(sample.payload.to_string())
        except (JSONDecodeError, TypeError):
            return

        action = parsed_msg.get(self.KEY_ACTION, False)

        if not action or action != self.ACTION_WRITE:
            return

        topic_split = str(sample.key_expr).split("/")

        splits_expected_len = len(self.topic_wildcard_requests.split("/")) + 1

        if len(topic_split) != splits_expected_len:
            return

        thing_url_name, prop_url_name = topic_split[-2], topic_split[-1]

        try:
            exp_thing = next(
                item for item in self.zenoh_server.exposed_things
                if item.url_name == thing_url_name)

            prop = next(
                exp_thing.thing.properties[key] for key in exp_thing.thing.properties
                if exp_thing.thing.properties[key].url_name == prop_url_name)
        except StopIteration:
            return

        await exp_thing.handle_write_property(prop.name, parsed_msg[self.KEY_VALUE])
        await self.publish_write_ack(sample, parsed_msg)

    async def publish_write_ack(self, sample, parsed_msg):
        """Publishes the write ACK message for the given write request."""

        ack_code = parsed_msg.get(self.KEY_ACK, None)

        if not ack_code:
            return

        topic_ack = self.to_write_ack_topic(str(sample.key_expr))

        await self.queue.put({
            "topic": topic_ack,
            "data": json.dumps({self.KEY_ACK: ack_code}).encode()
        })

    async def init(self):
        """Initializes the Zenoh handler.
        Called when the Zenoh runner starts."""

        async def refresh_subs():
            while True:
                self._interaction_subscriber.refresh()
                callback_sec = self._callback_ms / 1000
                callback_sec *= 1 + (self.DEFAULT_JITTER * (random.random() - 0.5))
                await asyncio.sleep(callback_sec)

        self._interaction_subscriber.refresh()
        self._periodic_refresh_subs = asyncio.create_task(refresh_subs())

        loop = asyncio.get_running_loop()
        splits_expected_len = len(self.topic_wildcard_requests.split("/")) + 1

        async def handle_read_query(query):
            topic_split = str(query.key_expr).split("/")

            if len(topic_split) != splits_expected_len:
                query.reply_err(b"Unexpected topic format")
                return

            thing_url_name, prop_url_name = topic_split[-2], topic_split[-1]

            try:
                exp_thing = next(
                    item for item in self.zenoh_server.exposed_things
                    if item.url_name == thing_url_name)

                prop = next(
                    exp_thing.thing.properties[key] for key in exp_thing.thing.properties
                    if exp_thing.thing.properties[key].url_name == prop_url_name)
            except StopIteration:
                query.reply_err(b"Property not found")
                return

            try:
                value = await exp_thing.properties[prop.name].read()
            except Exception as ex:
                query.reply_err(str(ex).encode())
                return

            now_ms = int(time.time() * 1000)
            payload = json.dumps({
                self.KEY_VALUE: to_json_obj(value),
                "timestamp": now_ms
            }).encode()
            query.reply(str(query.key_expr), payload)

        def queryable_callback(query):
            asyncio.run_coroutine_threadsafe(handle_read_query(query), loop)

        self._queryable = self.zenoh_server._session.declare_queryable(
            self.topic_wildcard_requests, queryable_callback)

        return None

    async def teardown(self):
        """Destroys the Zenoh handler.
        Called when the Zenoh runner stops."""

        self._periodic_refresh_subs.cancel()
        self._interaction_subscriber.dispose()

        if self._queryable is not None:
            self._queryable.undeclare()
            self._queryable = None

        return None

    def _build_update_message(self, topic, value):
        """Builds an Zenoh message to publish an update for a Property value."""

        now_ms = int(time.time() * 1000)

        return {
            "topic": topic,
            "data": json.dumps({
                "value": to_json_obj(value),
                "timestamp": now_ms
            }).encode()
        }

    def _build_on_next(self, exp_thing, prop):
        """Builds the on_next function to use when subscribing to the given Property."""

        topic = self.build_property_updates_topic(exp_thing, prop)

        def on_next(item):
            try:
                msg = self._build_update_message(topic, item.data.value)
                self.queue.put_nowait(msg)
            except asyncio.QueueFull:
                pass

        return on_next
