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


async def invoke_action(
    websocket,
    action_name: str,
    args: list | None,
    context: str,
) -> dict | None:
    if args is None:
        args = []

    request = {
        "type": "action",
        "name": action_name,
        "args": args,
        "context": context,
    }

    return await send_request(websocket, request)


async def main() -> None:
    websocket = None
    try:
        websocket = await websockets.connect(URI)
        print(f"Connected to {URI}")

        start_response = await invoke_action(
            websocket,
            "recorder.start",
            ["My Recording name"],
            "action-start-recording",
        )
        if start_response is None:
            return

        print(f"Start recording response: {start_response}")
        print(f"Recording id: {start_response.get('value')}")

        print("Waiting for 5 seconds before stopping recording...")
        await asyncio.sleep(5)

        stop_response = await invoke_action(
            websocket,
            "recorder.stop",
            None,
            "action-stop-recording",
        )
        if stop_response is None:
            return

        print(f"Stop recording response: {stop_response}")
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
