# WebRTC 3D Points Transmission

This project implements a secure, robust, and scalable WebRTC-based system for sending 3D points per message using a binary NumPy format. The client sends message at 4 Hz for 1 minute over a secure DataChannel, while the server handles SDP signaling and receives the binary data messages.

## Overview

- **Robust and Scalable:**  
  Each incoming SDP offer creates a new RTCPeerConnection, ensuring that each connection is isolated and managed independently. The design is built using an object-oriented approach and leverages asynchronous I/O for scalability.

- **Security:**  
  WebRTC's built-in DTLS/SRTP encryption secures the transmission, protecting data integrity and privacy. In production, further security measures (such as HTTPS for signaling) are recommended.

- **Efficiency:**  
  The client uses NumPy to generate and efficiently serialize 3D points per message (as 32-bit floats) into a compact binary format, which is transmitted at a steady 4 Hz.

## Components

### Server (webrtc_server.py)

- **Functionality:**

  - Hosts an HTTP signaling endpoint (`/offer`) using aiohttp.
  - Creates a new RTCPeerConnection per incoming SDP offer.
  - Receives and processes binary messages by converting them to NumPy arrays.
  - Logs connection events and message details for monitoring.

- **Design Intent:**  
  Avoids reusing connections in a closed state by spawning a fresh connection for each offer, maintaining scalability and robustness.

### Client (webrtc_client.py)

- **Functionality:**

  - Establishes a secure WebRTC connection using an SDP offer/answer exchange with the signaling server.
  - Generates and transmits 3D points (each message) using NumPy at 4 Hz over a secure DataChannel.
  - Logs the connection state and successful message transmissions.

- **Design Intent:**  
  Ensures a reliable data channel is established before streaming begins, with comprehensive logging for debugging and performance monitoring.

### Test Video Generator

It also includes a utility script, `tests/generate_test_video.sh`, for generating test video files with ffmpeg. The script supports two modes:

- **testsrc mode:**  
  Uses ffmpeg’s built‑in test pattern (testsrc) to create a video, with defaults of 10 seconds, 320×240 resolution, and 10 fps.

- **bounce mode (default):**  
  Overlays and animates an external image (default: `data/ball.png`) bouncing over a black background. In this mode, the default duration is 60 seconds.

Audio is enabled by default—using aevalsrc equation that generates a novel modulated tone (sinusoidal modulation around 440 Hz)—and is encoded at 32 kbps to keep file size in check. Audio can be disabled using the `-a no` option.

Additional customization options include duration, size, frame rate, output file name, image file (for bounce mode), and a force overwrite flag (`-F`) to automatically replace existing test video file.

## Getting Started

### Prerequisites

Ensure you have Python 3.7+ installed along with the following packages:

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

The server listens on `0.0.0.0:8080` by default. Modify the host and port within the script as needed.

### Running the Client

In a separate terminal session, run the client:

```bash
python3 webrtc_client.py --signaling http://localhost:8080/offer
```

The client creates an SDP offer, exchanges signaling messages with the server, and streams data upon successful connection.

## Security and Production Considerations

- **Data Security:**  
  All communication occurs over encrypted channels (DTLS and SRTP). For production, consider securing the signaling endpoint with HTTPS and adding proper error handling and timeout mechanisms.

- **Scalability:**  
  The asynchronous and OOP design supports concurrent connections and easy extension to more complex transmission scenarios.

## Contributing

Contributions and improvements are welcome. If you encounter issues or have enhancement suggestions, please open an issue or submit a pull request.

## License

Distributed under the MIT License.
