#!/usr/bin/env python
# -*- coding: utf-8 -*-

# SPDX-License-Identifier: MIT

"""
Enumeration classes related to the Modbus protocol binding.
"""

from wotpy.utils.enums import EnumListMixin


class ModbusSchemes(EnumListMixin):
    """Enumeration of Modbus URI schemes."""

    MODBUS_TCP = "modbus+tcp"


class ModbusEntity(EnumListMixin):
    """Enumeration of Modbus entities."""

    COIL = "Coil"
    INPUT_REGISTER = "InputRegister"
    HOLDING_REGISTER = "HoldingRegister"
    DISCRETE_INPUT = "DiscreteInput"


class ModbusFunction(EnumListMixin):
    """Enumeration of Modbus function codes used by the binding."""

    READ_COIL = 1
    READ_DISCRETE_INPUT = 2
    READ_HOLDING_REGISTERS = 3
    READ_INPUT_REGISTER = 4
    WRITE_SINGLE_COIL = 5
    WRITE_SINGLE_HOLDING_REGISTER = 6
    WRITE_MULTIPLE_COILS = 15
    WRITE_MULTIPLE_HOLDING_REGISTERS = 16
    READ_DEVICE_IDENTIFICATION = 43


class ModbusFunctionName(EnumListMixin):
    """Enumeration of Modbus function names from the WoT Modbus vocabulary."""

    READ_COIL = "readCoil"
    READ_DISCRETE_INPUT = "readDiscreteInput"
    READ_HOLDING_REGISTERS = "readHoldingRegisters"
    READ_INPUT_REGISTER = "readInputRegister"
    WRITE_SINGLE_COIL = "writeSingleCoil"
    WRITE_SINGLE_HOLDING_REGISTER = "writeSingleHoldingRegister"
    WRITE_MULTIPLE_COILS = "writeMultipleCoils"
    WRITE_MULTIPLE_HOLDING_REGISTERS = "writeMultipleHoldingRegisters"
    READ_DEVICE_IDENTIFICATION = "readDeviceIdentification"


class ModbusDataType(EnumListMixin):
    """Enumeration of the XSD data types allowed by the WoT Modbus vocabulary."""

    INTEGER = "xsd:integer"
    BOOLEAN = "xsd:boolean"
    STRING = "xsd:string"
    FLOAT = "xsd:float"
    DECIMAL = "xsd:decimal"
    BYTE = "xsd:byte"
    SHORT = "xsd:short"
    INT = "xsd:int"
    LONG = "xsd:long"
    UNSIGNED_BYTE = "xsd:unsignedByte"
    UNSIGNED_SHORT = "xsd:unsignedShort"
    UNSIGNED_INT = "xsd:unsignedInt"
    UNSIGNED_LONG = "xsd:unsignedLong"
    DOUBLE = "xsd:double"
    HEX_BINARY = "xsd:hexBinary"


class ModbusVocabularyKeys(EnumListMixin):
    """Vocabulary keys that can appear in TD forms for Modbus."""

    FUNCTION = "modv:function"
    ENTITY = "modv:entity"
    UNIT_ID = "modv:unitID"
    ADDRESS = "modv:address"
    QUANTITY = "modv:quantity"
    POLLING_TIME = "modv:pollingTime"
    TIMEOUT = "modv:timeout"
    TYPE = "modv:type"
    MOST_SIGNIFICANT_BYTE = "modv:mostSignificantByte"
    MOST_SIGNIFICANT_WORD = "modv:mostSignificantWord"
    ZERO_BASED_ADDRESSING = "modv:zeroBasedAddressing"
