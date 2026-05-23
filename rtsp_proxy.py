#!/usr/bin/env python3
"""RTSP Proxy + MULTITRANS Talk for TP-Link Camera → Frigate two-way audio."""

import socket, threading, re, os, struct, time, random, base64, hashlib, queue

CAM_HOST = os.getenv('CAMERA_HOST', '10.40.0.1')
CAM_PORT = int(os.getenv('CAMERA_PORT', '554'))
CAM_USER = os.getenv('CAMERA_USER', 'admin')
CAM_PASS = os.getenv('CAMERA_PASSWORD', 'admin')
CAM_PATH = os.getenv('CAMERA_PATH', '/stream1')
LISTEN_PORT = int(os.getenv('LISTEN_PORT', '8554'))

_GT = [0x48,0x48,0x48,0x48,0x50,0x50,0x50,0x50,0xfd,0xfd,0xfd,0xfd,0xed,0xed,0xed,0xed,0xb9,0xb9,0xb9,0xb9,0xda,0xda,0xda,0xda,0x5e,0x5e,0x5e,0x5e,0x15,0x15,0x15,0x15,0x46,0x46,0x46,0x46,0x57,0x57,0x57,0x57,0xa7,0xa7,0xa7,0xa7,0x8d,0x8d,0x8d,0x8d,0x9d,0x9d,0x9d,0x9d,0x84,0x84,0x84,0x84,0x90,0x90,0x90,0x90,0xd8,0xd8,0xd8,0xd8,0xab,0xab,0xab,0xab,0x0,0x0,0x0,0x0,0x8c,0x8c,0x8c,0x8c,0xbc,0xbc,0xbc,0xbc,0xd3,0xd3,0xd3,0xd3,0xa,0xa,0xa,0xa,0xf7,0xf7,0xf7,0xf7,0xe4,0xe4,0xe4,0xe4,0x58,0x58,0x58,0x58,0x5,0x5,0x5,0x5,0xb8,0xb8,0xb8,0xb8,0xb3,0xb3,0xb3,0xb3,0x45,0x45,0x45,0x45,0x6,0x6,0x6,0x6,0xd0,0xd0,0xd0,0xd0,0x2c,0x2c,0x2c,0x2c,0x1e,0x1e,0x1e,0x1e,0x8f,0x8f,0x8f,0x8f,0xca,0xca,0xca,0xca,0x3f,0x3f,0x3f,0x3f,0xf,0xf,0xf,0xf,0x2,0x2,0x2,0x2,0xc1,0xc1,0xc1,0xc1,0xaf,0xaf,0xaf,0xaf,0xbd,0xbd,0xbd,0xbd,0x3,0x3,0x3,0x3,0x1,0x1,0x1,0x1,0x13,0x13,0x13,0x13,0x8a,0x8a,0x8a,0x8a,0x6b,0x6b,0x6b,0x6b,0x3a,0x3a,0x3a,0x3a,0x91,0x91,0x91,0x91,0x11,0x11,0x11,0x11,0x41,0x41,0x41,0x41,0x4f,0x4f,0x4f,0x4f,0x67,0x67,0x67,0x67,0xdc,0xdc,0xdc,0xdc,0xea,0xea,0xea,0xea,0x97,0x97,0x97,0x97,0xf2,0xf2,0xf2,0xf2,0xcf,0xcf,0xcf,0xcf,0xce,0xce,0xce,0xce,0xf0,0xf0,0xf0,0xf0,0xb4,0xb4,0xb4,0xb4,0xe6,0xe6,0xe6,0xe6,0x73,0x73,0x73,0x73,0x96,0x96,0x96,0x96,0xac,0xac,0xac,0xac,0x74,0x74,0x74,0x74,0x22,0x22,0x22,0x22,0xe7,0xe7,0xe7,0xe7,0xad,0xad,0xad,0xad,0x35,0x35,0x35,0x35,0x85,0x85,0x85,0x85,0xe2,0xe2,0xe2,0xe2,0xf9,0xf9,0xf9,0xf9,0x37,0x37,0x37,0x37,0xe8,0xe8,0xe8,0xe8,0x1c,0x1c,0x1c,0x1c,0x75,0x75,0x75,0x75,0xdf,0xdf,0xdf,0xdf,0x6e,0x6e,0x6e,0x6e,0x47,0x47,0x47,0x47,0xf1,0xf1,0xf1,0xf1,0x1a,0x1a,0x1a,0x1a,0x71,0x71,0x71,0x71,0x1d,0x1d,0x1d,0x1d,0x29,0x29,0x29,0x29,0xc5,0xc5,0xc5,0xc5,0x89,0x89,0x89,0x89,0x6f,0x6f,0x6f,0x6f,0xb7,0xb7,0xb7,0xb7,0x62,0x62,0x62,0x62,0xe,0xe,0xe,0xe,0xaa,0xaa,0xaa,0xaa,0x18,0x18,0x18,0x18,0xbe,0xbe,0xbe,0xbe,0x1b,0x1b,0x1b,0x1b,0xfc,0xfc,0xfc,0xfc,0x56,0x56,0x56,0x56,0x3e,0x3e,0x3e,0x3e,0x4b,0x4b,0x4b,0x4b,0xc6,0xc6,0xc6,0xc6,0xd2,0xd2,0xd2,0xd2,0x79,0x79,0x79,0x79,0x20,0x20,0x20,0x20,0x9a,0x9a,0x9a,0x9a,0xdb,0xdb,0xdb,0xdb,0xc0,0xc0,0xc0,0xc0,0xfe,0xfe,0xfe,0xfe,0x78,0x78,0x78,0x78,0xcd,0xcd,0xcd,0xcd,0x5a,0x5a,0x5a,0x5a,0xf4,0xf4,0xf4,0xf4,0x1f,0x1f,0x1f,0x1f,0xdd,0xdd,0xdd,0xdd,0xa8,0xa8,0xa8,0xa8,0x33,0x33,0x33,0x33,0x88,0x88,0x88,0x88,0x7,0x7,0x7,0x7,0xc7,0xc7,0xc7,0xc7,0x31,0x31,0x31,0x31,0xb1,0xb1,0xb1,0xb1,0x12,0x12,0x12,0x12,0x10,0x10,0x10,0x10,0x59,0x59,0x59,0x59,0x27,0x27,0x27,0x27,0x80,0x80,0x80,0x80,0xec,0xec,0xec,0xec,0x5f,0x5f,0x5f,0x5f,0x60,0x60,0x60,0x60,0x51,0x51,0x51,0x51]
def pcm2g711(p):
    r=bytearray(len(p)//2)
    for i in range(0,len(p)-1,2):
        v=p[i]|(p[i+1]<<8)
        if v>=0x8000:
            v-=0x10000
        v=v>>3
        a=abs(v)
        idx=((a>>3)&0x1FF)if a<=4095 else 0x1FF
        r[i//2]=_GT[idx^0xFF]&0x7F if v<0 else _GT[idx]|0x80
    return bytes(r)

def g711_gain(data,factor=1):
    import audioop
    pcm=audioop.alaw2lin(data,2)
    if factor!=1:
        pcm=audioop.mul(pcm,2,factor)
    return pcm2g711(pcm)

class TalkSession:
    def __init__(self):
        self.buf=bytearray()
        self.sock=None
        self.seq=0
        self.ts=0
        self.ssrc=random.randint(0,0xffffffff)
        self.lock=threading.Lock()
        self.t=threading.Thread(target=self._run,daemon=True)
        self.t.start()

    def send(self,g711):
        with self.lock:
            self.buf.extend(g711)

    def _run(self):
        try:
            s=socket.socket()
            s.settimeout(10)
            s.connect((CAM_HOST,CAM_PORT))
            self.sock=s
            s.sendall(b'MULTITRANS rtsp://127.0.0.1/multitrans RTSP/1.0\r\nCSeq:0\r\nContent-Length:0\r\nX-Handshake:unused debug\r\n\r\n')
            b=b''
            while b'\r\n\r\n' not in b:
                c=s.recv(4096)
                b+=c
            h=b[:b.find(b'\r\n\r\n')].decode(errors='ignore')
            n=re.search(r'nonce="([^"]+)"',h).group(1)
            rm=re.search(r'realm="([^"]+)"',h).group(1)
            ha1=hashlib.md5(f"{CAM_USER}:{rm}:{CAM_PASS}".encode()).hexdigest()
            ha2=hashlib.md5(b"MULTITRANS:rtsp://127.0.0.1/multitrans").hexdigest()
            r=hashlib.md5(f"{ha1}:{n}:{ha2}".encode()).hexdigest()
            s.sendall(f'MULTITRANS rtsp://127.0.0.1/multitrans RTSP/1.0\r\nCSeq:1\r\nContent-Type:application/json\r\nX-Handshake:unused\r\nAuthorization:Digest username="{CAM_USER}",realm="{rm}",nonce="{n}",uri="rtsp://127.0.0.1/multitrans",response="{r}"\r\n\r\n'.encode())
            b=b''
            while b'\r\n\r\n' not in b:
                c=s.recv(4096)
                b+=c
            talk='{"type":"request","seq":0,"params":{"method":"get","talk":{"mode":"aec"}}}'
            s.sendall(f'MULTITRANS rtsp://127.0.0.1/multitrans RTSP/1.0\r\nCSeq:2\r\nContent-Type:application/json\r\nContent-Length:{len(talk)}\r\n\r\n{talk}'.encode())
            b=b''
            while b'\r\n\r\n' not in b:
                c=s.recv(4096)
                b+=c
            hdr=b[:b.find(b'\r\n\r\n')].decode(errors='ignore')
            cl=re.search(r'Content-Length:\s*(\d+)',hdr,re.I)
            body=''
            if cl:
                n=int(cl.group(1))
                bs=b.find(b'\r\n\r\n')+4
                while len(b)-bs<n:
                    b+=s.recv(min(4096,n-(len(b)-bs)))
                body=b[bs:bs+n].decode(errors='ignore')
            print(f"  [Talk] response: {body[:200]}")
            chunk=320
            silence=b'\xff\xff\x7f\x7f'*80
            while True:
                with self.lock:
                    if len(self.buf)>=chunk:
                        data=bytes(self.buf[:chunk])
                        self.buf=self.buf[chunk:]
                    else:
                        data=None
                if data is None:
                    data=silence
                self._send_g711(s,data)
                time.sleep(0.02)
        except Exception as e:
            print(f"  [Talk] {e}")
        finally:
            try:
                self.sock.close()
            except:
                pass
            self.sock=None

    def _send_g711(self,s,g711):
        frame=struct.pack('!BBH',0x24,1,12+len(g711))+struct.pack('!BBHII',0x80,102,self.seq,self.ts,self.ssrc)+g711
        try:
            s.sendall(frame)
        except Exception as e:
            print(f"  [Talk] send error: {e}")
            raise
        self.seq=(self.seq+1)&0xffff
        self.ts=(self.ts+len(g711))&0xffffffff

_talk_session=None
_talk_lock=threading.Lock()

def talk_send(g711):
    global _talk_session
    with _talk_lock:
        if _talk_session is None or _talk_session.sock is None:
            _talk_session=TalkSession()
    _talk_session.send(g711)

def read_rtsp(s):
    r=b''
    while b'\r\n\r\n' not in r:
        c=s.recv(8192)
        if not c:
            break
        r+=c
    if not r:
        return r
    h=r[:r.find(b'\r\n\r\n')].decode(errors='ignore')
    cl=re.search(r'Content-Length:\s*(\d+)',h,re.I)
    if cl:
        n=int(cl.group(1))
        bs=r.find(b'\r\n\r\n')+4
        while len(r)-bs<n:
            r+=s.recv(min(4096,n-(len(r)-bs)))
    return r

def handle(client, addr):
    cam=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    cam.settimeout(30)
    cam.connect((CAM_HOST,CAM_PORT))
    bc_ch=None
    try:
        while True:
            client.settimeout(30)
            data=client.recv(8192)
            if not data:
                break

            if b"track99" in data and b"SETUP" in data:
                m=re.search(rb"interleaved=(\d+)-(\d+)",data)
                bc=int(m.group(1))if m else 10
                bc_ch=bc
                cs=data.decode(errors='ignore').split('CSeq:')[1].split('\r\n')[0].strip()if b'CSeq:'in data else'99'
                client.sendall(f"RTSP/1.0 200 OK\r\nCSeq:{cs}\r\nTransport:RTP/AVP/TCP;unicast;interleaved={bc}-{bc+1}\r\nSession:BC\r\n\r\n".encode())
                print(f"  BC SETUP ch{bc}")
                continue

            cam.sendall(data)
            resp=read_rtsp(cam)
            if not resp:
                break

            if b"DESCRIBE" in data and b'200 OK' in resp:
                hdr_end=resp.find(b'\r\n\r\n')+4
                headers=resp[:hdr_end].decode(errors='ignore')
                sdp=resp[hdr_end:].decode(errors='ignore')
                hm=re.search(r"rtsp://([^/:]+)(:\d+)?/",data.decode(errors='ignore'))
                rh=hm.group(1)if hm else'127.0.0.1'
                rp=hm.group(2)[1:]if hm and hm.group(2)else str(LISTEN_PORT)
                headers=re.sub(r"Content-Base:\s*rtsp://[^/]+/",f"Content-Base: rtsp://{rh}:{rp}/",headers)
                sdp+="\r\nm=audio 0 RTP/AVP 8\r\na=rtpmap:8 PCMA/8000\r\na=sendonly\r\na=setup:passive\r\na=control:track99\r\n"
                headers=re.sub(r"Content-Length:\s*\d+",f"Content-Length: {len(sdp)}",headers)
                resp=(headers+sdp).encode()
            elif b"DESCRIBE" in data:
                rs=resp.decode(errors='ignore')
                hm=re.search(r"rtsp://([^/:]+)(:\d+)?/",data.decode(errors='ignore'))
                rh=hm.group(1)if hm else'127.0.0.1'
                rp=hm.group(2)[1:]if hm and hm.group(2)else str(LISTEN_PORT)
                rs=re.sub(r"Content-Base:\s*rtsp://[^/]+/",f"Content-Base: rtsp://{rh}:{rp}/",rs)
                resp=rs.encode()

            client.sendall(resp)

            if data.startswith(b'PLAY'):
                if b'200' not in resp:
                    cs=data.decode(errors='ignore').split('CSeq:')[1].split('\r\n')[0].strip()if b'CSeq:'in data else'5'
                    client.sendall(f"RTSP/1.0 200 OK\r\nCSeq:{cs}\r\nSession:cam\r\n\r\n".encode())
                print(f"  Relay {addr}")
                _bc=bc_ch
                def c2l():
                    try:
                        while True:
                            d=cam.recv(8192)
                            if not d:
                                break
                            client.sendall(d)
                    except:
                        pass
                def l2c():
                    try:
                        while True:
                            d=client.recv(8192)
                            if not d:
                                break
                            if d and d[0]==0x24 and len(d)>=4:
                                ch=d[1]
                                if _bc and ch==_bc:
                                    sz=struct.unpack('!H',d[2:4])[0]
                                    pl=d[4:4+sz]
                                    if len(pl)>12:
                                        import audioop
                                        raw=pl[12:]
                                        pcm=audioop.alaw2lin(raw,2)
                                        pcm16=audioop.ratecv(pcm,2,1,8000,16000,None)[0]
                                        ulaw=audioop.lin2ulaw(pcm16,2)
                                        talk_send(ulaw)
                                    continue
                            cam.sendall(d)
                    except:
                        pass
                t1=threading.Thread(target=c2l,daemon=True)
                t2=threading.Thread(target=l2c,daemon=True)
                t1.start()
                t2.start()
                t1.join()
                t2.join()
                break
    except Exception as e:
        print(f"  Error: {e}")
    finally:
        cam.close()
        client.close()

def start_http():
    from http.server import HTTPServer,BaseHTTPRequestHandler
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path=='/debug.wav':
                try:
                    import subprocess,os
                    if os.path.exists('/tmp/debug_raw.pcm'):
                        subprocess.run(['sox','-t','raw','-r','8000','-e','signed','-b','16','-c','1','/tmp/debug_raw.pcm','/tmp/debug_audio.wav'],check=True)
                        with open('/tmp/debug_audio.wav','rb') as f:
                            data=f.read()
                        self.send_response(200)
                        self.send_header('Content-Type','audio/wav')
                        self.send_header('Content-Length',len(data))
                        self.end_headers()
                        self.wfile.write(data)
                        return
                except:
                    pass
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'ok')
        def do_POST(self):
            cl=int(self.headers.get('Content-Length',0))
            if cl==0:
                self.send_response(400)
                self.end_headers()
                return
            data=self.rfile.read(cl)
            g711=data if self.path=='/talk_g711' else pcm2g711(data)
            threading.Thread(target=talk_send,args=(g711,),daemon=True).start()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'ok')
        def log_message(self,*a):
            pass
    HTTPServer(('0.0.0.0',int(os.getenv('HTTP_PORT','8556'))),H).serve_forever()

threading.Thread(target=start_http,daemon=True).start()

srv=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
srv.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
srv.bind(('0.0.0.0',LISTEN_PORT))
srv.listen(5)
print(f"Proxy :{LISTEN_PORT} -> {CAM_HOST}:{CAM_PORT} | Talk :{os.getenv('HTTP_PORT','8556')}/talk_g711")
while True:
    c,a=srv.accept()
    threading.Thread(target=handle,args=(c,a),daemon=True).start()
