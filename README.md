# frigate-tplink-talk

让 Frigate/go2rtc 支持 TP-Link 中国区摄像头双向对讲。项目默认通过一个 RTSP 代理监听容器内 `554`，透明转发摄像头视频和摄像头麦克风音频，同时在 SDP 中注入 go2rtc 可识别的回传音频轨道，把 Frigate 浏览器端的麦克风音频转发到 TP-Link `MULTITRANS` 对讲协议。

英文文档见 [README_EN.md](./README_EN.md)。

## 工作方式

```
摄像头 RTSP 视频/音频
  -> frigate-tplink-talk:554
  -> go2rtc / Frigate

Frigate 浏览器麦克风
  -> go2rtc 回传轨道 track99 (PCMA/8000)
  -> frigate-tplink-talk
  -> TP-Link MULTITRANS aec 对讲 (PCMU/16000)
  -> 摄像头扬声器
```

关键实现：

- 默认只监听 RTSP 端口 `554`，没有额外 HTTP API 或调试端口。
- 在 DESCRIBE 的 SDP 中注入 `track99`，并标记 `a=sendonly`，用于触发 Frigate/go2rtc 的 Talk 按钮。
- 拦截 `SETUP track99`，接收 go2rtc 发送的浏览器麦克风音频。
- 将 PCMA 8kHz 解码、升采样到 16kHz，再编码为摄像头对讲使用的 PCMU。
- Talk 关闭或刷新重连后会主动释放旧的 MULTITRANS 会话，避免摄像头对讲资源被占用。

## 快速开始

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

启动：

```bash
docker compose up -d
```

也可以使用端口映射模式，宿主机端口按需要调整。下面示例把宿主机 `8554` 映射到容器默认 `554`：

```bash
docker run -d --name frigate-tplink-talk --restart unless-stopped \
  -p 8554:554 \
  -e CAMERA_HOST=10.40.0.1 \
  -e CAMERA_PORT=554 \
  -e CAMERA_USER=admin \
  -e CAMERA_PASSWORD=your_password \
  ghcr.io/yoh0oo/frigate-tplink-talk:latest
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CAMERA_HOST` | `10.40.0.1` | 摄像头 IP |
| `CAMERA_PORT` | `554` | 摄像头 RTSP 端口 |
| `CAMERA_USER` | `admin` | 摄像头账号，用于 MULTITRANS 对讲认证 |
| `CAMERA_PASSWORD` | `admin` | 摄像头密码，用于 MULTITRANS 对讲认证 |
| `LISTEN_PORT` | `554` | 容器内代理监听端口 |
| `TALK_IDLE_TIMEOUT` | `1.5` | Frigate 停止发送回传音频后释放对讲会话的秒数 |

## Frigate 配置

在 Frigate 的 `go2rtc.streams` 中把摄像头地址指向本代理：

```yaml
go2rtc:
  streams:
    tplink_camera:
      - rtsp://admin:your_password@PROXY_IP:8554/stream1
      - ffmpeg:tplink_camera#audio=opus
```

`PROXY_IP` 替换为运行本容器的主机 IP，端口填写你映射到宿主机的端口。使用 `network_mode: host` 且 `LISTEN_PORT=554` 时可写 `rtsp://admin:your_password@PROXY_IP/stream1`。重启 Frigate 后，摄像头页面应显示 Talk/麦克风按钮。

## 兼容性

已测试环境：

- TP-Link TL-IPC48AW-PLUS，固件 1.0.7
- Frigate 0.17.1
- go2rtc 1.9.10
- Docker on Linux amd64/arm64

其他支持 TP-Link `MULTITRANS` / `TUMS` 对讲协议的型号理论上也可用。

## 故障排查

Frigate 没有 Talk 按钮：

- 确认 Frigate/go2rtc 使用的是代理地址，例如 `rtsp://PROXY_IP:8554/stream1`，其中端口是宿主机映射端口。
- 查看容器日志：`docker logs frigate-tplink-talk`。
- 日志出现 `BC SETUP ch...` 表示 go2rtc 已识别并打开回传通道。

Talk 按钮能打开但没有声音：

- 查看日志中 `[Talk] response` 是否包含 `"error_code":0`。
- 确认 `CAMERA_USER` 和 `CAMERA_PASSWORD` 是摄像头真实账号密码。
- 确认同一时间没有其他 App、网页或服务占用摄像头对讲。

刷新几次后偶尔才能说话：

- 当前版本会在新的回传通道打开时关闭旧的 MULTITRANS 会话，并在回传音频空闲后自动释放会话。
- 如果摄像头仍然偶发拒绝对讲，可适当增大 `TALK_IDLE_TIMEOUT`，例如 `2.0`。
