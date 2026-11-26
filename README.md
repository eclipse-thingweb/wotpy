<!-- Copyright (c) 2026 Contributors to the Eclipse Foundation -->

<h1>
  <picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/eclipse-thingweb/thingweb/master/brand/logos/wotpy_for_dark_bg.svg">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/eclipse-thingweb/thingweb/master/brand/logos/wotpy.svg">
  <img title="ThingWeb wotpy" alt="Thingweb wotpy logo" src="https://raw.githubusercontent.com/eclipse-thingweb/thingweb/master/brand/logos/wotpy.svg" width="300">
</picture>
</h1>

[![PyPI version](https://img.shields.io/pypi/v/wotpy.svg?style=flat-square)](https://pypi.org/project/wotpy/)
[![Python Versions](https://img.shields.io/pypi/pyversions/wotpy.svg?style=flat-square)](https://pypi.org/project/wotpy/)
[![License](https://img.shields.io/github/license/eclipse-thingweb/wotpy.svg?style=flat-square)](https://github.com/eclipse-thingweb/wotpy/blob/master/LICENSE)
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/eclipse-thingweb/wotpy/test-wotpy.yaml?branch=master&style=flat-square&label=tests)](https://github.com/eclipse-thingweb/wotpy/actions)
[![Documentation Status](https://img.shields.io/badge/docs-latest-blue.svg?style=flat-square)](https://eclipse-thingweb.github.io/wotpy/)

> A WoT runtime in Python for Thing and Consumer applications

## Introduction

wotpy is an implementation of a [W3C WoT Runtime](https://github.com/w3c/wot-architecture/blob/master/proposals/terminology.md#wot-runtime) and the [W3C WoT Scripting API](https://github.com/w3c/wot-architecture/blob/master/proposals/terminology.md#scripting-api) in Python.

## Documentation

See the [wotpy documentation](https://eclipse-thingweb.github.io/wotpy/).

## About the current version

⚠️ Please note that there's still a **significant pending issue**. Although the project is currently in a reasonably stable state, it does not implement the current version of the W3C WoT specifications. Specifically, the version at the time of writing is based on the following **outdated** references:

* K. Kajimoto, M. Kovatsch, and U. Davuluru, ‘Web of Things (WoT) Architecture’, W3C, W3C First Public Working Draft, Sep. 2017. [Online]. Available: https://www.w3.org/TR/2017/WD-wot-architecture-20170914/
* Z. Kis, K. Nimura, D. Peintner, and J. Hund, ‘Web of Things (WoT) Scripting API’, W3C, W3C Working Draft, Nov. 2018. [Online]. Available: https://www.w3.org/TR/2018/WD-wot-scripting-api-20181129/
* S. Käbisch and T. Kamiya, ‘Web of Things (WoT) Thing Description’, W3C, W3C Working Draft, Oct. 2018. [Online]. Available: https://www.w3.org/TR/2018/WD-wot-thing-description-20181021/

> ℹ️ It is in our plans to get wotpy up to speed with the latest version of the specifications. We don't have an ETA for this, but we will be working on it in the near future.
>
> If you are looking for a Python-like reference for the current Scripting API, see [the `WoT` namespace definition](https://w3c.github.io/wot-scripting-api/#the-wot-namespace) in the W3C WoT Scripting API specification. The canonical reference implementation is [node-wot](https://github.com/eclipse-thingweb/node-wot).

In summary, wotpy is mature enough to be used in projects; in fact, it is being used in production at [CTIC](https://github.com/fundacionctic). However, it is not an adequate representation of the current status of the W3C WoT. We greatly encourage you to check the [Developer Resources section on the WoT website](https://www.w3.org/WoT/developers) to find out about the current state of the art.

## Protocol Support

The wotpy project provides implementations of these protocol bindings:
- HTTP
- WebSockets
- CoAP
- MQTT
- Zenoh
- Modbus

These bindings are built on top of the following dependencies, which are instrumental to the project:

| Feature             | Implementation based on                                                      | Client | Server |
| ------------------- | ---------------------------------------------------------------------------- | :----: | :----: |
| HTTP binding        | [tornadoweb/tornado](https://github.com/tornadoweb/tornado)                  | ✔️     | ✔️     |
| WebSockets binding  | [tornadoweb/tornado](https://github.com/tornadoweb/tornado)                  | ✔️     | ✔️     |
| CoAP binding        | [chrysn/aiocoap](https://github.com/chrysn/aiocoap)                          | ✔️     | ✔️     |
| MQTT binding        | [Yakifo/amqtt](https://github.com/Yakifo/amqtt)                              | ✔️     | ✔️     |
| Zenoh binding       | [eclipse-zenoh/zenoh-python](https://github.com/eclipse-zenoh/zenoh-python)  | ✔️     | ✔️     |
| Modbus binding      | [pymodbus-dev/pymodbus](https://github.com/pymodbus-dev/pymodbus)            | ✔️     | -      |

## Installation
Install wotpy using pip:
```sh
pip install wotpy
```

### Development

The development workflow of wotpy is based on [Taskfile](https://taskfile.dev/installation/) v3.28 or later, so that's the first thing you need to install. If you are on Windows, see [Running tests on Windows](#running-tests-on-windows).

Create a `.venv` virtual environment and install the project in development mode with its development, documentation, and test dependencies.

Using `pip`:

```bash
task venv
```

Using `uv`:

```bash
task uv-venv
```

If `task` is not available or you have an older version, you can run the underlying commands directly:

Using `pip`:

```sh
python3 -m venv .venv
.venv/bin/pip install -U -e ".[dev,docs,tests]"
```

Using `uv`:

```sh
uv venv .venv
uv sync --extra dev --extra docs --extra tests
```

### Building the documentation

The docs are built with [Sphinx](https://www.sphinx-doc.org/), which is installed with the development dependencies above. Build them from the `docs/` directory:

```sh
cd docs
make html
```

The output is written to `docs/_build/html/`. Open `docs/_build/html/index.html` in a browser to preview. Use `make clean html` to force a full rebuild.

## Running tests on Windows

Some wotpy features (e.g., the CoAP binding) are not available outside of Linux. If you have Docker installed and want to run the full test suite in a Linux environment, you can use the Docker-based test task:

```sh
PYTHON_TAG=<version> task docker-tests
```

Replace `<version>` with the Python version you want to test. The task starts the MQTT broker and Zenoh router required by the tests and sets the corresponding environment variables.

## Publishing New Versions

You should use the `version.sh` file and not change any versions anywhere manually.
Running `version.sh minor` will bump the minor version, push the tags and update the master branch and also trigger the release.
Make sure to clear the `.venv` environment and reinstall the packages before publishing.
An unclean tree will fail the script, i.e. the develop branch must be in a clean state first.

Note: This can be only used by those who have force push rights to the develop branch. See [here](https://github.com/eclipse-thingweb/wotpy/issues/39).

