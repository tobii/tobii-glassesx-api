import asyncio

import websockets
from websockets.exceptions import InvalidHandshake, InvalidStatus


URI = "ws://192.168.1.138:49152"  # Replace with your device IP/host, keep port 49152 and make sure passphrase is correct
PASS_PHRASE = "GX-code-example-passphrase"
WAIT_SECONDS = 5


async def main() -> None:
    headers = {"X-GX-App-Passphrase": PASS_PHRASE}
    websocket = None
    try:
        websocket = await websockets.connect(URI, additional_headers=headers)
        print(f"Connected to {URI} with passphrase header")
        print(f"Keeping connection open for {WAIT_SECONDS} seconds...")
        await asyncio.sleep(WAIT_SECONDS)

    except (asyncio.TimeoutError, TimeoutError) as error:
        print(f"Connection timeout: {error}")
        print("Make sure Public API is enabled and the URI matches your device.")
    except (InvalidStatus, InvalidHandshake) as error:
        print("Connection failed due to authentication/handshake error")
        print(f"Error type: {type(error).__name__}")

        status_code = getattr(error, "status_code", None)
        if status_code is not None:
            print(f"HTTP status code: {status_code}")

        response = getattr(error, "response", None)
        if response is not None:
            response_status = getattr(response, "status_code", None)
            if response_status is not None:
                print(f"HTTP status code: {response_status}")

            response_headers = getattr(response, "headers", None)
            if response_headers is not None:
                print(f"Response headers: {dict(response_headers)}")

        print(f"Error: {error}")
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
