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



Use the API only on a trusted, private, secure network.



##### Network requirements

* The client and the Glasses X App device must be on the same network.
* Use the IP address shown in the API setup UI.
* Only one client can be connected at a time.



##### Authentication

If a passphrase is configured:

* Send it in the **X-GX-App-Passphrase** header during connection.
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
{ "value": "2.0.0" }
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
session.

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

