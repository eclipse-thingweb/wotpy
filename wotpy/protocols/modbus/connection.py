#!/usr/bin/env python
# -*- coding: utf-8 -*-

# SPDX-License-Identifier: MIT

"""
Connection helpers for Modbus TCP operations.
"""

import asyncio

from pymodbus.client import AsyncModbusTcpClient

from wotpy.protocols.modbus.enums import ModbusEntity, ModbusFunction


class ModbusConnection:
    """Connection wrapper around AsyncModbusTcpClient."""

    def __init__(self, host, port, timeout_ms=1000):
        self._host = host
        self._port = port
        self._timeout_secs = max(float(timeout_ms) / 1000.0, 0.1)
        self._client = AsyncModbusTcpClient(host=self._host, port=self._port, timeout=self._timeout_secs)
        self._lock = asyncio.Lock()

    @property
    def key(self):
        return "{}:{}".format(self._host, self._port)

    async def close(self):
        async with self._lock:
            try:
                self._client.close()
            except Exception:
                pass

    async def _connect(self):
        if self._client.connected:
            return

        ok = await self._client.connect()

        if not ok:
            raise ConnectionError("Could not connect to Modbus endpoint {}:{}".format(
                self._host, self._port))

    async def _call_with_unit(self, fn, *args, unit_id, **kwargs):
        """Calls pymodbus methods handling both 'slave' and 'unit' kwargs."""

        try:
            return await fn(*args, slave=unit_id, **kwargs)
        except TypeError:
            try:
                return await fn(*args, unit=unit_id, **kwargs)
            except TypeError:
                return await fn(*args, device_id=unit_id, **kwargs)

    @staticmethod
    def _raise_if_error(result):
        if hasattr(result, "isError") and result.isError():
            raise RuntimeError("Modbus operation failed: {}".format(result))

    async def read(self, entity, address, quantity, unit_id):
        """Reads coils/registers based on the requested Modbus entity."""

        async with self._lock:
            await self._connect()

            if entity == ModbusEntity.INPUT_REGISTER:
                result = await self._call_with_unit(
                    self._client.read_input_registers,
                    address,
                    count=quantity,
                    unit_id=unit_id)
            elif entity == ModbusEntity.COIL:
                result = await self._call_with_unit(
                    self._client.read_coils,
                    address,
                    count=quantity,
                    unit_id=unit_id)
            elif entity == ModbusEntity.HOLDING_REGISTER:
                result = await self._call_with_unit(
                    self._client.read_holding_registers,
                    address,
                    count=quantity,
                    unit_id=unit_id)
            elif entity == ModbusEntity.DISCRETE_INPUT:
                result = await self._call_with_unit(
                    self._client.read_discrete_inputs,
                    address,
                    count=quantity,
                    unit_id=unit_id)
            else:
                raise ValueError("Unknown Modbus entity: {}".format(entity))

            self._raise_if_error(result)

            if entity in (ModbusEntity.COIL, ModbusEntity.DISCRETE_INPUT):
                return list(result.bits[:quantity])

            return list(result.registers[:quantity])

    async def write(self, function_code, address, quantity, unit_id, payload):
        """Writes coils/registers depending on the selected Modbus function."""

        async with self._lock:
            await self._connect()

            if function_code == ModbusFunction.WRITE_SINGLE_COIL:
                result = await self._call_with_unit(
                    self._client.write_coil,
                    address,
                    bool(payload),
                    unit_id=unit_id)
            elif function_code == ModbusFunction.WRITE_MULTIPLE_COILS:
                result = await self._call_with_unit(
                    self._client.write_coils,
                    address,
                    [bool(item) for item in payload],
                    unit_id=unit_id)
            elif function_code == ModbusFunction.WRITE_SINGLE_HOLDING_REGISTER:
                result = await self._call_with_unit(
                    self._client.write_register,
                    address,
                    int(payload),
                    unit_id=unit_id)
            elif function_code == ModbusFunction.WRITE_MULTIPLE_HOLDING_REGISTERS:
                result = await self._call_with_unit(
                    self._client.write_registers,
                    address,
                    [int(item) for item in payload],
                    unit_id=unit_id)
            else:
                raise ValueError("Unsupported write function code: {}".format(function_code))

            self._raise_if_error(result)

            return None
