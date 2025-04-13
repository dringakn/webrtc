#!/usr/bin/env python3
"""
webrtc_server.py

This script implements a WebRTC server that:
  - Hosts an HTTP signaling endpoint (/offer) using aiohttp.
  - Waits for an SDP offer from a client, then creates and sends an SDP answer.
  - Establishes a secure and robust data channel (DTLS is used internally by WebRTC).
  - Receives binary data frames containing one million 3D points per frame.
  - Interprets each incoming binary frame using numpy (dtype=float32).

Intended for scalable use: the design encapsulates functionality in a class and logs key events.
"""

import asyncio
import json
import logging

import numpy as np
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription

# Configure logging for clarity
logging.basicConfig(level=logging.INFO)


class WebRTCServer:
    def __init__(self):
        # Create a new RTCPeerConnection instance.
        # DTLS-based encryption is handled under the hood for security.
        self.pc = RTCPeerConnection()
        # Register callback when a data channel is received from a remote peer.
        self.pc.ondatachannel = self.on_datachannel

    def on_datachannel(self, channel):
        """Called when a data channel is created by the remote peer."""
        logging.info("Data channel created by remote peer: %s", channel.label)

        @channel.on("message")
        async def on_message(message):
            """
            Called when a message is received.
            Expects binary data representing one frame containing one million 3D points.
            """
            if isinstance(message, bytes):
                try:
                    # Convert bytes back into a NumPy array.
                    # We expect the data to be of type float32 and shaped as (-1, 3).
                    arr = np.frombuffer(message, dtype=np.float32).reshape(-1, 3)
                    logging.info("Received frame with shape: %s", arr.shape)
                    # Additional processing can be added here.
                except Exception as e:
                    logging.error("Failed to parse incoming frame: %s", e)
            else:
                logging.warning("Received a non-binary message.")

    async def handle_offer(self, request):
        """
        HTTP POST handler to accept a WebRTC SDP offer,
        create an answer, and send the answer back in JSON.
        """
        try:
            params = await request.json()
            logging.info("Received SDP offer from client.")
            offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
            await self.pc.setRemoteDescription(offer)
            # Create an answer to the received offer.
            answer = await self.pc.createAnswer()
            await self.pc.setLocalDescription(answer)
            logging.info("Sending SDP answer to client.")
            # Return the SDP answer in JSON format.
            return web.json_response(
                {"sdp": self.pc.localDescription.sdp, "type": self.pc.localDescription.type}
            )
        except Exception as e:
            logging.error("Error handling offer: %s", e)
            return web.Response(status=500, text="Internal Server Error")

    async def run(self, host="0.0.0.0", port=8080):
        """
        Start the aiohttp web server to handle signaling.
        This loop runs indefinitely.
        """
        app = web.Application()
        app.add_routes([web.post("/offer", self.handle_offer)])
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        logging.info("Signaling server running on %s:%s", host, port)
        await site.start()

        # Keep running forever. In a production server, proper graceful shutdown handling should be added.
        while True:
            await asyncio.sleep(3600)


if __name__ == "__main__":
    server = WebRTCServer()
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logging.info("Server shutdown requested; exiting.")
