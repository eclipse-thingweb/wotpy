Zenoh
=====

This section describes the mapping between the high-level actions that can be executed on a Thing and the
messages exchanged with the Zenoh router when using the Zenoh Protocol Binding.

.. note:: Unlike the other bindings, the Zenoh binding is not self-contained and requires the presence of an external Zenoh router.

All messages are serialized in JSON format.

Form elements
-------------

Form elements produced by the Zenoh binding vary depending on the type of interaction. All forms contain the following fields:

=============   ===========
Field           Description
=============   ===========
``op``          Interaction verb (e.g. ``readproperty``) associated with this form element.
``href``        Contains the Zenoh router URL joined with the servient ID and the name of an Zenoh topic.
``mediaType``   This field will always contain the MIME media type for JSON.
=============   ===========

An example of an Zenoh form ``href``::

    zenoh+tcp://my.zenoh.router:7447/my-servient/property/requests/benchmark-thing/currenttime

* ``tcp`` is the transport of the underlying Zenoh locator (``tcp/my.zenoh.router:7447``).
* ``my.zenoh.router:7447`` is the router address.
* ``my-servient`` is the servient ID used as a namespace to avoid collisions between servients using the same router.
* ``property/requests/benchmark-thing/currenttime`` is the topic where messages are exchanged for this specific interaction and verb.

.. note:: The `zenoh+<transport>` URL scheme is not standard but is used internally to select the appropriate protocols.


Topics
------

There are six different types of topics used by clients and servers of the Zenoh binding to exchange messages:

==================  ===========
Topic               Pattern
==================  ===========
Property request    ``<servient_id>/property/requests/<thing_name>/<property_name>``
Property update     ``<servient_id>/property/updates/<thing_name>/<property_name>``
Property write ACK  ``<servient_id>/property/ack/<thing_name>/<property_name>``
Action invocation   ``<servient_id>/action/invocation/<thing_name>/<action_name>``
Action result       ``<servient_id>/action/result/<thing_name>/<action_name>``
Event emission      ``<servient_id>/event/<thing_name>/<event_name>``
==================  ===========

The format of the messages published in these topics and the way the binding interfaces with them is described in the next section.

Interaction Model mapping
-------------------------

.. note:: There is no need to manually manage subscriptions as the Zenoh server maintains an internal subscription to all properties and events throughout its lifetime.

Read Property
^^^^^^^^^^^^^

The client may publish a message in the **property request** topic to force the server to publish the current value of the property::

    {
        "action": "read"
    }

The property value will be published in the **property update** topic::

    {
        "value": <property_value>,
        "timestamp": <unix_timestamp_ms>
    }

Observe Property changes
^^^^^^^^^^^^^^^^^^^^^^^^

All property changes are automatically published in the **property update** topic without further intervention from the client::

    {
        "value": <property_value>,
        "timestamp": <unix_timestamp_ms>
    }

Write Property
^^^^^^^^^^^^^^

To update the value of a property, the client will publish a message in the **property request** topic with the following format::

    {
        "action": "write",
        "value": <property_value>,
        "ack": <unique_ack_handler>
    }

The server will acknowledge the write by publishing a message in the **property write ACK** topic::

    {
        "ack": <unique_ack_handler>
    }

Invoke Action
^^^^^^^^^^^^^

An invocation may be started by publishing a message in the **action invocation** topic::

    {
        "id": <unique_invocation_handler>,
        "input": <action_argument>
    }

The invocation result will be published in the **action result** topic::

    {
        "id": <unique_invocation_handler>,
        "timestamp": <unix_timestamp_ms>,
        "result" <result_value>,
        "error": <error_message>
    }

Observe Event
^^^^^^^^^^^^^

All event emissions are automatically published in the **event emission** topic without further intervention from the client::

    {
        "name": <event_name>,
        "data": <event_payload>,
        "timestamp": <unix_timestamp_ms>
    }

