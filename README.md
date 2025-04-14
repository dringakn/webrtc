# WebRTC 3D Points and Media Transmission

This project implements a secure and scalable WebRTC system that sends 3D point data and simultaneously streams an audio+video file. The client transmits binary messages (using a compact NumPy format) at 4 Hz via a DataChannel while also streaming media from a test file (`../tests/data/test.mp4`) to the server.

## Overview

- **Dual-Stream Design:**  
  Each SDP offer creates its own RTCPeerConnection to ensure isolated sessions. The system handles a data channel for 3D points **and** audio/video tracks for media streaming concurrently. This makes the solution both versatile and efficient.

- **Security & Efficiency:**  
  WebRTC’s native DTLS/SRTP encryption secures both data and media streams. On the client side, NumPy serializes thousands of 3D points into a lightweight binary format, and the media player streams audio and video without interfering with the data flow.

## Components

### Server (webrtc_server.py)

- **Functionality:**
  - Hosts an HTTP signaling endpoint (`/offer`) using aiohttp.
  - Spawns a fresh RTCPeerConnection for each incoming SDP offer.
  - Receives binary data messages, converting them into NumPy arrays.
  - Listens for media tracks (audio and video) and logs received frames for inspection.
- **Design Intent:**  
  Every connection is independent to maximize scalability. The addition of a media track handler means the server processes both 3D point data and media streams without mixing concerns.

### Client (webrtc_client.py)

- **Functionality:**
  - Initiates a secure WebRTC connection through SDP offer/answer signaling.
  - Streams binary 3D point data at 4 Hz over a dedicated DataChannel.
  - Simultaneously streams audio and video from `../tests/data/test.mp4` using media tracks.
- **Design Intent:**  
  The client waits for a fully opened data channel before sending data, ensuring stable transmission. Integrating media streaming with DataChannel communications makes the solution a compact, multi-functional system.

### Test Video Generator

This project includes a utility script (`tests/generate_test_video.sh`) for creating test video files with ffmpeg. It supports:

- **testsrc mode:**  
  Generates a simple test pattern video (default: 10 seconds, 320×240, 10 fps).

- **bounce mode (default):**  
  Animates an external image (default: `data/ball.png`) bouncing over a black background for 60 seconds.

Audio is enabled by default using a modulated tone (around 440 Hz) and encoded at 32 kbps to keep file sizes down. Options allow you to customize duration, resolution, frame rate, and more.

## Getting Started

### Prerequisites

Ensure you have Python 3.7+ installed along with:

- `aiortc`
- `aiohttp`
- `numpy`

Install dependencies via pip:

```bash
pip install aiortc aiohttp numpy
```

### Running the Server

Start the signaling server:

```bash
python3 webrtc_server.py
```

The server defaults to listening on `0.0.0.0:8080`. Adjust host/port settings inside the script as needed.

### Running the Client

In another terminal, start the client:

```bash
python3 webrtc_client.py --signaling http://localhost:8080/offer --points 100000
```

The client will generate an SDP offer, exchange signaling messages, and once connected, simultaneously stream the test video (audio+video) and binary 3D point data.

## Security and Production Considerations

- **Data Security:**  
  All transmission occurs over encrypted channels (DTLS/SRTP). In production, secure the signaling server using HTTPS and add robust error handling.

- **Scalability:**  
  The asynchronous, object‑oriented design supports multiple concurrent connections and diverse transmission types, making future expansions straightforward.

## Contributing

Contributions are welcome. If you have bug fixes, improvements, or suggestions, please open an issue or submit a pull request.

## License

Distributed under the MIT License.
