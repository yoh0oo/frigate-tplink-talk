# frigate-tplink-talk

Adds TP-Link CN camera two-way talk support to Frigate/go2rtc. The container runs a single RTSP proxy on container port `554` by default, passes through camera video and camera microphone audio, injects a go2rtc-compatible backchannel track, and forwards Frigate browser microphone audio to TP-Link's `MULTITRANS` talk protocol.

Primary Chinese documentation: [README.md](./README.md).

## How It Works

```
Camera RTSP video/audio
  -> frigate-tplink-talk:554
  -> go2rtc / Frigate

Frigate browser microphone
  -> go2rtc backchannel track99 (PCMA/8000)
  -> frigate-tplink-talk
  -> TP-Link MULTITRANS aec talk (PCMU/16000)
  -> Camera speaker
```

Key behavior:

- Listens only on RTSP port `554` by default; there is no extra HTTP API or debug port.
- Injects `track99` with `a=sendonly` into DESCRIBE SDP so Frigate/go2rtc shows the Talk button.
- Intercepts `SETUP track99` and receives go2rtc browser microphone audio.
- Converts PCMA 8 kHz to PCM, resamples to 16 kHz, then encodes PCMU for the camera talk channel.
- Releases stale MULTITRANS sessions when Talk closes or Frigate reconnects, so the camera talk resource is not left occupied.

## Quick Start

### Docker Compose

```yaml
services:
  frigate-tplink-talk:
    image: ghcr.io/yoh0oo/frigate-tplink-talk:latest
    container_name: frigate-tplink-talk
    restart: unless-stopped
    network_mode: host
    environment:
      - CAMERA_HOST=10.40.0.1
      - CAMERA_PORT=554
      - CAMERA_USER=admin
      - CAMERA_PASSWORD=your_password
      - LISTEN_PORT=554
```

Start it:

```bash
docker compose up -d
```

Port mapping mode also works. Adjust the host port as needed. This example maps host `8554` to the container default `554`:

```bash
docker run -d --name frigate-tplink-talk --restart unless-stopped \
  -p 8554:554 \
  -e CAMERA_HOST=10.40.0.1 \
  -e CAMERA_PORT=554 \
  -e CAMERA_USER=admin \
  -e CAMERA_PASSWORD=your_password \
  ghcr.io/yoh0oo/frigate-tplink-talk:latest
```

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `CAMERA_HOST` | `10.40.0.1` | Camera IP |
| `CAMERA_PORT` | `554` | Camera RTSP port |
| `CAMERA_USER` | `admin` | Camera username for MULTITRANS talk auth |
| `CAMERA_PASSWORD` | `admin` | Camera password for MULTITRANS talk auth |
| `LISTEN_PORT` | `554` | Container proxy listen port |
| `TALK_IDLE_TIMEOUT` | `1.5` | Seconds to keep a talk session after go2rtc stops sending backchannel audio |

## Frigate Config

Point the Frigate `go2rtc.streams` entry at this proxy:

```yaml
go2rtc:
  streams:
    tplink_camera:
      - rtsp://admin:your_password@PROXY_IP:8554/stream1
      - ffmpeg:tplink_camera#audio=opus
```

Replace `PROXY_IP` with the host running this container, and use the host port you mapped. With `network_mode: host` and `LISTEN_PORT=554`, `rtsp://admin:your_password@PROXY_IP/stream1` also works. After restarting Frigate, the camera page should show the Talk/microphone button.

## Compatibility

Tested with:

- TP-Link TL-IPC48AW-PLUS, firmware 1.0.7
- Frigate 0.17.1
- go2rtc 1.9.10
- Docker on Linux amd64/arm64

Other TP-Link models that support the `MULTITRANS` / `TUMS` talk protocol may also work.

## Troubleshooting

No Talk button in Frigate:

- Ensure Frigate/go2rtc uses the proxy URL, for example `rtsp://PROXY_IP:8554/stream1`, where the port is the mapped host port.
- Check logs with `docker logs frigate-tplink-talk`.
- `BC SETUP ch...` means go2rtc detected and opened the backchannel.

Talk button opens but there is no audio:

- Check that `[Talk] response` contains `"error_code":0`.
- Verify `CAMERA_USER` and `CAMERA_PASSWORD`.
- Ensure no other app, browser page, or service is using camera talk at the same time.

Talk only works sometimes after repeated refreshes:

- This version closes stale MULTITRANS sessions when a new backchannel opens and releases talk after the backchannel goes idle.
- If the camera still rejects talk occasionally, try increasing `TALK_IDLE_TIMEOUT`, for example `2.0`.
