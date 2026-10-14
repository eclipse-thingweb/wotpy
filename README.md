<!-- Copyright (c) 2026 Contributors to the Eclipse Foundation -->

<h1>
  <picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/eclipse-thingweb/thingweb/master/brand/logos/wotpy_for_dark_bg.svg">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/eclipse-thingweb/thingweb/master/brand/logos/wotpy.svg">
  <img title="ThingWeb wotpy" alt="Thingweb wotpy logo" src="https://raw.githubusercontent.com/eclipse-thingweb/thingweb/master/brand/logos/wotpy.svg" width="300">
</picture>
</h1>

> A WoT runtime in Python for Thing and Consumer applications

## Introduction

wotpy is an implementation of a [W3C WoT Runtime](https://github.com/w3c/wot-architecture/blob/master/proposals/terminology.md#wot-runtime) and the [W3C WoT Scripting API](https://github.com/w3c/wot-architecture/blob/master/proposals/terminology.md#scripting-api) in Python.

You can find the documentation at <https://eclipse-thingweb.github.io/wotpy/>.

### About the current version

Please note that there's still a **significant pending issue**. Although the project is currently in a reasonably stable state, it does not implement the current version of the W3C WoT specifications. Specifically, the version at the time of writing is based on the following **outdated** references:

* K. Kajimoto, M. Kovatsch, and U. Davuluru, ‘Web of Things (WoT) Architecture’, W3C, W3C First Public Working Draft, Sep. 2017. [Online]. Available: https://www.w3.org/TR/2017/WD-wot-architecture-20170914/
* Z. Kis, K. Nimura, D. Peintner, and J. Hund, ‘Web of Things (WoT) Scripting API’, W3C, W3C Working Draft, Nov. 2018. [Online]. Available: https://www.w3.org/TR/2018/WD-wot-scripting-api-20181129/
* S. Käbisch and T. Kamiya, ‘Web of Things (WoT) Thing Description’, W3C, W3C Working Draft, Oct. 2018. [Online]. Available: https://www.w3.org/TR/2018/WD-wot-thing-description-20181021/

> ℹ️ It is in our plans to get wotpy up to speed with the latest version of the specifications. We don't have an ETA for this, but we will be working on it in the near future.
>
> If you are looking for a Python-like reference for the current Scripting API, see [the `WoT` namespace definition](https://w3c.github.io/wot-scripting-api/#the-wot-namespace) in the W3C WoT Scripting API specification. The canonical reference implementation is [node-wot](https://github.com/eclipse-thingweb/node-wot).

In summary, wotpy is mature enough to be used in projects; in fact, it is being used in production at [CTIC](https://github.com/fundacionctic). However, it is not an adequate representation of the current status of the W3C WoT. We greatly encourage you to check the [Developer Resources section on the WoT website](https://www.w3.org/WoT/developers) to find out about the current state of the art.

## Features

The wotpy project provides fully functional implementations of four different protocol bindings: MQTT, HTTP, WebSockets, and CoAP. Moreover, it offers a discovery implementation based on Multicast DNS.

These bindings are built on top of the following dependencies, which are instrumental to the project:

|            Feature  | Implementation based on                                                      |
| ------------------: | ---------------------------------------------------------------------------- |
|       HTTP binding  | [tornadoweb/tornado](https://github.com/tornadoweb/tornado)                  |
| WebSockets binding  | [tornadoweb/tornado](https://github.com/tornadoweb/tornado)                  |
|       CoAP binding  | [chrysn/aiocoap](https://github.com/chrysn/aiocoap)                          |
|       MQTT binding  | [sbtinstruments/aiomqtt](https://github.com/sbtinstruments/aiomqtt)          |
|       Zenoh binding | [eclipse-zenoh/zenoh-python](https://github.com/eclipse-zenoh/zenoh-python)  |


## Installation
```sh
pip install wotpy
```

### Development

The development workflow of wotpy is based on [Taskfile](https://taskfile.dev/installation/) v3.28 or later, so that's the first thing you need to install. If you are on Windows, see [Running tests on Windows](#running-tests-on-windows).

Then, to create a virtual environment under `.venv`, and install the project in development mode with all the test dependencies, run:
* Using `pip`:
```sh
task venv
```
* Using `uv`:
```sh
task uv-venv
```

If `task` is not available or you have an older version, you can run the underlying commands directly:
* Using `pip`:
```sh
python3 -m venv .venv
.venv/bin/pip install -U -e ".[tests]"
```
* Using `uv`:
```sh
uv venv .venv
uv sync --extra tests
```

### Documentation

The docs are built with [Sphinx](https://www.sphinx-doc.org/). Install the docs dependencies first:

```sh
pip install -e ".[docs]"
```

Or with `uv`:

```sh
uv sync --extra docs
```

Then build from the `docs/` directory:

```sh
cd docs
make html
```

The output is written to `docs/_build/html/`. Open `docs/_build/html/index.html` in a browser to preview. Use `make clean html` to force a full rebuild.

## Running tests on Windows

Some wotpy features (e.g., the CoAP binding) are not available outside of Linux. If you have Docker installed and want to run the full test suite in a Linux environment, you can use the Docker-based test task:

```sh
$ PYTHON_TAG="3.10" task docker-tests
task: [test-broker] docker run -d -p 1883:1883 --name wotpy_test_broker eclipse-mosquitto:1.6

68bfef102faf3529427e5c7122f41d43490885c04f8a2d673a2c57b3afd68f72
task: [docker-tests] echo "⚙️ Running tests for Python 3.10..."
⚙️ Running tests for Python 3.10...
task: [docker-tests] PWD/wotpy/pytest-docker.sh
Running python tests for version 3.10 with arguments "-v"
Creating temporary container volume
wotpy_tests_28b82c629b354b83a7fa22a9ed3d6dba
Running test container. Environment setup will take a while.
+ docker run --rm -it -v wotpy_tests_28b82c629b354b83a7fa22a9ed3d6dba:/app -e WOTPY_TESTS_MQTT_BROKER_URL=mqtt://172.16.102.196:1883 python:3.10 /bin/bash -c 'cd /app && pip install --quiet -U .[tests] && pytest -v'
WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager. It is recommended to use a virtual environment instead: https://pip.pypa.io/warnings/venv

[notice] A new release of pip is available: 23.0.1 -> 23.3.1
[notice] To update, run: pip install --upgrade pip
================================================================================================================================================== test session starts ===================================================================================================================================================
platform linux -- Python 3.10, pytest-7.4.2, pluggy-1.3.0 -- /usr/local/bin/python
cachedir: .pytest_cache
rootdir: /app
configfile: pytest.ini
plugins: asyncio-0.21.1, rerunfailures-10.3, Faker-13.16.0, cov-2.5.1
asyncio: mode=strict
collected 154 items

tests/codecs/test_json.py::test_json_codec PASSED [  0%]
tests/protocols/test_protocols.py::test_all_protocols_combined PASSED [  1%]

[...]

================================================================================================================================== 148 passed, 6 skipped, 1 warning in 60.70s (0:01:00) ==================================================================================================================================
+ set +x
wotpy_tests_28b82c629b354b83a7fa22a9ed3d6dba
task: [docker-tests] echo "✅ Tests for Python 3.10 completed successfully"
✅ Tests for Python 3.10 completed successfully
```

An MQTT broker is needed as a dependency for the MQTT binding tests. The task will automatically create a new container based on the [eclipse-mosquitto image](https://hub.docker.com/_/eclipse-mosquitto) and expose the broker port to the host. The `WOTPY_TESTS_MQTT_BROKER_URL` environment variable will be set to the broker URL.

## Publishing New Versions

Do not change version numbers manually. Always use the `version.sh` script to manage releases.

Before running any release steps, ensure your working directory is clean, recreate your virtual environment and reinstall dependencies:

```bash
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
.venv/bin/pip install -U -e ".[dev]"
```

Publishing is a two-step process:

### 1. Prepare the Release Branch

Run `prepare` with the desired bump component (`major`, `minor`, or `patch`):

```bash
./version.sh prepare minor
```

This step will:
- Check out and pull the latest `develop` branch from the `upstream` remote
- Calculate the target version and create a new branch: `release/v<NEW_VERSION>`
- Bump the version files without tagging
- Push the release branch to the `origin` remote which is assumed to be a fork

Open a Pull Request from `<origin>:release/v<NEW_VERSION>` into `<upstream>:develop` and ensure it gets reviewed and merged.

### 2. Trigger the Release

Once the Pull Request is merged into `develop`, run:

```bash
./version.sh release
```

This step will:
- Pull the latest `develop` containing the merged version bump from `upstream`
- Merge `develop` into `master` locally
- Create an annotated Git tag (`v<VERSION>`) on `master`
- Push both `master` and the release tag to the `upstream` repo, triggering the automated release workflow
