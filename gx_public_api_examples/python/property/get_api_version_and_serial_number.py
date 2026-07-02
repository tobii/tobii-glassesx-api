import asyncio
import json

import websockets


URI = "ws://192.168.1.138:49152"  # Replace with your device IP/host, keep port 49152 and passphrase empty


async def send_request(websocket, request: dict) -> dict | None:
    await websocket.send(json.dumps(request))
    response_raw = await websocket.recv()
    response = json.loads(response_raw)

    if "error" in response:
        print(f"Error: {response['error']}")
        return None

    return response


async def get_property(websocket, property_name: str, context: str) -> str | None:
    request = {
        "type": "property-get",
        "name": property_name,
        "context": context,
    }

    response = await send_request(websocket, request)
    if response is None:
        return None

    return response.get("value")


async def main() -> None:
    websocket = None
    try:
        websocket = await websockets.connect(URI)
        print(f"Connected to {URI}")

        version = await get_property(websocket, "api.version", "property-api-version")
        if version is None:
            return
        print(f"api.version: {version}")

        serial = await get_property(
            websocket,
            "glasses.serial_number",
            "property-glasses-serial-number",
        )
        if serial is None:
            return
        print(f"glasses.serial_number: {serial}")
    except (asyncio.TimeoutError, TimeoutError) as error:
        print(f"Connection timeout: {error}")
        print("Make sure Public API is enabled and the URI matches your device.")
    except Exception as error:
        print(f"Error: {error}")
    finally:
        if websocket is not None:
            try:
                await websocket.close()
                print("Disconnected")
            except Exception as error:
                print(f"Error: {error}")


if __name__ == "__main__":
    asyncio.run(main())
