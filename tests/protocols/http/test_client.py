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

import pytest

from tests.protocols.helpers import \
    client_test_on_property_change, \
    client_test_on_event, \
    client_test_read_property, \
    client_test_read_all_properties, \
    client_test_read_multiple_properties, \
    client_test_write_property, \
    client_test_write_all_properties, \
    client_test_write_multiple_properties, \
    client_test_invoke_action, \
    client_test_invoke_action_error, \
    client_test_on_property_change_error
from wotpy.protocols.http.client import HTTPClient


@pytest.mark.asyncio
async def test_read_property(http_servient):
    """The HTTP client can read properties."""

    await client_test_read_property(http_servient, HTTPClient)


@pytest.mark.asyncio
async def test_read_all_properties(http_servient):
    """The HTTP client can read all properties."""

    await client_test_read_all_properties(http_servient, HTTPClient)


@pytest.mark.asyncio
async def test_read_multiple_properties(http_servient):
    """The HTTP client can read selected properties."""

    await client_test_read_multiple_properties(http_servient, HTTPClient)


@pytest.mark.asyncio
async def test_write_property(http_servient):
    """The HTTP client can write properties."""

    await client_test_write_property(http_servient, HTTPClient)


@pytest.mark.asyncio
async def test_write_all_properties(http_servient):
    """The HTTP client can write all properties."""

    await client_test_write_all_properties(http_servient, HTTPClient)


@pytest.mark.asyncio
async def test_write_multiple_properties(http_servient):
    """The HTTP client can write selected properties."""

    await client_test_write_multiple_properties(http_servient, HTTPClient)


@pytest.mark.asyncio
async def test_invoke_action(http_servient):
    """The HTTP client can invoke actions."""

    await client_test_invoke_action(http_servient, HTTPClient)


@pytest.mark.asyncio
async def test_invoke_action_error(http_servient):
    """Errors raised by Actions are propagated propertly by the HTTP binding client."""

    await client_test_invoke_action_error(http_servient, HTTPClient)


@pytest.mark.asyncio
async def test_on_event(http_servient):
    """The HTTP client can subscribe to event emissions."""

    await client_test_on_event(http_servient, HTTPClient)


@pytest.mark.asyncio
async def test_on_property_change(http_servient):
    """The HTTP client can subscribe to property updates."""

    await client_test_on_property_change(http_servient, HTTPClient)


@pytest.mark.asyncio
async def test_on_property_change_error(http_servient):
    """Errors that arise in the middle of an ongoing Property
    observation are propagated to the subscription as expected."""

    await client_test_on_property_change_error(http_servient, HTTPClient)
