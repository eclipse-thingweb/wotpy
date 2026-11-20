#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2018 CTIC Centro Tecnologico
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
Wrapper classes for data schema dictionaries defined in the Scripting API.
"""

from wotpy.wot.dictionaries.base import WotBaseDict
from wotpy.utils.utils import merge_args_kwargs_dict
from wotpy.wot.enums import DataType


class DataSchemaDict(WotBaseDict):
    """Represents the common properties of a value type definition."""

    class Meta:
        fields = {
            "@type",
            "title",
            "titles",
            "description",
            "descriptions",
            "const",
            "default",
            "unit",
            "oneOf",
            "enum",
            "readOnly",
            "writeOnly",
            "format",
            "type"
        }

        defaults = {
            "readOnly": False,
            "writeOnly": False
        }

    @property
    def one_of(self):
        """Used to ensure that the data is valid against
        one of the specified schemas in the array."""

        one_of = self._init.get("oneOf", None)
        if not one_of:
            return None

        return [DataSchemaDict.build(item) for item in one_of]

    @classmethod
    def build(cls, *args, **kwargs):
        """Builds an instance of the appropriate subclass for the given ValueType."""

        init_dict = merge_args_kwargs_dict(args, kwargs)
        if not init_dict:
            raise ValueError("Missing data schema definition")

        klass_map = {
            DataType.NUMBER: NumberSchemaDict,
            DataType.BOOLEAN: BooleanSchemaDict,
            DataType.STRING: StringSchemaDict,
            DataType.OBJECT: ObjectSchemaDict,
            DataType.ARRAY: ArraySchemaDict,
            DataType.INTEGER: IntegerSchema,
            DataType.NULL: NullSchemaDict
        }

        klass_type = init_dict.get("type")

        if klass_type is None:
            if "properties" in init_dict:
                klass = ObjectSchemaDict
            elif "items" in init_dict:
                klass = ArraySchemaDict
            elif any(k in init_dict for k in ("minimum", "maximum", "multipleOf", "exclusiveMinimum", "exclusiveMaximum")):
                klass = NumberSchemaDict
            elif "enum" in init_dict:
                klass = DataSchemaDict
            else:
                klass = DataSchemaDict
        else:
            klass = klass_map.get(klass_type)

        if not klass:
            raise ValueError("Unknown type: {}".format(klass_type))

        return klass(*args, **kwargs)

class NullSchemaDict(DataSchemaDict):
    """Empty Null schema class."""

    @property
    def type(self):
        """The type property represents the value type enumerated in DataType."""

        return DataType.NULL

class NumberSchemaDict(DataSchemaDict):
    """Properties to describe a numeric type."""

    class Meta:
        fields = DataSchemaDict.Meta.fields.union({
            "minimum",
            "exclusiveMinimum",
            "maximum",
            "exclusiveMaximum",
            "multipleOf"
        })

        defaults = DataSchemaDict.Meta.defaults

    @property
    def type(self):
        """The type property represents the value type (a member of DataType)."""

        return DataType.NUMBER


class BooleanSchemaDict(DataSchemaDict):
    """Properties to describe a boolean type."""

    @property
    def type(self):
        """The type property represents the value type enumerated in DataType."""

        return DataType.BOOLEAN


class StringSchemaDict(DataSchemaDict):
    """Properties to describe a string type."""

    class Meta:
        fields = DataSchemaDict.Meta.fields.union({
            "minLength",
            "maxLength",
            "pattern",
            "contentEncoding",
            "contentMediaType"
        })

        defaults = DataSchemaDict.Meta.defaults

    @property
    def type(self):
        """The type property represents the value type enumerated in DataType."""

        return DataType.STRING


class ObjectSchemaDict(DataSchemaDict):
    """Properties to describe an object type."""

    class Meta:
        fields = DataSchemaDict.Meta.fields.union({
            "properties",
            "required"
        })

        defaults = DataSchemaDict.Meta.defaults

    @property
    def type(self):
        """The type property represents the value type enumerated in DataType."""

        return DataType.OBJECT

    @property
    def properties(self):
        """Data schema nested definitions."""

        return {
            key: DataSchemaDict.build(val)
            for key, val in self._init.get("properties", {}).items()
        }


class ArraySchemaDict(DataSchemaDict):
    """Properties to describe an array type."""

    class Meta:
        fields = DataSchemaDict.Meta.fields.union({
            "items",
            "minItems",
            "maxItems"
        })

        defaults = DataSchemaDict.Meta.defaults

    @property
    def type(self):
        """The type property represents the value type enumerated in DataType."""

        return DataType.ARRAY

    @property
    def items(self):
        """Used to define the characteristics of an array."""

        if "items" not in self._init:
            return None

        items = self._init["items"]
        if isinstance(items, list):
            return [DataSchemaDict.build(item) for item in items]

        return DataSchemaDict.build(items)


class IntegerSchema(NumberSchemaDict):
    """Properties to describe an integer type."""

    @property
    def type(self):
        """The type property represents the value type enumerated in DataType."""

        return DataType.INTEGER
