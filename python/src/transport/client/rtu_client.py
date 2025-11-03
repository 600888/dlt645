import time
import serial
from typing import Optional
from ...common.transform import bytes_to_spaced_hex
from ...transport.client.log import log
from ...protocol.frame import FRAME_START_BYTE, FRAME_END_BYTE


class RtuClient:
    def __init__(
        self,
        port: str = "",
        baud_rate: int = 9600,
        data_bits: int = 8,
        stop_bits: int = 1,
        parity: str = serial.PARITY_NONE,
        timeout: float = 1.0,
    ):
        self.port = port
        self.baud_rate = baud_rate
        self.data_bits = data_bits
        self.stop_bits = stop_bits
        self.parity = parity
        self.timeout = timeout
        self.conn: Optional[serial.Serial] = None

    def connect(self) -> bool:
        """连接到串口"""
        try:
            self.conn = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                bytesize=self.data_bits,
                stopbits=self.stop_bits,
                parity=self.parity,
                timeout=self.timeout,
            )
            log.info(f"RTU client connected to port {self.port}")
            return True
        except Exception as e:
            log.error(f"Failed to open serial port: {e}")
            return False

    def _is_valid_response(self, response: bytearray) -> bool:
        """检查响应是否为有效的DLT645帧

        Args:
            response: 接收到的响应数据

        Returns:
            bool: 如果响应包含完整的DLT645帧则返回True
        """
        # 检查是否同时包含起始字节和结束字节
        if FRAME_START_BYTE in response and FRAME_END_BYTE in response:
            # 确保结束字节在起始字节之后
            start_pos = response.find(FRAME_START_BYTE)
            end_pos = response.find(FRAME_END_BYTE, start_pos)
            if end_pos > start_pos:
                # 检查帧长度是否合理（最小帧长度约为12字节）
                if end_pos - start_pos >= 12:
                    return True
        return False

    def disconnect(self) -> bool:
        """断开与串口的连接"""
        if self.conn is not None:
            try:
                self.conn.close()
                self.conn = None
                log.info(f"RTU client disconnected from port {self.port}")
                return True
            except Exception as e:
                log.error(f"Failed to close serial port: {e}")
                return False
        return True

    def send_request(
        self,
        data: bytes,
        retries: int = 1,
    ) -> Optional[bytes]:
        """简化版串口请求-响应

        Args:
            data: 要发送的请求数据
            retries: 失败重试次数

        Returns:
            bytes: 成功接收的响应数据
            None: 失败时返回
        """
        # 确保连接已建立
        if not self._ensure_connection():
            log.error("Failed to establish serial port connection")
            return None

        response = bytearray()

        for attempt in range(retries + 1):
            try:
                # 清空缓冲区
                if not self._safe_clear_buffer():
                    log.warning("Buffer clearance failed, proceeding anyway")

                # 发送数据
                written = self.conn.write(data)
                if written != len(data):
                    log.error(f"Write incomplete ({written}/{len(data)} bytes)")
                    continue

                log.info(f"Sent: {bytes_to_spaced_hex(data)}")

                # 接收数据（持续读取直到收到完整帧）
                response.clear()
                while True:
                    # 读取数据
                    chunk = self.conn.read(256)
                    if chunk:
                        response.extend(chunk)
                        # 检查是否收到完整的DLT645帧
                        if self._is_valid_response(response):
                            log.info(f"Received: {bytes_to_spaced_hex(response)}")
                            return bytes(response)

            except Exception as e:
                log.error(f"Attempt {attempt} failed: {type(e).__name__}: {str(e)}")

            # 非最后一次尝试时延迟重试
            if attempt < retries:
                log.info(f"Retrying ({attempt + 1}/{retries})...")
                time.sleep(0.5 * (attempt + 1))  # 指数退避

        log.error("All attempts failed")
        return None

    def _safe_clear_buffer(self) -> bool:
        """安全清空串口缓冲区"""
        try:
            if self.conn is not None:
                self.conn.reset_input_buffer()
                if hasattr(self.conn, "reset_output_buffer"):
                    self.conn.reset_output_buffer()
                return True
        except Exception as e:
            log.warning(f"Clear buffer failed: {str(e)}")
        return False
    
    def _ensure_connection(self) -> bool:
        """确保串口连接已建立，如果连接断开则尝试重新连接
        
        Returns:
            bool: 连接是否成功建立
        """
        try:
            # 检查连接是否存在且打开
            if self.conn is None or not self.conn.is_open:
                log.info("Connection lost or not established, attempting to reconnect...")
                return self.connect()
            return True
        except Exception as e:
            log.error(f"Connection check failed: {str(e)}")
            # 尝试重新连接
            return self.connect()
