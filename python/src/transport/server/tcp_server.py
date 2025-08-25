import socket

from src.common.transform import bytes_to_spaced_hex
from src.protocol.protocol import DLT645Protocol
from src.transport.server.log import log


class TcpServer:
    def __init__(self, ip: str, port: int, timeout: float, service):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.ln = None
        self.service = service

    def start(self):
        try:
            # 创建 TCP 套接字
            self.ln = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 设置地址可重用
            self.ln.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # 绑定地址和端口
            self.ln.bind((self.ip, self.port))
            # 开始监听
            self.ln.listen(5)
            log.info(f"TCP server started on port {self.port}")

            while True:
                try:
                    # 接受连接
                    conn, addr = self.ln.accept()
                    log.info(f"Accepted connection from {addr}")
                    # 设置超时时间
                    conn.settimeout(self.timeout)
                    # 启动新线程处理连接
                    import threading
                    threading.Thread(target=self.handle_connection, args=(conn,)).start()
                except socket.error as e:
                    if isinstance(e, socket.timeout):
                        continue
                    log.error(f"Failed to accept connection: {e}")
                    if not e.errno == 10038:  # 非套接字关闭错误
                        return e
        except Exception as e:
            log.error(f"Failed to start TCP server: {e}")
            return e

    def stop(self):
        if self.ln:
            log.info("Shutting down TCP server...")
            try:
                self.ln.close()
            except Exception as e:
                log.error(f"Error closing server: {e}")
                return e
        return None

    def handle_connection(self, conn):
        try:
            while True:
                try:
                    # 接收数据
                    buf = conn.recv(256)
                    if not buf:
                        break
                    log.info(f"Received data: {bytes_to_spaced_hex(buf)}")

                    # 协议解析
                    try:
                        frame = DLT645Protocol.deserialize(buf)
                    except Exception as e:
                        log.error(f"Error parsing frame: {e}")
                        continue

                    # 业务处理
                    try:
                        resp = self.service.handle_request(frame)
                    except Exception as e:
                        log.error(f"Error handling request: {e}")
                        continue

                    # 响应
                    if resp:
                        try:
                            conn.sendall(resp)
                            log.info(f"Sent response: {bytes_to_spaced_hex(resp)}")
                        except Exception as e:
                            log.error(f"Error writing response: {e}")
                except socket.timeout:
                    break
        except Exception as e:
            log.error(f"Error handling connection: {e}")
        finally:
            try:
                conn.close()
            except Exception as e:
                log.error(f"Error closing connection: {e}")
