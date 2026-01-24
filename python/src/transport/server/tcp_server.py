"""TCP 服务器模块。

本模块实现了 DLT645 协议的 TCP 服务器功能。
"""

import socket
import threading
import time
from typing import Optional

from ...common.transform import bytes_to_spaced_hex
from ...common.message_capture import MessageCapture
from ...protocol.protocol import DLT645Protocol
from ...transport.server.log import log


class TcpServer:
    """TCP 服务器类，用于与 DLT645 客户端进行 TCP 通信。

    :ivar ip: 服务器 IP 地址。
    :ivar port: 服务器端口号。
    :ivar timeout: 连接超时时间（秒）。
    :ivar ln: 监听套接字。
    :ivar service: 服务实例，用于处理业务逻辑。
    """

    def __init__(self, ip: str, port: int, timeout: float, service):
        """初始化 TCP 服务器。

        :param ip: 服务器 IP 地址（如 '0.0.0.0'）。
        :type ip: str
        :param port: 服务器端口号。
        :type port: int
        :param timeout: 连接超时时间（秒）。
        :type timeout: float
        :param service: 服务实例，用于处理业务逻辑。
        :type service: Any
        """
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.ln = None
        self.service = service
        self._server_thread = None
        self._running = False
        self._stop_event = threading.Event()
        # 跟踪所有活跃的客户端连接
        self._connections = []
        # 用于保护连接列表的锁
        self._connections_lock = threading.Lock()
        # 报文捕获管理器
        self._message_capture: Optional[MessageCapture] = None

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

                    # 将连接添加到活跃连接列表
                    with self._connections_lock:
                        self._connections.append(conn)

                    # 启动新线程处理连接
                    threading.Thread(
                        target=self.handle_connection, args=(conn,), daemon=True
                    ).start()
                except socket.timeout:
                    # 超时是正常的，继续检查停止信号
                    continue
                except socket.error as e:
                    if self._stop_event.is_set():
                        break
                    log.error(f"Failed to accept connection: {e}")
                    if hasattr(e, "errno") and e.errno == 10038:  # 套接字关闭错误
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

        # 主动关闭所有活跃的客户端连接
        with self._connections_lock:
            for conn in self._connections:
                try:
                    conn.close()
                    log.info(f"Closed active connection: {conn}")
                except Exception as e:
                    log.error(f"Error closing client connection: {e}")
            # 清空连接列表
            self._connections.clear()

        # 关闭服务器套接字
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
            # 初始化数据缓冲区，用于累积接收的数据
            data_buffer = bytearray()

            while not self._stop_event.is_set():
                try:
                    # 接收数据
                    buf = conn.recv(256)

                    if not buf:
                        continue

                    # 将新接收的数据添加到缓冲区
                    data_buffer.extend(buf)
                    log.info(f"RX: {bytes_to_spaced_hex(buf)} (len:{len(data_buffer)})")
                    
                    # 捕获接收的报文
                    current_tx_id: Optional[str] = None
                    if self._message_capture:
                        current_tx_id = self._message_capture.capture_rx_for_server(buf)

                    # 尝试解析缓冲区中的数据
                    try:
                        # 尝试从缓冲区中提取完整的帧
                        remaining_data, frame = (
                            DLT645Protocol.deserialize_with_remaining(
                                bytes(data_buffer)
                            )
                        )

                        if frame is not None:
                            # 解析成功，更新缓冲区为剩余未解析的数据
                            data_buffer = bytearray(remaining_data)
                            log.info(
                                f"Successfully parsed frame, remaining buffer size: {len(remaining_data)}"
                            )

                            # 业务处理
                            try:
                                resp = self.service.handle_request(frame)

                                # 响应
                                if resp:
                                    try:
                                        conn.sendall(resp)
                                        log.info(
                                            f"TX: {bytes_to_spaced_hex(resp)} (len:{len(resp)})"
                                        )
                                        # 捕获发送的报文并与接收配对
                                        if self._message_capture:
                                            self._message_capture.capture_tx_for_server(resp, current_tx_id)
                                    except Exception as e:
                                        log.error(f"Error writing response: {e}")
                            except Exception as e:
                                log.error(f"Error handling request: {e}")

                            # 继续循环，处理缓冲区中剩余的数据
                            continue

                        # 如果没有完整的帧，但收到了新数据，继续等待
                        # 注意：这里不会清空缓冲区，而是保持数据以等待后续数据

                    except Exception as e:
                        # 解析错误，但不立即清空缓冲区
                        # 可能是因为数据不完整，等待更多数据
                        log.warning(
                            f"Error parsing frame (might be incomplete data): {e}"
                        )
                        # 只有在确定是无效数据格式时才清空缓冲区
                        # 这里可以根据具体的异常类型或错误信息来判断

                except socket.timeout:
                    # 清空缓冲区
                    if len(data_buffer) > 0:
                        log.warning(
                            f"Connection timeout with {len(data_buffer)} bytes in buffer, clearing buffer {bytes_to_spaced_hex(data_buffer)}"
                        )
                    data_buffer.clear()
        except Exception as e:
            log.error(f"Error handling connection: {e}")
        finally:
            try:
                # 将连接从活跃连接列表中移除
                with self._connections_lock:
                    if conn in self._connections:
                        self._connections.remove(conn)

                conn.close()
                log.info("Connection closed")
            except Exception as e:
                log.error(f"Error closing connection: {e}")
