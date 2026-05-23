# frigate-tplink-talk &middot; TP-Link Camera Two-Way Audio Bridge for Frigate

Enables **two-way talk** (browser → camera speaker) for **TP-Link TL-IPC48AW-PLUS** and similar cameras in Frigate/go2rtc, using TP-Link's MULTITRANS talk protocol.

> 中文主文档：[README.md](./README.md)
> Primary Chinese documentation: [README.md](./README.md)

---

## Architecture

```
Browser Mic (WebRTC OPUS)
  → go2rtc (OPUS → PCMA 8kHz on backchannel track99)
    → frigate-tplink-talk (PCMA → PCM → upscale 16kHz → μ-law)
      → Camera MULTITRANS (μ-law 16kHz on interleaved channel)
        → Camera Speaker 🔊
```

```
Camera Mic (AAC 16kHz)
  → Camera RTSP stream (/stream1)
    → frigate-tplink-talk (passthrough + SDP backchannel injection)
      → go2rtc → Frigate / WebRTC browser 🎧
```

---

## Quick Start

### 1. Create `docker-compose.yml`

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
      - CAMERA_PATH=/stream1
      - LISTEN_PORT=8554
      - HTTP_PORT=8556
```

| Variable | Default | Description |
|----------|---------|-------------|
| `CAMERA_HOST` | `10.40.0.1` | Camera IP address |
| `CAMERA_PORT` | `554` | Camera RTSP port |
| `CAMERA_USER` | `admin` | Camera username |
| `CAMERA_PASSWORD` | `admin` | Camera password |
| `CAMERA_PATH` | `/stream1` | Camera RTSP path |
| `LISTEN_PORT` | `8554` | RTSP proxy listen port |
| `HTTP_PORT` | `8556` | HTTP audio endpoint port |

### 2. Start

```bash
docker compose up -d
```

> Or with `docker run`:
> ```bash
> docker run -d --name frigate-tplink-talk --restart unless-stopped \
>   --network host \
>   -e CAMERA_HOST=10.40.0.1 \
>   -e CAMERA_PORT=554 \
>   -e CAMERA_USER=admin \
>   -e CAMERA_PASSWORD=your_password \
>   -e CAMERA_PATH=/stream1 \
>   -e LISTEN_PORT=8554 \
>   -e HTTP_PORT=8556 \
>   frigate-tplink-talk
> ```

### 3. Configure Frigate go2rtc

Add the proxy stream to your Frigate go2rtc config:

```yaml
go2rtc:
  streams:
    tplink_camera:
      - rtsp://admin:password@PROXY_IP:8554/stream1
      - ffmpeg:tplink_camera#audio=opus
```

Replace `PROXY_IP` with the IP of the machine running this container.

### 4. Restart Frigate

A **microphone button** will appear in the Frigate UI. Press it to talk through the camera speaker.

---

## How It Works

### RTSP Proxy
- Passes through video (H.264) and mic audio (AAC) from camera to go2rtc
- Injects a **backchannel audio track** (track99) into the SDP with `a=sendonly`
- go2rtc detects the sendonly track and routes WebRTC mic audio to it

### Audio Pipeline

| Step | Input | Output | Description |
|------|-------|--------|-------------|
| 1 | Browser OPUS | go2rtc PCMA 8kHz | go2rtc transcoding |
| 2 | go2rtc PCMA | 16-bit PCM 8kHz | Proxy decode |
| 3 | PCM 8kHz | PCM 16kHz | Upsample to camera native rate |
| 4 | PCM 16kHz | μ-law 16kHz | Convert to camera default codec |
| 5 | μ-law 16kHz | Speaker | MULTITRANS RTP send |

### MULTITRANS Protocol
TP-Link's proprietary talk protocol over RTSP `MULTITRANS`:
- **Auth**: RTSP Digest authentication
- **Handshake**: JSON `{"method":"get","talk":{"mode":"aec"}}`
- **Data**: RTP interleaved frames: `$` + 1-byte channel + 2-byte length + RTP header (PT=102) + μ-law payload
- **Flow control**: Continuous streaming with silence fill to prevent speaker timeout

### Smooth Buffering
Audio arrives from go2rtc in variable bursts (WebRTC jitter). The proxy smooths it out:
- Accumulates incoming audio chunks
- Drains at a fixed rate: 320 bytes (20ms) per packet at 16kHz μ-law mono
- Fills gaps with μ-law silence (`0xFF`/`0x7F` alternating)
- Ensures continuous, stutter-free speaker output

### Technical Notes

| Area | Detail |
|------|--------|
| Default codec | Camera MULTITRANS uses **μ-law (PCMU)** |
| Sample rate | Talk audio plays at **16kHz** |
| RTP format | Interleaved channel is **1 byte**, PT=102 |

---

## HTTP API

### Health Check

```
GET http://PROXY_IP:8556/
→ 200 OK
```

### Direct Audio Upload

Send G.711 A-law audio directly to the camera speaker:

```
POST http://PROXY_IP:8556/talk_g711
Content-Type: application/octet-stream
Body: G.711 A-law bytes (8kHz, mono)
→ 200 OK
```

Send 16-bit PCM audio (auto-converted to G.711):

```
POST http://PROXY_IP:8556/talk_pcm
Content-Type: application/octet-stream
Body: 16-bit PCM bytes (8kHz, mono, little-endian)
→ 200 OK
```

---

## Compatibility

Tested with:
- **TP-Link TL-IPC48AW-PLUS** (firmware 1.0.7)
- **Frigate 0.17.1** + go2rtc 1.9.10
- Docker on Linux (amd64/arm64)

Other TP-Link cameras supporting the MULTITRANS (TUMS) protocol should also work.

---

## Troubleshooting

**No microphone button in Frigate:**
- Ensure go2rtc config points to `rtsp://PROXY_IP:8554/stream1`
- Check proxy logs: `docker logs frigate-tplink-talk`
- `BC SETUP` in logs confirms backchannel detection

**Choppy/stuttering audio:**
- Check for `BC SETUP` spam in logs (go2rtc reconnecting)
- Try restarting Frigate for clean RTSP connections
- Ensure camera connection limit not exceeded (max 4 main streams)

**No audio or noise only:**
- Verify camera credentials in environment variables
- MULTITRANS response should show `error_code:0`
- Camera must support the MULTITRANS (TUMS) protocol
