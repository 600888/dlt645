import socket
import time
from typing import Optional, Any

from src.common.transform import bytes_to_spaced_hex
from src.transport.client.log import log


class TcpClient:
    def __init__(self, ip: str = "", port: int = 0, timeout: float = 5.0):
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
        """增强版TCP请求-响应（带完整超时控制）

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
        response = bytearray()

        for attempt in range(retries + 1):
            try:
                # 0. 初始化计时器
                start_time = time.time()
                response.clear()

                # 1. 设置socket超时（影响后续所有操作）
                self.conn.settimeout(read_timeout)

                # 2. 带超时的数据写入
                try:
                    self.conn.sendall(data)  # sendall本身不返回发送字节数
                    log.info(f"Sent request: {bytes_to_spaced_hex(data)}")
                except socket.timeout:
                    raise TimeoutError(f"Write timeout after {write_timeout}s")

                # 3. 接收数据（带总超时控制）
                while (time.time() - start_time) < total_timeout:
                    try:
                        chunk = self.conn.recv(256)
                        if chunk:
                            response.extend(chunk)
                            log.info(f"Received: {bytes_to_spaced_hex(response)}")
                            return bytes(response)
                        else:  # 空数据表示连接关闭
                            log.warning("Connection closed by peer")
                            break
                    except socket.timeout:
                        # 单次recv超时，检查总超时
                        if (time.time() - start_time) >= total_timeout:
                            break
                        continue

                # 超时或中断处理
                if len(response) >= min_response_len:
                    log.warning(
                        f"Incomplete response ({len(response)} bytes): {bytes_to_spaced_hex(response)}"
                    )
                else:
                    log.error(f"No valid response within {total_timeout}s")

            except TimeoutError as e:
                log.error(str(e))
            except Exception as e:
                log.error(f"Attempt {attempt} failed: {type(e).__name__}: {str(e)}")

            # 非最后一次尝试时延迟重试
            if attempt < retries:
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
