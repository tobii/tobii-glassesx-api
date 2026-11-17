# Glasses X Application Public API Guide

This guide explains how to connect to the Glasses X Application Public API, understand the request and response model, and use the generated reference and examples.



##### How to use this guide

Use the documents in this order:

1. Read this guide for setup, message flow, and common patterns.
2. Use the generated API reference (gx_api_<version>.md and .json) as the source of truth for properties, signals, actions, and payloads.
3. Use the Python examples (README.md and scripts) for runnable client code.



### About the API

The Glasses X Application Public API exposes a WebSocket server on the device.



External clients can:

* Read current device state using **properties**
* Trigger commands using **actions**
* Receive real-time updates using **signals**
* Receive live video using **WebRTC actions** and **signals**
* Receive live gaze data on **WebRTC data channels**



The generated API reference defines all available endpoints and payloads.



The API surface is documented in the generated Glasses X app Public API references for your release, typically named **gx_api_<version>.md** and
**gx_api_<version>.json**.





### Connect to the API

### 

##### Enable access



1. Launch the Glasses X application on the phone.
2. Go to **Settings.**
3. Enable **Allow remote access: Live stream + recording control (via API)**.
4. Set up the API in the app.
5. Copy the endpoint.



###### Endpoint format:

ws://<device-ip>:49152



Port `**49152**` is fixed.



##### Security notice

The API uses **ws** (WebSocket), not **wss**.



* Traffic is not TLS encrypted
* Data can be intercepted or read by anyone with network access.
* Recording downloads use plain HTTP.



Use the API only on a trusted, private, secure network.



##### Network requirements

* The client and the Glasses X App device must be on the same network.
* Use the IP address shown in the API setup UI.
* Only one client can be connected at a time.



##### Authentication

If a passphrase is configured:

* Send it in the **X-GX-App-Passphrase** header during connection and with each recording download.
* Missing or incorrect values return HTTP 401



If no passphrase is configured:

* Do not send the `X-GX-App-Passphrase` header.
* Sending it returns a HTTP 401 error.



Additional clients that try to connect simultaneously are rejected with a 403 error type.

###### 

###### Browser limitation:

Browsers may not support custom headers during connection.

* Browser clients often require no passphrase
* Python and other clients can send headers normally



In practice, a browser client can only connect when the Glasses X app API setup is configured without a passphrase.





### API model

The API uses three request types: properties, actions, and signals.





##### Properties (read state)

Properties let you read the current state of the device.



###### Example

Get current app version



Request:

```json
{ "type": "property-get", "name": "api.version" }
```

Response:

```json
{ "value": "2.2.0" }
```

##### 

##### Actions (run commands)

Allow you to run commands.



Send arguments as an ordered JSON list in **args**.The order must match the generated API reference for that action.



###### Example

Start a recording



Request:

```json
{ "type": "action", "name": "recorder.start", "args": ["My Recording"] }
```

Response:

```json
{ "value": "recording-id-123" }
```



##### Signals (subscribe to updates)

Signals push asynchronous updates from Glasses X App to client.

###### 

###### Example

Recording status



Request (Subscribe):

```json
{ "type": "signal-subscribe", "name": "recorder.is_recording" }
```

Response (Subscription confirmation):

```json
{ "signal-id": 1 }
```



Response update:

```json
{ "signal-id": 1, "value": true }
```



To stop receiving updates



Request:

```json
{ "type": "signal-unsubscribe", "signal-id": 1 }
```



### Match requests and responses

Use `**context**` to associate a response with a specific request.



###### Example

xxxxxx



Request:

```json
{ "type": "action", "name": "recorder.start", "args": ["My Recording"], "context": 42 }
```

Response:

```json
{ "context": 42, "value": "recording-id-123" }
```

For scripts that send one request at a time, using `**context**` is optional. For clients that pipeline requests or combine subscriptions with request /
response traffic, it is strongly recommended to use `**context**`.





### Use the API Reference

The generated reference (gx_api_<version>.md) for your release is the authoritative reference for:



* Property names
* Action names and argument order
* Signal names
* Return types
* Payload formats
* Error codes (see `## Error Codes` section)



###### Key rules 

Pay special attention to these details:



* Send action `arguments` in the documented order.
* Some payloads and return values are documented as `record` types.
* Some payloads use ordered JSON arrays instead of objects. This means that field names are omitted from the wire format, and values must be parsed sequentially by their array index. 
* Error responses use a structured envelope with `error.request`, `error.msg`, and `error.code`. 
* Treat unknown error codes as general failures.



###### Example

For example, `recorder.stop` returns a `record` type, where the fields are documented in the exact sequence they appear in the array. Similarly, the `live_viewer.ice_candidate.discovered` event emits an ordered JSON array payload, requiring positional parsing based on the array index.





### Common patterns

### 

##### Read current state

Use properties when you need the current value.



###### Examples:

* `api.version`
* `glasses.serial_number`
* `recorder.current.id`



##### Run commands

Use actions to trigger behavior.



###### Examples:

* `recorder.start`
* `recorder.stop`
* `live_viewer.session.create`
* `live_viewer.session.start`



##### Subscribe to changes

Use signals for real-time updates.



###### Examples:

* `glasses.is_connected`
* `recorder.is_recording`
* `uploader.progress.changed`



Signals stay active until you unsubscribe or disconnect.



##### Start recording and get current state



###### Sequence:

```text
1. property-get glasses.serial_number
2. signal-subscribe recorder.is_recording
3. action recorder.start ["Test Recording"]
4. handle async signal updates using signal-id
5. action recorder.stop []
6. signal-unsubscribe using the returned signal-id
```



##### Download local recordings

The app serves the recordings that it saved in local mode. On the phone, these are the folders in `Documents/TobiiGlassesX`.



###### Sequence:

```text
1. action recordings.list []                     -> folder names, sorted by name
2. action recordings.files.list ["Store visit"]  -> one download path for each file
3. HTTP GET http://<device-ip>:49152<path> for each download path
```

To download a recording right after you stop it, send the `recording_id` that `recorder.stop` returns to `recordings.files.list`. The app saves the recording a short time after it stops. Until then, the action fails with the error code `recording_not_ready`. Wait, and then send the action again. The same error code applies to a recording that is still running. If the save fails, the action fails with `action_failed`.



###### Rules:

* Downloads work only in local mode. In connected mode, both actions fail with `action_failed`.
* Download paths are URL-encoded. Use them as the app returns them.
* Send each download as an HTTP GET request. The app does not treat other methods, such as HEAD, as downloads.
* Each download is a separate HTTP request on port `49152`. Downloads work while your WebSocket client is connected, and while the app records.
* Download responses allow any origin (`Access-Control-Allow-Origin: *`), so browser clients can download files too.
* A failed download starts again from the beginning. Downloads cannot resume.



|HTTP status|Meaning|
|-|-|
|200|The response body is the file. `Content-Length` gives its size.|
|400|The app cannot decode the download path.|
|401|The passphrase is missing or incorrect, or the app has no passphrase and the request sends one.|
|404|No file matches the download path, or the app is in connected mode.|
|500|The app could not read the file.|



The download example in the Python example set shows this flow.



##### Start live view



###### Sequence:

```text
1. action live_viewer.session.create
2. signal-subscribe live_viewer.ice_candidate.discovered
3. action live_viewer.offer.create
4. create a local WebRTC answer in your client
5. action live_viewer.session.start [answer-sdp]
6. exchange ICE candidates in both directions
7. action live_viewer.session.delete when done
```

The generated reference documents the exact signal payload and action argument
types. The runnable flow is demonstrated in the live view example in the Python
example set.



`live_viewer.session.create` is idempotent while a live view session is active. If
the app already has an active session, the action returns `true` and reuses that
session. A second call with a different `streams` list fails with `action_failed`.
To change the streams, delete the session and create a new one.



##### Choose the streams

The second argument of `live_viewer.session.create` lists the streams you want.
The app sends only these streams, and it does not process the others. The video
track is the one exception, as described below.

|Stream|You get|
|-|-|
|`video`|The scene camera video|
|`video_gaze_overlay`|The scene camera video with the gaze point drawn into each frame. It replaces `video` if you list both.|
|`audio`|The microphone audio, if audio is on in the app|
|`gaze2d`|The `gaze2d` data channel|
|`gaze3d`|The `gaze3d` data channel|
|`timesync`|The `timesync` data channel. It needs `video` or `video_gaze_overlay`.|

If you leave out the argument, you get `video_gaze_overlay` and `audio`, as in API
2.0.0. An empty list, an unknown name, or `timesync` without video fails with
`invalid_args`.

###### Example

```json
{ "type": "action", "name": "live_viewer.session.create", "args": [[], ["video", "gaze2d", "timesync"]] }
```

The first argument is the ICE server list. An empty list works the same as no
list.

The offer always has a video track and an audio track. A track that you did not
choose stays silent, except for video. While someone looks at the live view in
the app, the video track sends video with the gaze point drawn in. This happens
even if you chose `video` or no video stream.



##### Receive gaze data

The live view offer includes the data channels that you chose. Your client
receives them when the peer connection connects, for example through the
`datachannel` event of `RTCPeerConnection`.

|Channel|Content|
|-|-|
|`gaze2d`|One message for each gaze sample, valid or not|
|`gaze3d`|One message for each gaze sample, with the 3D gaze data of each eye and of both eyes combined|
|`timesync`|One message for each encoded video frame|

Each message is one JSON object in a text message. All channels are ordered and
reliable. If your client reads a channel too slowly, the app drops messages on
that channel instead of delaying them.

The gaze messages have the same fields, units, and validity fields as
[`Gaze2D`](GX_App_Recording_Format_Guide.md#gaze2d),
[`Gaze3D`](GX_App_Recording_Format_Guide.md#gaze3d), and
[`Eye`](GX_App_Recording_Format_Guide.md#eye) in a recording. They differ in two
ways:

* A point or a vector is an array, `[x, y]` or `[x, y, z]`.
* A value is `null` when its validity field is `false`.

All timestamps are in [recording time](GX_App_Recording_Format_Guide.md#timestamps),
the same clock as the timestamps in a recording.

###### `gaze2d` message

```json
{ "timestamp_us": 981234567, "gaze": [0.512, 0.377], "valid": true }
```

###### `gaze3d` message

```json
{
  "timestamp_us": 981234567,
  "left": {
    "gaze_origin_valid": true, "gaze_origin_mm": [-31.2, 12.4, -24.8],
    "gaze_direction_valid": true, "gaze_direction_normalized": [0.08, -0.21, 0.97],
    "pupil_diameter_valid": true, "pupil_diameter_mm": 3.6,
    "blink_valid": true, "blink": false
  },
  "right": {
    "gaze_origin_valid": true, "gaze_origin_mm": [30.7, 12.1, -25.3],
    "gaze_direction_valid": true, "gaze_direction_normalized": [0.02, -0.20, 0.98],
    "pupil_diameter_valid": true, "pupil_diameter_mm": 3.5,
    "blink_valid": true, "blink": false
  },
  "gaze_origin_combined_valid": true, "gaze_origin_combined_mm": [-0.3, 12.3, -25.1],
  "gaze_direction_combined_valid": true, "gaze_direction_combined_normalized": [0.05, -0.21, 0.98],
  "convergence_point_valid": true, "convergence_point_mm": [49.7, -197.7, 954.9]
}
```

###### `timesync` message

```json
{ "type": "video_frame_map", "app_frame_id": 12345, "app_timestamp_us": 981234567, "rtp_timestamp": 3456789012 }
```

|Field|Type|Description|
|-|-|-|
|type|string|Always `video_frame_map`.|
|app_frame_id|integer|A frame counter. Your client can ignore it.|
|app_timestamp_us|integer|The recording time of the video frame, in microseconds.|
|rtp_timestamp|integer|The RTP timestamp of the video frame, an unsigned 32-bit value.|



###### Match gaze to video frames

WebRTC does not keep the recording time of a video frame. To draw gaze on a frame:

1. Read the RTP timestamp of the frame. In a browser, it is `metadata.rtpTimestamp` in the `requestVideoFrameCallback` callback of the video element.
2. Find the recording time of the frame in the `timesync` messages.
3. Use the `gaze2d` sample with the closest `timestamp_us`.

The live view example in the Python example set shows this flow.

## 

### Error types

There are two broad categories of errors.



##### Connection errors

Occur before the WebSocket session is open - during the WebSocket
upgrade request.



###### Examples:

* 401 – invalid or missing passphrase
* 403 – another client is connected
* 400 – invalid WebSocket request
* 500 – WebSocket upgrade failure



##### API errors

Occur after WebSocket connection is open. 



API errors are returned as JSON objects with a nested `error` payload that includes the original request, a human-readable message, and a stable error code.



###### Example:



```json
{
	"error": {
		"request": {
			"type": "action",
			"name": "recorder.start",
			"args": [123]
		},
		"msg": "Action "recorder.start" expected argument "name" to be of type String but received int.",
		"code": "invalid_args"
	}
}
```

Error payloads include the original request in `error.request`. If the client
sent `context`, it is echoed at the top level of the response as `context`.
Malformed JSON is reported as `invalid_payload` and uses a placeholder
`error.request` object with `{"type": "unknown"}` because the request could
not be parsed.





### Example Clients



Included Python examples:

* `connect_without_passphrase.py`
* `connect_with_passphrase.py`
* `get_api_version_and_serial_number.py`
* `live_view.py`, which also draws the streamed gaze over the video
* `download_recording.py`, which downloads a recording saved in local mode



See the README.md for setup instructions.





### Troubleshooting

##### 

##### Cannot connect

* Check API access is enabled in the Glasses X app - **Allow remote access: Live stream + recording control (via API)**.
* Verify the IP address, it needs to match the one provided in the Glasses X app.
* Ensure both devices are on the same network.
* Confirm passphrase settings
* Check if another client is already connected.



##### Connected, but requests fail

* Verify the property, signal, or action name exactly matches the generated reference.
* Check action argument order and types.
* Review the returned `error` payload for the request details and stable `error.code`.



##### Signals do not update

* Some signals only emit when the underlying state changes.
* Keep the WebSocket open after subscribing.
* Use the returned `signal-id` to match updates and unsubscribe later.

### 

##### Browser cannot connect

Browsers may not support passphrase headers.



* Disable the passphrase in the Glasses X App API setup for browser-based testing.
* Use a non-browser client if needed. Other clients, such as Python, can send this header normally.

## 

### Summary



* The generated reference describes the API surface.
* This guide explains how the API behaves on the wire and how to interpret it.
* The examples show real client implementations.



Together, these references, documents and samples give a complete starting point for building against the GX App Public API.

