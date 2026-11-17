import asyncio
import json
import shutil
import urllib.request
from pathlib import Path
from urllib.parse import unquote

import websockets


URI = "ws://192.168.1.138:49152"  # Replace with your device IP/host, keep port 49152
PASS_PHRASE = ""  # Set to the passphrase in Glasses X application, if it has one
HEADERS = {"X-GX-App-Passphrase": PASS_PHRASE} if PASS_PHRASE else {}
HTTP_BASE_URL = URI.replace("ws://", "http://", 1)
OUTPUT_DIRECTORY = Path("downloads")


async def invoke_action(websocket, action_name: str, args: list, context: str):
    request = {
        "type": "action",
        "name": action_name,
        "args": args,
        "context": context,
    }
    await websocket.send(json.dumps(request))
    response = json.loads(await websocket.recv())

    if "error" in response:
        raise RuntimeError(response["error"]["msg"])

    return response["value"]


def download_file(url: str, target: Path) -> None:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request) as response, target.open("wb") as file:
        shutil.copyfileobj(response, file)


async def main() -> None:
    websocket = None
    try:
        websocket = await websockets.connect(URI, additional_headers=HEADERS)
        print(f"Connected to {URI}")

        folder_names = await invoke_action(
            websocket,
            "recordings.list",
            [],
            "action-list-recordings",
        )
        if not folder_names:
            raise RuntimeError("No recordings are saved in local mode")

        folder_name = folder_names[-1]
        paths = await invoke_action(
            websocket,
            "recordings.files.list",
            [folder_name],
            "action-list-recording-files",
        )

        folder = OUTPUT_DIRECTORY / folder_name
        folder.mkdir(parents=True, exist_ok=True)

        for path in paths:
            target = folder / Path(unquote(path)).name
            print(f"Downloading {target.name}")
            await asyncio.to_thread(download_file, HTTP_BASE_URL + path, target)

        print(f"Downloaded {len(paths)} files to {folder}")
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
