import asyncio
import json
import logging
import time

import zenoh

from wotpy.protocols.modbus.client import ModbusClient
from wotpy.wot.servient import Servient

MODBUS_HOST = '[::1]'
MODBUS_PORT = 1502
UNIT_ID = 1
START_ADDRESS = 0
QUANTITY = 4
ZENOH_KEY = 'test/modbus'

WRITE_ENABLED = False
WRITE_VALUES = [1234, 5678, 9012, 3456]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("logger")

TD = {
    "@context": "https://www.w3.org/2022/wot/td/v1.1",
    "id": "urn:modbus:zenoh:bridge",
    "title": "Modbus sim",
    "securityDefinitions": {"nosec": {"scheme": "nosec"}},
    "security": "nosec",
    "base": "modbus+tcp://{}:{}/{}".format(MODBUS_HOST, MODBUS_PORT, UNIT_ID),
    "properties": {
        "registers": {
            "type": "array",
            "items": {"type": "integer"},
            "forms": [
                {
                    "op": ["readproperty", "writeproperty"],
                    "href": "/{}?quantity={}".format(START_ADDRESS, QUANTITY),
                    "modv:entity": "HoldingRegister"
                }
            ]
        }
    }
}


async def write_test(consumed_thing):
    logger.info(f"Writing {WRITE_VALUES} to holding registers starting at {START_ADDRESS}")
    await consumed_thing.properties["registers"].write(WRITE_VALUES)

    readback = await consumed_thing.properties["registers"].read()

    if list(readback) == WRITE_VALUES:
        logger.info(f"Write verified: {readback}")
    else:
        logger.warning(f"Write mismatch: wrote {WRITE_VALUES}, read {readback}")


async def main():
    logger.info("Opening Zenoh session...")
    conf = zenoh.Config()
    # conf.insert_json5("listen/endpoints", '["tcp/127.0.0.1:7447"]')

    z_session = zenoh.open(conf)

    logger.info(f"Consuming Modbus Thing at {MODBUS_HOST}:{MODBUS_PORT}...")
    servient = Servient(clients=[ModbusClient()])
    wot = await servient.start()
    consumed_thing = wot.consume(json.dumps(TD))

    try:
        if WRITE_ENABLED:
            await write_test(consumed_thing)

        while True:
            try:
                values = await consumed_thing.properties["registers"].read()
            except Exception as ex:
                logger.error(f"Modbus Error: {ex}")
            else:
                data = {
                    "timestamp": time.time(),
                    "values": list(values)
                }
                z_session.put(ZENOH_KEY, json.dumps(data))
                logger.info(f"Published: {values}")

            await asyncio.sleep(2)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await servient.shutdown()
        z_session.close()


if __name__ == "__main__":
    asyncio.run(main())