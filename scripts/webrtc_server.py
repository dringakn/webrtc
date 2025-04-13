#!/usr/bin/env python3
"""
webrtc_server.py

This script implements a WebRTC server that:
  - Hosts an HTTP signaling endpoint (/offer) using aiohttp.
  - Creates a new RTCPeerConnection instance per incoming SDP offer. 
    This avoids reusing a connection that might be in a closed state.
  - Establishes a secure and robust data channel (WebRTC handles DTLS encryption).
  - Receives binary data frames with one million 3D points per frame.
  - Decodes the frames into NumPy arrays (dtype=float32).

Setup Notes:
- sudo apt-get install python3-pip
- pip3 install aiohttp aiortc numpy --break-system-packages
"""

import asyncio
import logging

import numpy as np
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription

# Configure basic logging.
logging.basicConfig(level=logging.INFO)


class WebRTCServer:
    def __init__(self):
        # Store active peer connections to prevent garbage collection.
        self.connections = []

    def on_datachannel(self, channel):
        """Callback when a remote data channel is established."""
        logging.info("Data channel created by remote peer: %s", channel.label)

        @channel.on("message")
        async def on_message(message):
            """
            Called when a message is received on the data channel.
            Expects binary data representing a frame of one million 3D points.
            """
            if isinstance(message, bytes):
                try:
                    # Decode the binary message into a NumPy array of shape (-1, 3)
                    arr = np.frombuffer(message, dtype=np.float32).reshape(-1, 3)
                    logging.info("Received frame with shape: %s", arr.shape)
                    # Further processing can be done here.
                except Exception as e:
                    logging.error("Failed to parse incoming frame: %s", e)
            else:
                logging.warning("Received a non-binary message.")

    async def handle_offer(self, request):
        """
        Handles a POST request containing an SDP offer, creates a new peer connection,
        sets the remote description, creates an SDP answer, and returns it.
        """
        try:
            params = await request.json()
            logging.info("Received SDP offer from client.")

            # Build the offer description.
            offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

            # Create a new peer connection for this offer.
            pc = RTCPeerConnection()
            pc.ondatachannel = self.on_datachannel

            # Set the remote description and generate an answer.
            await pc.setRemoteDescription(offer)
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)

            # Store the connection for lifecycle management.
            self.connections.append(pc)

            logging.info("Sending SDP answer to client.")
            return web.json_response(
                {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
            )
        except Exception as e:
            logging.error("Error handling offer: %s", e)
            return web.Response(status=500, text="Internal Server Error")

    async def run(self, host="0.0.0.0", port=8080):
        """
        Runs the HTTP signaling server.
        Note: In production, you'd add shutdown and cleanup logic.
        """
        app = web.Application()
        app.add_routes([web.post("/offer", self.handle_offer)])
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        logging.info("Signaling server running on %s:%s", host, port)
        await site.start()

        # Run indefinitely.
        while True:
            await asyncio.sleep(3600)


if __name__ == "__main__":
    server = WebRTCServer()
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logging.info("Server shutdown requested; exiting.")
