# Python API examples

Runnable Python examples for the Glasses X Public API.



Each example connects to the Glasses X application WebSocket server and shows one part of the API. For a connection and protocol overview, see the published API Quick Start. For the full API surface, see the generated Glasses X Public API reference for your release.



All examples follow the same general flow:

* Define the URI and other constants near the top of the file.
* Connect with `websockets.connect(...)`.
* Build and send API requests as JSON payloads.
* Parse responses and handle errors clearly.
* Print lifecycle logs and close the connection cleanly.

## Prerequisites

* Python 3.10 or later
* [`uv`](https://docs.astral.sh/uv/) installed
* Glasses X application running on the device with **Public API** enabled
* The device and the computer on the same network

## Set up

From the `python` folder, sync dependencies:

```bash
uv sync
```

`websockets` is required for all examples.

`aiortc` and `opencv-python` are required only for the `live_view` example.

## Configure the endpoint

Each example file defines a `URI` constant near the top. Replace the IP address with the address shown on the **Public API** page in Glasses X application:

```python
URI = "ws://192.168.x.y:49152"
```

Port `49152` is fixed.

If a passphrase is set in Glasses X application, send it in the `X-GX-App-Passphrase` header during the WebSocket upgrade and with each recording download. This applies only to native clients. Browsers can't set custom headers.

## Troubleshooting

### Connection refused or timeout

* Verify the device IP address in `URI`.
* Make sure the device and the computer are on the same network.
* Confirm that Glasses X application is running and **Public API** is enabled.

### Authentication or handshake failure

* Check that the `X-GX-App-Passphrase` value matches the passphrase configured in Glasses X application.
* If no passphrase is configured, use the example without passphrase headers.

### `live_view` dependency errors

If `aiortc` or `cv2` imports fail:

* Reinstall dependencies from this folder.
* Make sure you use Python 3.10 or later.
* Make sure you install and run the examples in the same Python environment.

```bash
uv sync --reinstall
```

## Examples

### Connect

**File:** `connect/connect_without_passphrase.py`

Connects to Glasses X application, keeps the WebSocket open for five seconds, and then disconnects cleanly.

```bash
uv run python ./connect/connect_without_passphrase.py
```

### Connect with passphrase

**File:** `connect/connect_with_passphrase.py`

Connects to Glasses X application by using the `X-GX-App-Passphrase` header, keeps the WebSocket open for five seconds, and then disconnects cleanly.

```bash
uv run python ./connect/connect_with_passphrase.py
```

### Read properties

**File:** `property/get_api_version_and_serial_number.py`

Connects once and reads multiple properties over the same WebSocket connection:

* `api.version`
* `glasses.serial_number`

```bash
uv run python ./property/get_api_version_and_serial_number.py
```

### Start and stop recording

**File:** `action/start_and_stop_recording.py`

Starts a recording with `recorder.start`, waits briefly, stops it with `recorder.stop`, and prints the returned recording summary.

```bash
uv run python ./action/start_and_stop_recording.py
```

### Download a recording

**File:** `recordings/download_recording.py`

Downloads the recording in the last folder of the list that `recordings.list` returns. The list is sorted by folder name, so with the default timestamp names this is the newest recording. The example:

* Lists the saved recordings with `recordings.list`, and stops with an error if there are none.
* Gets the download paths of the last folder in the list with `recordings.files.list`.
* Downloads each file with HTTP GET into `downloads/<folder name>`.
* Sends the passphrase in `PASS_PHRASE` with each request, if you set one.

Glasses X application must be in local mode.

```bash
uv run python ./recordings/download_recording.py
```

### Handle API errors

**File:** `error_handling/handle_api_error_responses.py`

Shows centralized API response parsing with detailed error handling. The example:

* Extracts the API message.
* Extracts the original request.
* Extracts the response context.
* Shows both success and error cases, including invalid actions and invalid arguments.

```bash
uv run python ./error_handling/handle_api_error_responses.py
```

### Subscribe to a signal

**File:** `signal/glasses_isconnected_subscribe_unsubscribe.py`

Subscribes to `glasses.is_connected`, prints updates for 10 seconds, unsubscribes, and then closes the connection cleanly.

```bash
uv run python ./signal/glasses_isconnected_subscribe_unsubscribe.py
```

### Live view with WebRTC

**File:** `live_view/live_view.py`

Shows the full WebRTC live view flow:

* Creates a WebRTC session with `live_viewer.session.create`. It asks for clean video and the `gaze2d` and `timesync` channels. See [Choose the streams](../../GX_App_Public_API_Guide.md#choose-the-streams) for the other streams.
* Subscribes to remote ICE candidates with `live_viewer.ice_candidate.discovered`.
* Gets the SDP offer with `live_viewer.offer.create`.
* Creates and sends an SDP answer with `live_viewer.session.start`.
* Exchanges ICE candidates in both directions.
* Renders incoming video in an OpenCV window.
* Draws the gaze point from the `gaze2d` and `timesync` data channels over the video.
* Reports disconnected glasses, setup errors, or missing video tracks in the console.

To match gaze to a frame, the example keeps the latest 4096 `timesync` entries and draws the closest `gaze2d` sample if it is within 10 ms of the frame. By default, `aiortc` changes the RTP timestamps to start at 0, so the example replaces its timestamp mapper to keep them unchanged.

Close the video window to stop. The session is cleaned up automatically.

`aiortc` and `opencv-python` are included in `pyproject.toml`.

```bash
uv run python ./live_view/live_view.py
```

