import socket
import threading
import time

from ...common.transform import bytes_to_spaced_hex
from ...protocol.protocol import DLT645Protocol
from ...transport.server.log import log


class TcpServer:
    def __init__(self, ip: str, port: int, timeout: float, service):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.ln = None
        self.service = service
        self._server_thread = None
        self._running = False
        self._stop_event = threading.Event()

    def start(self):
        """启动TCP服务器（非阻塞，在后台线程中运行）"""
        if self._running:
            log.warning("TCP server is already running")
            return None
            
        self._stop_event.clear()
        self._running = True
        
        # 在后台线程中启动服务器
        self._server_thread = threading.Thread(target=self._run_server, daemon=True)
        self._server_thread.start()
        
        # 等待服务器启动完成
        time.sleep(0.1)
        log.info(f"TCP server starting in background on {self.ip}:{self.port}")
        return None
    
    def _run_server(self):
        """服务器主循环（在后台线程中运行）"""
        try:
            # 创建 TCP 套接字
            self.ln = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 设置地址可重用
            self.ln.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # 设置非阻塞超时，以便能够响应停止信号
            self.ln.settimeout(1.0)
            # 绑定地址和端口
            self.ln.bind((self.ip, self.port))
            # 开始监听
            self.ln.listen(5)
            log.info(f"TCP server started on port {self.port}")

            while not self._stop_event.is_set():
                try:
                    # 接受连接
                    conn, addr = self.ln.accept()
                    log.info(f"Accepted connection from {addr}")
                    # 设置超时时间
                    conn.settimeout(self.timeout)
                    # 启动新线程处理连接
                    threading.Thread(target=self.handle_connection, args=(conn,), daemon=True).start()
                except socket.timeout:
                    # 超时是正常的，继续检查停止信号
                    continue
                except socket.error as e:
                    if self._stop_event.is_set():
                        break
                    log.error(f"Failed to accept connection: {e}")
                    if hasattr(e, 'errno') and e.errno == 10038:  # 套接字关闭错误
                        break
        except Exception as e:
            log.error(f"Failed to start TCP server: {e}")
        finally:
            self._running = False
            if self.ln:
                try:
                    self.ln.close()
                except:
                    pass
            log.info("TCP server stopped")

    def stop(self):
        """停止TCP服务器"""
        if not self._running:
            log.warning("TCP server is not running")
            return None
            
        log.info("Shutting down TCP server...")
        
        # 设置停止信号
        self._stop_event.set()
        
        # 关闭套接字
        if self.ln:
            try:
                self.ln.close()
            except Exception as e:
                log.error(f"Error closing server socket: {e}")
        
        # 等待服务器线程结束
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=5.0)
            if self._server_thread.is_alive():
                log.warning("Server thread did not stop gracefully")
        
        self._running = False
        log.info("TCP server shutdown complete")
        return None
    
    def is_running(self):
        """检查服务器是否正在运行"""
        return self._running

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
