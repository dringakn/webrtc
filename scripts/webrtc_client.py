#!/usr/bin/env python3
"""
webrtc_client.py

This script implements a WebRTC client that:
  - Creates an RTCPeerConnection and opens a DataChannel for binary data transfer.
  - Streams audio and video from the ../tests/data/test.mp4 file to the server.
  - Generates random 3D points with NumPy (dtype=float32) and sends them over the data channel.
  - Transmits these frames at 4Hz for a set duration.
  - Exchanges SDP offers/answers with the signaling server via HTTP.
"""

import argparse
import asyncio
import logging

import numpy as np
import aiohttp
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaPlayer  # For streaming media from a file

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

        # Add media tracks from test.mp4 for audio and video streaming.
        self.player = MediaPlayer("../tests/data/test.mp4")
        if self.player.audio:
            self.pc.addTrack(self.player.audio)
            logging.info("Added audio track from file ../tests/data/test.mp4")
        if self.player.video:
            self.pc.addTrack(self.player.video)
            logging.info("Added video track from file ../tests/data/test.mp4")

    async def connect(self):
        """
        Establish a WebRTC connection using SDP offer/answer via the signaling server.
        """
        # Create the offer and set it as the local description.
        await self.pc.setLocalDescription(await self.pc.createOffer())

        # Wait for ICE gathering to complete.
        while self.pc.iceGatheringState != "complete":
            await asyncio.sleep(0.1)

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

    async def send_data_stream(self, duration: int = 60, frequency: int = 4, points: int = 1_000):
        """
        Sends binary frames over the data channel.

        Args:
            duration (int): Duration in seconds.
            frequency (int): Frames per second.
            points (int): Number of 3D points per message.
        """
        interval = 1 / frequency
        num_frames = duration * frequency
        logging.info("Beginning transmission of %d frames.", num_frames)

        for frame in range(int(num_frames)):
            try:
                data = np.random.rand(points, 3).astype(np.float32)
                data[0] = frame  # Embed frame number in the first point for reference.
                binary_data = data.tobytes()
                self.channel.send(binary_data)
                logging.info("Sent frame %d/%d", frame + 1, int(num_frames))
            except Exception as e:
                logging.error("Error sending frame %d: %s", frame + 1, e)
            await asyncio.sleep(interval)

        logging.info("Data stream transmission completed.")


async def main(signaling_url: str, points: int):
    client = WebRTCClient(signaling_url)
    await client.connect()

    # Wait until the data channel is open.
    while client.channel.readyState != "open":
        await asyncio.sleep(0.1)

    # Start sending binary data over the data channel concurrently.
    data_stream_task = asyncio.create_task(client.send_data_stream(duration=10, frequency=4, points=points))
    await data_stream_task

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebRTC Client for transmitting 3D points and media stream.")
    parser.add_argument(
        "--signaling",
        type=str,
        default="http://localhost:8080/offer",
        help="Signaling server URL (default: http://localhost:8080/offer)",
    )
    parser.add_argument(
        "--points",
        type=int,
        default=100000,
        help="Number of 3D points per message (default: 100,000)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(main(args.signaling, args.points))
    except KeyboardInterrupt:
        logging.info("Client interrupted; shutting down.")
