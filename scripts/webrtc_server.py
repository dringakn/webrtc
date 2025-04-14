#!/usr/bin/env python3
"""
webrtc_server.py

This script implements a WebRTC server that:
  - Hosts an HTTP signaling endpoint (/offer) using aiohttp.
  - Creates a new RTCPeerConnection per incoming SDP offer.
  - Establishes a secure data channel.
  - Receives binary data frames with 3D points and decodes them into NumPy arrays.
"""

import asyncio
import logging
import numpy as np
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription

logging.basicConfig(level=logging.INFO)


class WebRTCServer:
    def __init__(self):
        # Hold references to active connections.
        self.connections = []

    async def handle_offer(self, request):
        try:
            params = await request.json()
            logging.info(f"Received SDP offer from client.")

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
                        logging.info(f"Data channel message received.")
                        try:
                            # Decode the binary data into a NumPy array of shape (-1, 3).
                            arr = np.frombuffer(message, dtype=np.float32).reshape(-1, 3)
                            logging.info(f"Received frame {arr[0][0]} with shape: {arr.shape}")
                        except Exception as e:
                            logging.error(f"Failed to parse incoming frame: {e}")
                    else:
                        logging.warning(f"Received a non-binary message.")

            # Set remote description and create answer.
            await pc.setRemoteDescription(offer)
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)

            # Save the connection to prevent it from being garbage collected.
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
