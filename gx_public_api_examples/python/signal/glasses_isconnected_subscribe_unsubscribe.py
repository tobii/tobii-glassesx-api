import asyncio
import json

import websockets


URI = "ws://192.168.1.138:49152"  # Replace with your device IP/host, keep port 49152 and passphrase empty
SIGNAL_NAME = "glasses.is_connected"
LISTEN_SECONDS = 10


async def send_request(websocket, request: dict) -> dict:
    await websocket.send(json.dumps(request))
    expected_context = request["context"]

    while True:
        message = json.loads(await websocket.recv())
        # Signal updates include "value"; request responses do not.
        if message.get("context") == expected_context and "value" not in message:
            return message

        print(f"Signal update: {message}")


async def subscribe(websocket, signal_name: str) -> str:
    subscribe_request = {
        "type": "signal-subscribe",
        "name": signal_name,
        "context": "subscribe",
    }
    response = await send_request(websocket, subscribe_request)
    signal_id = response.get("signal-id")
    print(f"Subscribed with signal-id: {signal_id}")
    return signal_id


async def unsubscribe(websocket, signal_id: str) -> None:
    unsubscribe_request = {
        "type": "signal-unsubscribe",
        "signal-id": signal_id,
        "context": "unsubscribe",
    }
    await send_request(websocket, unsubscribe_request)
    print(f"Unsubscribed from signal-id: {signal_id}")


async def listen_for_updates(websocket) -> None:
    while True:
        update = await websocket.recv()
        data = json.loads(update)
        print(f"Signal update: {data}")


async def main() -> None:
    websocket = None
    try:
        websocket = await websockets.connect(URI)
        print(f"Connected to {URI}")

        signal_id = await subscribe(websocket, SIGNAL_NAME)

        try:
            await asyncio.wait_for(
                listen_for_updates(websocket), timeout=LISTEN_SECONDS
            )
        except asyncio.TimeoutError:
            print(f"Stopped listening after {LISTEN_SECONDS} seconds")

        await unsubscribe(websocket, signal_id)
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
