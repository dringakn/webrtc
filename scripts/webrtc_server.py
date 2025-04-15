#!/usr/bin/env python3
"""
webrtc_server.py

This script implements a WebRTC server that:
  - Hosts an HTTP signaling endpoint (/offer) using aiohttp.
  - Creates a new RTCPeerConnection per incoming SDP offer.
  - Establishes a secure data channel.
  - Receives binary data frames with 3D points and decodes them into NumPy arrays.
  - Receives and plays audio and video streams from the client.
  
Before running, install dependencies:
  sudo apt-get install portaudio19-dev
  pip install aiohttp aiortc opencv-python pyaudio numpy
"""

import asyncio
import logging
import numpy as np
import cv2
import pyaudio
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription

logging.basicConfig(level=logging.INFO)

# Initialize PyAudio for audio playback.
p = pyaudio.PyAudio()
# for i in range(p.get_device_count()):
#     dev = p.get_device_info_by_index(i)
#     print(f"Device {i}: {dev['name']}")
    
# We assume stereo audio (2 channels), 48000 Hz sample rate, and 16-bit samples.
# On your system, find output_device_index=0 based on `aplay -l`.
audio_stream = p.open(
    format=pyaudio.paInt16,
    channels=2,
    rate=48000,
    output=True,
    output_device_index=0
)
async def play_video(track):
    """Continuously receive video frames and display them using OpenCV."""
    logging.info("Starting video playback.")
    while True:
        try:
            # Receive next video frame.
            frame = await track.recv()
            # Convert the frame to a BGR NumPy array for OpenCV.
            img = frame.to_ndarray(format="bgr24")
            cv2.imshow("Video", img)
            # If "q" is pressed, break out of the loop.
            if cv2.waitKey(1) & 0xFF == ord("q"):
                logging.info("Video playback stopped by user.")
                break
        except Exception as e:
            logging.error(f"Video playback error: {e}")
            break
    cv2.destroyAllWindows()

async def play_audio(track):
    """Continuously receive audio frames and send them to PyAudio."""
    logging.info("Starting audio playback.")
    while True:
        try:
            # Receive next audio frame.
            frame = await track.recv()
            # Convert the frame to a NumPy array then to raw bytes.
            pcm_data = frame.to_ndarray().tobytes()
            audio_stream.write(pcm_data)
        except Exception as e:
            logging.error(f"Audio playback error: {e}")
            break

class WebRTCServer:
    def __init__(self):
        # Keep a reference to active connections to prevent garbage collection.
        self.connections = []

    async def handle_offer(self, request):
        try:
            params = await request.json()
            logging.info("Received SDP offer from client.")

            # Build the offer and create a new peer connection.
            offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
            pc = RTCPeerConnection()

            @pc.on("datachannel")
            def on_datachannel(channel):
                logging.info(f"Data channel created: {channel.label}")

                @channel.on("message")
                async def on_message(message):
                    if isinstance(message, bytes):
                        logging.info("Received binary data on the data channel.")
                        try:
                            # Decode binary data into a NumPy array assuming float32 values.
                            arr = np.frombuffer(message, dtype=np.float32).reshape(-1, 3)
                            logging.info(f"Decoded data frame with shape: {arr.shape}")
                        except Exception as e:
                            logging.error(f"Failed to decode binary data: {e}")
                    else:
                        logging.warning("Received non-binary message on the data channel.")

            @pc.on("track")
            def on_track(track):
                logging.info(f"Track '{track.kind}' received.")
                if track.kind == "video":
                    # Schedule video playback.
                    asyncio.ensure_future(play_video(track))
                elif track.kind == "audio":
                    # Schedule audio playback.
                    asyncio.ensure_future(play_audio(track))
                else:
                    logging.warning(f"Unsupported track type: {track.kind}")

            # Set remote description, create and set local answer.
            await pc.setRemoteDescription(offer)
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)

            # Keep a reference to the connection.
            self.connections.append(pc)
            logging.info("Sending SDP answer to client.")
            return web.json_response({
                "sdp": pc.localDescription.sdp,
                "type": pc.localDescription.type
            })
        except Exception as e:
            logging.error(f"Error handling offer: {e}")
            return web.Response(status=500, text="Internal Server Error")

    async def run(self, host="0.0.0.0", port=8080):
        # Set up the aiohttp web app.
        app = web.Application()
        app.add_routes([web.post("/offer", self.handle_offer)])
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        logging.info(f"Signaling server running on {host}:{port}")
        await site.start()

        # Keep the server running.
        while True:
            await asyncio.sleep(1)

if __name__ == "__main__":
    server = WebRTCServer()
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logging.info("Server shutdown requested; exiting.")
    finally:
        # Clean up the PyAudio stream upon exit.
        audio_stream.stop_stream()
        audio_stream.close()
        p.terminate()
