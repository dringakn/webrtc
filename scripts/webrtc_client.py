#!/usr/bin/env python3
"""
webrtc_client.py

This script implements a WebRTC client that:
  - Creates an RTCPeerConnection and a secure DataChannel for transmitting binary data.
  - Generates one million 3D random points per frame using numpy (dtype=float32).
  - Transmits these frames at 4 Hz for one minute via a data channel.
  - Uses an HTTP POST to exchange SDP offers/answers with a signaling server.

The design is object-oriented and robust with logging and error handling.
"""

import argparse
import asyncio
import logging

import numpy as np
import aiohttp
from aiortc import RTCPeerConnection, RTCSessionDescription

# Configure logging for clarity.
logging.basicConfig(level=logging.INFO)


class WebRTCClient:
    def __init__(self, signaling_url: str):
        """
        Initialize a new WebRTC client.

        Args:
            signaling_url (str): The URL of the signaling server (e.g., http://localhost:8080/offer)
        """
        self.signaling_url = signaling_url
        self.pc = RTCPeerConnection()
        # Create a data channel for binary transmission.
        self.channel = self.pc.createDataChannel("data")

        # Log changes in the connection state.
        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logging.info("Connection state changed to: %s", self.pc.connectionState)

        # Log when the data channel becomes open.
        @self.channel.on("open")
        def on_open():
            logging.info("Data channel is open and ready for data transmission.")

    async def connect(self):
        """
        Establish a WebRTC connection by creating and sending an SDP offer, and receiving an answer.
        Utilizes an HTTP POST for signaling.
        """
        # Create the SDP offer.
        offer = await self.pc.createOffer()
        await self.pc.setLocalDescription(offer)
        logging.info("SDP offer created. Sending to signaling server...")

        # Send the offer to the signaling server.
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.signaling_url,
                json={"sdp": self.pc.localDescription.sdp, "type": self.pc.localDescription.type},
            ) as response:
                if response.status != 200:
                    raise Exception(f"Signaling server error: {response.status}")
                answer_data = await response.json()

        # Set the remote SDP answer.
        answer = RTCSessionDescription(sdp=answer_data["sdp"], type=answer_data["type"])
        await self.pc.setRemoteDescription(answer)
        logging.info("SDP answer received. WebRTC connection established.")

    async def send_data_stream(self, duration: int = 60, frequency: int = 4):
        """
        Begin sending binary frames over the data channel.

        Args:
            duration (int): Duration of streaming in seconds (default 60).
            frequency (int): Number of frames transmitted per second (default 4).
        """
        interval = 1 / frequency
        num_frames = duration * frequency
        logging.info("Beginning transmission of %d frames.", num_frames)

        # Loop over the frame count.
        for frame in range(int(num_frames)):
            try:
                # Generate one million random 3D points.
                data = np.random.rand(1_000_000, 3).astype(np.float32)
                binary_data = data.tobytes()  # Convert NumPy array to binary.
                self.channel.send(binary_data)
                logging.info("Sent frame %d/%d", frame + 1, int(num_frames))
            except Exception as e:
                logging.error("Error sending frame %d: %s", frame + 1, e)
            # Maintain the desired transmission rate.
            await asyncio.sleep(interval)

        logging.info("Data stream transmission completed.")


async def main(signaling_url: str):
    client = WebRTCClient(signaling_url)

    # Connect to the WebRTC server via the signaling server.
    await client.connect()

    # Ensure the data channel is open before starting transmission.
    while client.channel.readyState != "open":
        await asyncio.sleep(0.1)

    # Start sending the data stream.
    await client.send_data_stream()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebRTC Client for transmitting one million 3D points per frame.")
    parser.add_argument(
        "--signaling",
        type=str,
        default="http://localhost:8080/offer",
        help="Signaling server URL (default: http://localhost:8080/offer)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(main(args.signaling))
    except KeyboardInterrupt:
        logging.info("Client interrupted; shutting down.")
