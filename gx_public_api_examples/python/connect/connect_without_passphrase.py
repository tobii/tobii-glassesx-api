import asyncio

import websockets


URI = "ws://192.168.1.138:49152"  # Replace with your device IP/host, keep port 49152 and passphrase empty
WAIT_SECONDS = 5


async def main() -> None:
    websocket = None
    try:
        websocket = await websockets.connect(URI)
        print(f"Connected to {URI}")
        print(f"Keeping connection open for {WAIT_SECONDS} seconds...")
        await asyncio.sleep(WAIT_SECONDS)

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
