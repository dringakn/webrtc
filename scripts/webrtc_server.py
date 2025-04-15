#!/usr/bin/env python3
"""
webrtc_server.py

This script implements a WebRTC server that:
  - Hosts an HTTP signaling endpoint (/offer) using aiohttp.
  - Creates a new RTCPeerConnection per incoming SDP offer.
  - Establishes a secure data channel.
  - Receives binary data frames with 3D points and decodes them into NumPy arrays.
  - Receives audio and video streams from the client.
"""

import asyncio
import logging
import subprocess
import numpy as np
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRecorder

logging.basicConfig(level=logging.INFO)


class WebRTCServer:
    def __init__(self):
        # Hold references to active connections.
        self.connections = []

    async def handle_offer(self, request):
        try:
            params = await request.json()
            logging.info("Received SDP offer from client.")

            # Build offer description.
            offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

            # Create a new peer connection.
            pc = RTCPeerConnection()

            @pc.on("datachannel")
            def on_datachannel(channel):
                logging.info(f"Data channel created by remote peer: {channel.label}")

                @channel.on("message")
                async def on_message(message):
                    if isinstance(message, bytes):
                        logging.info("Data channel message received.")
                        try:
                            # Decode the binary data into a NumPy array of shape (-1, 3).
                            arr = np.frombuffer(message, dtype=np.float32).reshape(-1, 3)
                            logging.info(f"Received frame {arr[0][0]} with shape: {arr.shape}")
                        except Exception as e:
                            logging.error(f"Failed to parse incoming frame: {e}")
                    else:
                        logging.warning("Received a non-binary message.")

            @pc.on("track")
            def on_track(track):
                logging.info(f"Track '{track.kind}' received.")
                
                if track.kind == "video":
                    async def recv_video():
                        # Option: dynamically detect width/height from the first frame.
                        frame = await track.recv()
                        width, height = frame.width, frame.height
                        logging.info(f"Using video size: {width}x{height}")

                        # Start FFplay to display raw BGR24 frames
                        ffplay_proc = subprocess.Popen(
                            [
                                "ffplay",
                                "-f", "rawvideo",
                                "-pixel_format", "bgr24",
                                "-video_size", f"{width}x{height}",
                                "-i", "-"  # read from stdin
                            ],
                            stdin=subprocess.PIPE
                        )

                        # Process the first frame
                        img = frame.to_ndarray(format="bgr24")
                        ffplay_proc.stdin.write(img.tobytes())
                        ffplay_proc.stdin.flush()

                        # Now process subsequent frames
                        while True:
                            try:
                                frame = await track.recv()
                                img = frame.to_ndarray(format="bgr24")
                                ffplay_proc.stdin.write(img.tobytes())
                                ffplay_proc.stdin.flush()
                            except Exception as e:
                                logging.error(f"Error processing video frame: {e}")
                                break

                    # Launch the video receiving coroutine.
                    asyncio.ensure_future(recv_video())

                elif track.kind == "audio":
                    async def recv_audio():
                        try:
                            # Wait for first audio frame to determine parameters.
                            frame = await track.recv()
                            sample_rate = frame.sample_rate
                            channels = frame.channels
                            logging.info(f"Audio parameters: {sample_rate} Hz, {channels} channels")

                            # Launch FFplay to live preview raw PCM audio.
                            ffplay_proc = subprocess.Popen(
                                [
                                    "ffplay",
                                    "-f", "s16le",
                                    "-ar", str(sample_rate),
                                    "-ac", str(channels),
                                    "-i", "-"
                                ],
                                stdin=subprocess.PIPE
                            )

                            # Process the first audio frame.
                            samples = frame.to_ndarray()  # Assumes float format in range [-1, 1]
                            samples_i16 = (samples * 32767).astype(np.int16)
                            ffplay_proc.stdin.write(samples_i16.tobytes())
                            ffplay_proc.stdin.flush()

                            # Continuously receive and pipe audio frames.
                            while True:
                                try:
                                    frame = await track.recv()
                                    samples = frame.to_ndarray()
                                    samples_i16 = (samples * 32767).astype(np.int16)
                                    ffplay_proc.stdin.write(samples_i16.tobytes())
                                    ffplay_proc.stdin.flush()
                                except Exception as inner_e:
                                    logging.error(f"Error processing audio frame: {inner_e}")
                                    break
                        except Exception as e:
                            logging.error(f"Audio track error: {e}")

                    asyncio.ensure_future(recv_audio())
                    pass
                
            # Set remote description and create answer.
            await pc.setRemoteDescription(offer)
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)

            # Save the connection to prevent garbage collection.
            self.connections.append(pc)
            logging.info("Sending SDP answer to client.")
            return web.json_response(
                {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
            )
        except Exception as e:
            logging.error(f"Error handling offer: {e}")
            return web.Response(status=500, text="Internal Server Error")

    async def run(self, host="0.0.0.0", port=8080):
        app = web.Application()
        app.add_routes([web.post("/offer", self.handle_offer)])
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        logging.info(f"Signaling server running on {host}:{port}")
        await site.start()

        # Run indefinitely.
        while True:
            await asyncio.sleep(1)


if __name__ == "__main__":
    server = WebRTCServer()
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logging.info("Server shutdown requested; exiting.")
