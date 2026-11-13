#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2017 CTIC Centro Tecnologico
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
Class that represents a Thing.
"""

import hashlib
import itertools
import uuid

from slugify import slugify

from wotpy.utils.utils import to_camel
from wotpy.wot.dictionaries.thing import ThingFragment
from wotpy.wot.interaction import Property, Action, Event


class Thing:
    """An abstraction of a physical or virtual entity whose metadata
    and interfaces are described by a WoT Thing Description."""

    THING_FRAGMENT_WRITABLE_FIELDS = {
            "@context",
            "@type",
            "id",
            "title",
            "titles",
            "description",
            "descriptions",
            "version",
            "created",
            "modified",
            "support",
            "base",
            "properties",
            "actions",
            "events",
            "links",
            "forms",
            "security",
            "securityDefinitions",
            "profile",
            "schemaDefinitions",
            "uriVariables"
    }

    assert THING_FRAGMENT_WRITABLE_FIELDS.issubset(ThingFragment.Meta.fields)

    def __init__(self, thing_fragment=None, **kwargs):
        self._thing_fragment = thing_fragment if thing_fragment else ThingFragment(**kwargs)
        self._security  = []
        self._security_definitions = {}
        self._properties = {}
        self._actions = {}
        self._events = {}
        self._init_fragment_data()

    def __getattr__(self, name):
        """Search for members that raised an AttributeError in
        the private ThingFragment before propagating the exception."""

        return getattr(self._thing_fragment, name)

    def __setattr__(self, name, value):
        """Setter for ThingFragment attributes."""

        name_camel = to_camel(name)

        if name_camel not in self.THING_FRAGMENT_WRITABLE_FIELDS:
            return super().__setattr__(name, value)

        return self._thing_fragment.__setattr__(name, value)

    def _init_fragment_data(self):
        """Adds the data declared in the ThingFragment to the instance private dicts."""

        self._security = self._thing_fragment.security
        self._security_definitions = self._thing_fragment.security_definitions

        for name, prop_fragment in self._thing_fragment.properties.items():
            prop = Property(thing=self, name=name, init_dict=prop_fragment)
            self.add_interaction(prop)

        for name, action_fragment in self._thing_fragment.actions.items():
            action = Action(thing=self, name=name, init_dict=action_fragment)
            self.add_interaction(action)

        for name, event_fragment in self._thing_fragment.events.items():
            event = Event(thing=self, name=name, init_dict=event_fragment)
            self.add_interaction(event)

    @property
    def thing_fragment(self):
        """The ThingFragment dictionary of this Thing."""

        def interaction_to_json(intrct):
            """Returns the JSON serialization of an Interaction instance."""

            ret = intrct.interaction_fragment.to_dict()

            ret.update({"forms": [form.form_dict.to_dict() for form in intrct.forms]})

            return ret

        doc = self._thing_fragment.to_dict()

        doc.update(
            {
                "properties": {
                    key: interaction_to_json(val)
                    for key, val in self.properties.items()
                }
            }
        )

        doc.update(
            {
                "actions": {
                    key: interaction_to_json(val) for key, val in self.actions.items()
                }
            }
        )

        doc.update(
            {
                "events": {
                    key: interaction_to_json(val) for key, val in self.events.items()
                }
            }
        )

        return ThingFragment(doc)

    @property
    def id(self):
        """Thing ID."""

        return self._thing_fragment.id

    @property
    def title(self):
        """Thing title."""

        return self._thing_fragment.title

    @property
    def url_name(self):
        """Returns the URL-safe name of this Thing."""

        return slugify(self._thing_fragment.title)

    @property
    def security(self):
        """List of supported security schemes."""

        return self._security

    @property
    def security_definitions(self):
        """Security configuration for each of the supported protocols."""

        return self._security_definitions

    @property
    def properties(self):
        """Properties interactions."""

        return self._properties

    @property
    def actions(self):
        """Actions interactions."""

        return self._actions

    @property
    def events(self):
        """Events interactions."""

        return self._events

    @property
    def interactions(self):
        """Sequence of interactions linked to this thing."""

        return itertools.chain(
            self._properties.values(),
            self._actions.values(),
            self._events.values())

    def find_interaction(self, name):
        """Finds an existing Interaction by name.
        The name argument may be the original name or the URL-safe version."""

        def is_match(intrct):
            return intrct.name == name or intrct.url_name == name

        return next((intrct for intrct in self.interactions if is_match(intrct)), None)

    def add_interaction(self, interaction):
        """Add a new Interaction."""

        if not isinstance(interaction, (Property, Event, Action)):
            raise ValueError("Not an Interaction")

        if interaction.thing is not self:
            raise ValueError("Interaction linked to another Thing")

        if self.find_interaction(interaction.name) or self.find_interaction(interaction.url_name):
            raise ValueError("Duplicate Interaction: {}".format(interaction.name))

        interaction_dict_map = {
            Property: self._properties,
            Action: self._actions,
            Event: self._events
        }

        interaction_class = next(
            klass for klass in [Property, Action, Event]
            if isinstance(interaction, klass))

        interaction_dict_map[interaction_class][interaction.name] = interaction

    def remove_interaction(self, name):
        """Removes an existing Interaction by name.
        The name argument may be the original name or the URL-safe version."""

        interaction = self.find_interaction(name)

        if interaction is None:
            return

        self._properties.pop(interaction.name, None)
        self._actions.pop(interaction.name, None)
        self._events.pop(interaction.name, None)
