import asyncio
import bisect
import json
from collections import OrderedDict
from collections.abc import Awaitable, Callable

import cv2
import websockets
from aiortc import RTCPeerConnection, RTCSessionDescription, rtcrtpreceiver
from aiortc.sdp import candidate_from_sdp


URI = "ws://192.168.1.138:49152"  # Replace with your device IP/host, keep port 49152 and passphrase empty
GLASSES_CONNECTION_WAIT_SECONDS = 5
MAX_FRAME_MAPS = 4096
MAX_GAZE_SAMPLES = 2048
MAX_GAZE_OFFSET_US = 10_000

SignalHandler = Callable[[dict], Awaitable[None]]


class RtpTimestampPassthrough(rtcrtpreceiver.TimestampMapper):
    def map(self, timestamp: int) -> int:
        return timestamp


rtcrtpreceiver.TimestampMapper = RtpTimestampPassthrough


class GazeMatcher:
    def __init__(self):
        self._frame_times: OrderedDict[int, int] = OrderedDict()
        self._gaze_times: list[int] = []
        self._gaze_points: list[list[float] | None] = []

    def on_message(self, label: str, raw: str):
        message = json.loads(raw)
        if label == "timesync" and message.get("type") == "video_frame_map":
            self._frame_times[message["rtp_timestamp"]] = message["app_timestamp_us"]
            if len(self._frame_times) > MAX_FRAME_MAPS:
                self._frame_times.popitem(last=False)
        elif label == "gaze2d":
            self._gaze_times.append(message["timestamp_us"])
            self._gaze_points.append(message["gaze"])
            if len(self._gaze_times) > MAX_GAZE_SAMPLES:
                del self._gaze_times[0]
                del self._gaze_points[0]

    def gaze_for_frame(self, rtp_timestamp: int) -> list[float] | None:
        frame_time = self._frame_times.get(rtp_timestamp)
        if frame_time is None or not self._gaze_times:
            return None
        index = bisect.bisect_left(self._gaze_times, frame_time)
        nearby = [i for i in (index - 1, index) if 0 <= i < len(self._gaze_times)]
        closest = min(nearby, key=lambda i: abs(self._gaze_times[i] - frame_time))
        if abs(self._gaze_times[closest] - frame_time) > MAX_GAZE_OFFSET_US:
            return None
        return self._gaze_points[closest]


class GxApiClient:
    def __init__(self, uri: str):
        self.uri = uri
        self.websocket = None
        self._context = 1
        self._pending: dict[int, asyncio.Future] = {}
        self._signal_handlers: dict[int, SignalHandler] = {}
        self._buffered_signals: dict[int, list[dict]] = {}
        self._receiver_task: asyncio.Task | None = None

    async def connect(self):
        self.websocket = await websockets.connect(self.uri)
        self._receiver_task = asyncio.create_task(self._receiver_loop())

    async def close(self):
        if self._receiver_task:
            self._receiver_task.cancel()
            try:
                await self._receiver_task
            except asyncio.CancelledError:
                pass

        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            print("Disconnected")

    async def _receiver_loop(self):
        try:
            async for raw in self.websocket:
                message = json.loads(raw)

                context = message.get("context")
                if isinstance(context, int) and context in self._pending:
                    future = self._pending.pop(context)
                    if "error" in message:
                        future.set_exception(Exception(message["error"]))
                    else:
                        future.set_result(message)
                    continue

                signal_id = message.get("signal-id")
                if isinstance(signal_id, int):
                    if signal_id in self._signal_handlers:
                        handler = self._signal_handlers[signal_id]
                        await handler(message)
                    else:
                        self._buffered_signals.setdefault(signal_id, []).append(message)
        finally:
            # Clean up any pending futures on disconnect/cancellation
            pending = list(self._pending.values())
            self._pending.clear()
            for future in pending:
                if not future.done():
                    future.set_exception(RuntimeError("WebSocket connection closed"))

    async def send_request(self, payload: dict):
        context = self._context
        self._context += 1

        envelope = {**payload, "context": context}
        future = asyncio.get_running_loop().create_future()
        self._pending[context] = future

        await self.websocket.send(json.dumps(envelope))
        return await future

    async def call_action(self, name: str, args: list | None = None):
        if args is None:
            args = []
        response = await self.send_request(
            {"type": "action", "name": name, "args": args}
        )
        return response.get("value")

    async def subscribe_signal(self, name: str, handler: SignalHandler):
        response = await self.send_request({"type": "signal-subscribe", "name": name})
        signal_id = response.get("signal-id")
        if not isinstance(signal_id, int):
            raise RuntimeError(
                f"Expected signal-id when subscribing to {name}, got: {response}"
            )

        self._signal_handlers[signal_id] = handler

        if signal_id in self._buffered_signals:
            for buffered_message in self._buffered_signals.pop(signal_id):
                await handler(buffered_message)

        return signal_id

    async def unsubscribe_signal(self, signal_id: int):
        try:
            await self.send_request(
                {"type": "signal-unsubscribe", "signal-id": signal_id}
            )
        finally:
            self._signal_handlers.pop(signal_id, None)


async def render_video(track, gaze: GazeMatcher):
    window_name = "GX LiveView"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    try:
        while True:
            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                break

            frame = await track.recv()
            image = frame.to_ndarray(format="bgr24")
            point = gaze.gaze_for_frame(frame.pts)
            if point is not None:
                height, width = image.shape[:2]
                center = (int(point[0] * width), int(point[1] * height))
                cv2.circle(image, center, 20, (255, 229, 0), 3)
            cv2.imshow(window_name, image)
            cv2.waitKey(1)
            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                break
    finally:
        cv2.destroyAllWindows()


async def run_liveview(uri: str):
    api = GxApiClient(uri)
    pc = RTCPeerConnection()
    pc.addTransceiver("video", direction="recvonly")
    gaze = GazeMatcher()

    display_task: asyncio.Task | None = None
    remote_signal_id: int | None = None
    session_created = False

    @pc.on("track")
    def on_track(track):
        nonlocal display_task
        if track.kind == "video" and display_task is None:
            display_task = asyncio.create_task(render_video(track, gaze))

    @pc.on("datachannel")
    def on_datachannel(channel):
        @channel.on("message")
        def on_message(message):
            gaze.on_message(channel.label, message)

    @pc.on("icecandidate")
    async def on_icecandidate(candidate):
        if candidate is None:
            return

        await api.call_action(
            "live_viewer.ice_candidate.add",
            [candidate.sdpMLineIndex, candidate.to_sdp()],
        )

    async def on_remote_ice_signal(message):
        value = message.get("value")
        if not isinstance(value, list) or len(value) < 2:
            return

        sdp_mline_index = int(value[0])
        candidate_sdp = value[1]

        candidate = candidate_from_sdp(candidate_sdp)
        candidate.sdpMid = "0"
        candidate.sdpMLineIndex = sdp_mline_index
        await pc.addIceCandidate(candidate)

    async def wait_for_glasses_connection_state() -> bool | None:
        connection_state_future = asyncio.get_running_loop().create_future()

        async def on_glasses_connection_signal(message):
            value = message.get("value")
            if isinstance(value, bool) and not connection_state_future.done():
                connection_state_future.set_result(value)

        signal_id = await api.subscribe_signal(
            "glasses.is_connected",
            on_glasses_connection_signal,
        )

        try:
            return await asyncio.wait_for(
                connection_state_future,
                timeout=GLASSES_CONNECTION_WAIT_SECONDS,
            )
        except asyncio.TimeoutError:
            return None
        finally:
            await api.unsubscribe_signal(signal_id)

    try:
        await api.connect()
        print(f"Connected to {uri}")

        glasses_connected = await wait_for_glasses_connection_state()
        if glasses_connected is None:
            print(
                "Could not determine glasses connection state. "
                "Connect the glasses and try again."
            )
            return

        if glasses_connected is not True:
            print("Glasses are not connected. Connect the glasses and try again.")
            return

        created = await api.call_action(
            "live_viewer.session.create",
            [[], ["video", "gaze2d", "timesync"]],
        )
        if created is not True:
            raise RuntimeError(f"live_viewer.session.create failed: {created}")
        session_created = True

        remote_signal_id = await api.subscribe_signal(
            "live_viewer.ice_candidate.discovered",
            on_remote_ice_signal,
        )
        print(f"Subscribed to remote ICE signal (signal-id: {remote_signal_id})")

        offer_sdp = await api.call_action("live_viewer.offer.create")
        if not isinstance(offer_sdp, str) or not offer_sdp.strip():
            raise RuntimeError("live_viewer.offer.create did not return an SDP offer")

        await pc.setRemoteDescription(
            RTCSessionDescription(sdp=offer_sdp, type="offer")
        )

        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        await api.call_action("live_viewer.session.start", [answer.sdp])
        print("LiveView started. Close the window to stop.")

        if display_task:
            await display_task
        else:
            await asyncio.sleep(10)
            print("No video track received within 10 seconds")
    finally:
        if remote_signal_id is not None:
            await api.unsubscribe_signal(remote_signal_id)

        if session_created:
            try:
                await api.call_action("live_viewer.session.delete")
            except Exception:
                pass

        await pc.close()
        await api.close()


async def main():
    try:
        await run_liveview(URI)
    except (asyncio.TimeoutError, TimeoutError) as error:
        print(f"Connection timeout: {error}")
        print("Make sure Public API is enabled and the URI matches your device.")
    except Exception as error:
        print(f"Error: {error}")


if __name__ == "__main__":
    asyncio.run(main())
