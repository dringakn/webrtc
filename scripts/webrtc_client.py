#!/usr/bin/env python3
"""
webrtc_client.py

This script implements a WebRTC client that:
  - Creates an RTCPeerConnection and opens a DataChannel for binary data transfer.
  - Generates random 3D points with NumPy (dtype=float32).
  - Transmits these frames at 4Hz for one minute.
  - Uses an HTTP POST to exchange SDP offers/answers with the signaling server.
  
Setup Notes:
- sudo apt-get install python3-pip
- pip3 install aiohttp aiortc numpy --break-system-packages
"""

import argparse
import asyncio
import logging

import numpy as np
import aiohttp
from aiortc import RTCPeerConnection, RTCSessionDescription

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
        self.channel = self.pc.createDataChannel("data")

        @self.pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logging.info("Connection state changed to: %s", self.pc.connectionState)

        @self.channel.on("open")
        def on_open():
            logging.info("Data channel is open and ready for data transmission.")

    async def connect(self):
        """
        Establish a WebRTC connection using SDP offer/answer via the signaling server.
        """
        # Create the offer and set it as the local description.
        await self.pc.setLocalDescription(await self.pc.createOffer())

        # Wait for ICE gathering to finish.
        while self.pc.iceGatheringState != "complete":
            await asyncio.sleep(0.1)

        # Now self.pc.localDescription is the fully gathered SDP.
        logging.info("SDP offer created. Sending to signaling server...")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.signaling_url,
                json={"sdp": self.pc.localDescription.sdp, "type": self.pc.localDescription.type},
            ) as response:
                if response.status != 200:
                    raise Exception(f"Signaling server error: {response.status}")
                answer_data = await response.json()

        # Set the remote description to complete the handshake.
        answer = RTCSessionDescription(sdp=answer_data["sdp"], type=answer_data["type"])
        await self.pc.setRemoteDescription(answer)
        logging.info("SDP answer received. WebRTC connection established.")


    async def send_data_stream(self, duration: int = 60, frequency: int = 4, data_size=1_000):
        """
        Sends binary frames over the data channel.
        
        Args:
            duration (int): Duration in seconds (default: 60).
            frequency (int): Frames per second (default: 4).
        """
        interval = 1 / frequency
        num_frames = duration * frequency
        logging.info("Beginning transmission of %d frames.", num_frames)

        for frame in range(int(num_frames)):
            try:
                data = np.random.rand(data_size, 3).astype(np.float32)
                data[0] = frame  # Set the first point to (frame,frame,frame)
                binary_data = data.tobytes()
                self.channel.send(binary_data)
                logging.info("Sent frame %d/%d", frame + 1, int(num_frames))
            except Exception as e:
                logging.error("Error sending frame %d: %s", frame + 1, e)
            await asyncio.sleep(interval)

        logging.info("Data stream transmission completed.")


async def main(signaling_url: str):
    client = WebRTCClient(signaling_url)
    await client.connect()

    # Wait until the data channel is open.
    while client.channel.readyState != "open":
        await asyncio.sleep(0.1)

    await client.send_data_stream(duration=10, frequency=4, data_size=1_000_000)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebRTC Client for transmitting 3D points.")
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
