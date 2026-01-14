"""
TCP 客户端模块。

本模块实现了 DLT645 协议的 TCP 客户端功能。
"""

import socket
import time
from typing import Optional, Any

from ...common.transform import bytes_to_spaced_hex
from ...protocol.protocol import DLT645Protocol
from ...transport.client.log import log


class TcpClient:
    """
    TCP 客户端类，用于与 DLT645 设备进行 TCP 通信。

    :ivar ip: 服务器 IP 地址。
    :ivar port: 服务器端口号。
    :ivar timeout: 连接超时时间（秒）。
    :ivar conn: socket 连接对象。
    """

    def __init__(self, ip: str = "", port: int = 0, timeout: float = 5.0):
        """
        初始化 TCP 客户端。

        :param ip: 服务器 IP 地址（如 '0.0.0.0'）。
        :type ip: str
        :param port: 服务器端口号。
        :type port: int
        :param timeout: 连接超时时间（秒），默认 5.0。
        :type timeout: float
        """
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.conn: Optional[socket.socket] = None

    def connect(self) -> bool:
        """连接到服务器"""
        address = f"{self.ip}:{self.port}"
        try:
            self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.conn.settimeout(self.timeout)
            self.conn.connect((self.ip, self.port))
            log.info(f"成功连接到服务器 {address}")
            return True
        except Exception as e:
            log.error(f"连接服务器失败: {e}")
            return False

    def disconnect(self) -> bool:
        """断开与服务器的连接"""
        if self.conn is not None:
            try:
                self.conn.close()
                self.conn = None
                log.info("已断开与服务器的连接")
                return True
            except Exception as e:
                log.error(f"断开连接失败: {e}")
                return False
        return True

    def send_request(
        self,
        data: bytes,
        write_timeout: float = 2.0,
        read_timeout: float = 5.0,
        total_timeout: float = 10.0,
        min_response_len: int = 1,
        retries: int = 1,
    ) -> Optional[bytes]:
        """增强版TCP请求-响应（支持超时控制和分片数据处理）

        Args:
            data: 要发送的请求数据
            write_timeout: 数据写入超时(秒)
            read_timeout: 单次recv操作的超时(秒)
            total_timeout: 整个请求-响应的总超时(秒)
            min_response_len: 最小有效响应长度
            retries: 失败重试次数

        Returns:
            bytes: 成功接收的响应数据
            None: 超时或失败时返回      
        """
        if self.conn is None:
            log.error("Not connected to server")
            return None

        original_timeout = self.conn.gettimeout()  # 保存原始超时设置
        data_buffer = bytearray()

        for attempt in range(retries + 1):
            try:
                # 0. 初始化计时器和缓冲区
                start_time = time.time()
                data_buffer.clear()

                # 1. 设置socket超时（影响后续所有操作）
                self.conn.settimeout(read_timeout)

                # 2. 带超时的数据写入
                try:
                    self.conn.sendall(data)
                    log.info(f"TX: {bytes_to_spaced_hex(data)}")
                except socket.timeout:
                    raise TimeoutError(f"Write timeout after {write_timeout}s")

                # 3. 接收数据（带总超时控制和分片处理）
                while (time.time() - start_time) < total_timeout:
                    try:
                        # 读取数据到缓冲区
                        chunk = self.conn.recv(1024)  # 增加缓冲区大小
                        if chunk:
                            data_buffer.extend(chunk)
                            log.info(
                                f"RX: {bytes_to_spaced_hex(chunk)} (buffer size: {len(data_buffer)})"
                            )

                            # 尝试解析缓冲区中的数据
                            try:
                                remaining_data, frame = (
                                    DLT645Protocol.deserialize_with_remaining(
                                        bytes(data_buffer)
                                    )
                                )
                                if frame is not None:
                                    log.debug(
                                        f"Successfully received complete response: {bytes_to_spaced_hex(data_buffer)}"
                                    )
                                    # 恢复原始超时设置
                                    self.conn.settimeout(original_timeout)
                                    return data_buffer
                            except Exception as parse_error:
                                log.warning(
                                    f"Parse error (might be incomplete data): {parse_error}"
                                )
                                # 继续等待更多数据
                                continue
                        else:  # 空数据表示连接关闭
                            log.warning("Connection closed by peer")
                            break
                    except socket.timeout:
                        # 单次recv超时，检查总超时
                        if (time.time() - start_time) >= total_timeout:
                            log.warning(f"Total timeout reached after {total_timeout}s")
                            break
                        # 继续等待更多数据
                        continue

                # 超时或中断处理
                if len(data_buffer) >= min_response_len:
                    log.warning(
                        f"Incomplete response ({len(data_buffer)} bytes): {bytes_to_spaced_hex(data_buffer)}"
                    )
                else:
                    log.error(f"No valid response within {total_timeout}s")

            except TimeoutError as e:
                log.error(str(e))
            except Exception as e:
                log.error(f"Attempt {attempt} failed: {type(e).__name__}: {str(e)}")

            # 非最后一次尝试时延迟重试
            if attempt < retries:
                log.info(f"Retrying ({attempt+1}/{retries})...")
                time.sleep(0.5 * (attempt + 1))  # 指数退避
                # 重连逻辑（如果连接已断开）
                if not self._ensure_connection():
                    continue

        # 恢复原始超时设置
        self.conn.settimeout(original_timeout)
        return None

    def _ensure_connection(self) -> bool:
        """确保连接有效（用于重试时重新连接）"""
        if self.conn is None:
            return self.connect()

        # 简单检查连接是否仍有效
        try:
            self.conn.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            return True
        except:
            self.disconnect()
            return self.connect()

    def _safe_sendall(self, data: bytes, timeout: float) -> bool:
        """带超时的sendall实现"""
        self.conn.settimeout(timeout)
        try:
            self.conn.sendall(data)
            return True
        except socket.timeout:
            return False
        finally:
            self.conn.settimeout(self.timeout)  # 恢复原始超时

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.disconnect()
