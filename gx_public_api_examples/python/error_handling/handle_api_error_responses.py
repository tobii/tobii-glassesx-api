import asyncio
import json

import websockets


URI = "ws://192.168.1.138:49152"  # Replace with your device IP/host, keep port 49152 and passphrase empty


def parse_api_response(response, action_name):
    if "error" in response:
        error_info = response["error"]
        print(f"\nAPI error on {action_name}:")

        if isinstance(error_info, dict):
            error_code = error_info.get("code", "unknown_error")
            error_message = error_info.get("msg", "No message provided")
            error_request = error_info.get("request")

            print(f"  Code: {error_code}")
            print(f"  Message: {error_message}")

            if error_request is not None:
                print(f"  Request: {error_request}")
        else:
            print(f"  Message: {error_info}")

        context = response.get("context")
        if context:
            print(f"  Context: {context}")

        print(f"  Full response: {response}")
        return None

    return response.get("value")


async def send_request(websocket, request: dict) -> dict | None:
    await websocket.send(json.dumps(request))
    response_raw = await websocket.recv()
    response = json.loads(response_raw)
    return response


async def invoke_action(websocket, action_name, args, context):
    request = {
        "type": "action",
        "name": action_name,
        "args": args,
        "context": context,
    }

    try:
        response = await send_request(websocket, request)
        return parse_api_response(response, action_name)

    except Exception as error:
        print(f"Error: {error}")
        return None


async def main():
    websocket = None
    try:
        websocket = await websockets.connect(URI)
        print(f"Connected to {URI}")
        print("Demonstrating centralized API error response handling\n")

        print("--- Example 1: Valid action ---")
        result = await invoke_action(
            websocket,
            "api.ping",
            [],
            "test-api-ping",
        )
        if result is not None:
            print(f"Success: {result}\n")

        print("--- Example 2: Invalid action ---")
        result = await invoke_action(
            websocket,
            "invalid.action.name",
            [],
            "test-invalid-action",
        )
        if result is None:
            print("Error was handled gracefully\n")

        print("--- Example 3: Valid action with invalid arguments ---")
        result = await invoke_action(
            websocket,
            "recorder.start",
            ["arg1", "arg2", "arg3"],  # Too many args
            "test-invalid-args",
        )
        if result is None:
            print("Error was handled gracefully\n")

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
