# frigate-tplink-talk &middot; TP-Link 摄像头 Frigate 双向语音桥接

[![Docker Pulls](https://img.shields.io/badge/ghcr-download-blue)](https://github.com/yoh0oo/frigate-tplink-talk/pkgs/container/frigate-tplink-talk)

让 Frigate/go2rtc 实现对 **TP-Link TL-IPC48AW-PLUS** 等摄像头的**双向对讲**（浏览器 → 摄像头扬声器），通过 TP-Link 的 MULTITRANS 对讲协议实现。

> 完整英文文档见 [README_EN.md](./README_EN.md)
> Full English documentation: [README_EN.md](./README_EN.md)

---

## 架构

```
浏览器麦克风 (WebRTC OPUS)
  → go2rtc (OPUS → PCMA 8kHz, track99 回传通道)
    → frigate-tplink-talk (PCMA → PCM → 升采样 16kHz → μ-law)
      → 摄像头 MULTITRANS (μ-law 16kHz, 交织通道)
        → 摄像头扬声器 🔊
```

```
摄像头麦克风 (AAC 16kHz)
  → 摄像头 RTSP 码流 (/stream1)
    → frigate-tplink-talk (透明转发 + SDP 回传通道注入)
      → go2rtc → Frigate / WebRTC 浏览器 🎧
```

---

## 快速开始

### 1. 创建 `docker-compose.yml`

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

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CAMERA_HOST` | `10.40.0.1` | 摄像头 IP 地址 |
| `CAMERA_PORT` | `554` | 摄像头 RTSP 端口 |
| `CAMERA_USER` | `admin` | 摄像头登录用户名 |
| `CAMERA_PASSWORD` | `admin` | 摄像头登录密码 |
| `CAMERA_PATH` | `/stream1` | 摄像头 RTSP 路径 |
| `LISTEN_PORT` | `8554` | RTSP 代理监听端口 |
| `HTTP_PORT` | `8556` | HTTP 音频接口端口 |

### 2. 启动

```bash
docker compose up -d
```

> 或者直接用 `docker run`：
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

### 3. 配置 Frigate go2rtc

在 Frigate 配置中添加 go2rtc 码流，指向代理地址：

```yaml
go2rtc:
  streams:
    tplink_camera:
      - rtsp://admin:密码@代理IP:8554/stream1
      - ffmpeg:tplink_camera#audio=opus
```

`代理IP` 替换为运行此容器的机器 IP。

### 4. 重启 Frigate

Frigate 界面会出现**麦克风按钮**，按下即可对着摄像头扬声器喊话。

---

## 工作原理

### RTSP 代理层
- 透明转发摄像头的视频 (H.264) 和麦克风音频 (AAC) 到 go2rtc
- 在 SDP 中注入**回传音频轨道** (track99)，标记为 `a=sendonly`
- go2rtc 检测到 sendonly 轨道后，将 WebRTC 麦克风音频路由到该通道

### 音频处理管线

| 步骤 | 输入 | 输出 | 说明 |
|------|------|------|------|
| 1 | 浏览器 OPUS | go2rtc PCMA 8kHz | go2rtc 转码 |
| 2 | go2rtc PCMA | 16-bit PCM 8kHz | 代理解码 |
| 3 | PCM 8kHz | PCM 16kHz | 升采样到摄像头原生采样率 |
| 4 | PCM 16kHz | μ-law 16kHz | 转换为摄像头默认编码 |
| 5 | μ-law 16kHz | 扬声器 | MULTITRANS RTP 发送 |

### MULTITRANS 协议
TP-Link 专有对讲协议，通过 RTSP `MULTITRANS` 方法实现：
- **认证**：RTSP Digest 摘要认证
- **握手**：JSON `{"method":"get","talk":{"mode":"aec"}}`
- **数据传输**：RTP 交织帧格式 `$` + 1字节通道号 + 2字节长度 + RTP头(PT=102) + μ-law 负载
- **流控**：持续发送音频流，静音时填充分隔包，防止扬声器超时断开

### 平滑缓冲
go2rtc 的音频以变长突发方式到达（WebRTC 抖动），代理使用平滑缓冲区：
- 积累到达的音频块
- 以固定速率排出：每 20ms 发送 320 字节（16kHz μ-law 单声道）
- 缓冲区空时自动填充 μ-law 静音 (`0xFF`/`0x7F` 交替)
- 保证摄像头扬声器输出连续流畅，无卡顿

### 技术要点

| 项目 | 说明 |
|------|------|
| 默认编码 | 摄像头 MULTITRANS 默认 **μ-law (PCMU)** |
| 采样率 | 对讲音频以 **16kHz** 播放 |
| RTP 格式 | 交织通道号 **1 字节**，PT=102 |

---

## HTTP API

### 健康检查

```
GET http://代理IP:8556/
→ 200 OK
```

### 直接音频上传

发送 G.711 A-law 音频直接到摄像头扬声器：

```
POST http://代理IP:8556/talk_g711
Content-Type: application/octet-stream
Body: G.711 A-law 音频字节 (8kHz, 单声道)
```

发送 16-bit PCM 音频（自动转换为 G.711）：

```
POST http://代理IP:8556/talk_pcm
Content-Type: application/octet-stream
Body: 16-bit PCM 音频字节 (8kHz, 单声道, 小端序)
```

---

## 兼容性

已测试：
- **TP-Link TL-IPC48AW-PLUS** (固件 1.0.7)
- **Frigate 0.17.1** + go2rtc 1.9.10
- Docker on Linux (amd64/arm64)

其他支持 MULTITRANS (TUMS) 协议的 TP-Link 摄像头理论上也可用。

---

## 故障排查

**Frigate 没有麦克风按钮：**
- 确认 go2rtc 配置指向代理地址：`rtsp://代理IP:8554/stream1`
- 查看代理日志：`docker logs frigate-tplink-talk`
- 日志中出现 `BC SETUP` 表示回传通道已被检测到

**声音卡顿/断续：**
- 查看日志是否频繁出现 `BC SETUP`（表示 go2rtc 反复重连）
- 尝试重启 Frigate 清理 RTSP 连接
- 确认摄像头连接数未达上限（主码流最多 4 路）

**没有声音或只有噪音：**
- 检查环境变量中摄像头账号密码是否正确
- 查看日志中 MULTITRANS 响应是否包含 `error_code:0`
- 摄像头必须支持 MULTITRANS (TUMS) 协议
