"""
RTU 客户端模块。

本模块实现了 DLT645 协议的 RTU（串口）客户端功能。
"""

import time
import serial
from typing import Optional
from ...common.transform import bytes_to_spaced_hex
from ...transport.client.log import log
from ...protocol.frame import FRAME_START_BYTE, FRAME_END_BYTE
from ...protocol.protocol import DLT645Protocol


class RtuClient:
    """
    RTU 客户端类，用于与 DLT645 设备进行串口通信。

    该类实现了 RTU（Remote Terminal Unit）客户端功能，
    支持与 DLT645 协议设备进行串口通信。

    :ivar port: 串口名称。
    :ivar baud_rate: 波特率。
    :ivar data_bits: 数据位。
    :ivar stop_bits: 停止位。
    :ivar parity: 校验位。
    :ivar timeout: 超时时间（秒）。
    :ivar conn: 串口连接对象。
    """

    def __init__(
        self,
        port: str = "",
        baud_rate: int = 9600,
        data_bits: int = 8,
        stop_bits: int = 1,
        parity: str = serial.PARITY_NONE,
        timeout: float = 1.0,
    ):
        """
        初始化 RTU 客户端。

        :param port: 串口名称（如 "COM1" 或 "/dev/ttyUSB0"）。
        :type port: str
        :param baud_rate: 波特率，默认 9600。
        :type baud_rate: int
        :param data_bits: 数据位，默认 8。
        :type data_bits: int
        :param stop_bits: 停止位，默认 1。
        :type stop_bits: int
        :param parity: 校验位，默认无校验。
        :type parity: str
        :param timeout: 超时时间（秒），默认 1.0。
        :type timeout: float
        """
        self.port = port
        self.baud_rate = baud_rate
        self.data_bits = data_bits
        self.stop_bits = stop_bits
        self.parity = parity
        self.timeout = timeout
        self.conn: Optional[serial.Serial] = None

    def connect(self) -> bool:
        """连接到串口
        
        建立与指定串口的连接，配置为DLT645协议通信所需的参数。
        
        Returns:
            bool: 连接成功返回True，失败返回False
        """
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
        """断开与串口的连接
        
        关闭串口连接并释放资源。
        
        Returns:
            bool: 断开连接成功返回True，失败返回False
        """
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

    def _check_timeout(self, start_time: float) -> bool:
        """检查是否超时

        Args:
            start_time: 开始时间

        Returns:
            bool: 如果超时则返回True，否则返回False
        """
        return time.time() - start_time > self.timeout

    def send_request(
        self,
        data: bytes,
        retries: int = 1,
    ) -> Optional[bytes]:
        """发送请求并接收响应
        
        向DLT645设备发送请求数据，并接收响应。支持超时处理和自动重试机制。
        
        Args:
            data: 要发送的请求数据
            retries: 失败重试次数，默认1次

        Returns:
            bytes: 成功接收的响应数据
            None: 失败时返回
        """
        # 确保连接已建立
        if not self._ensure_connection():
            log.error("Failed to establish serial port connection")
            return None

        # 保存原始超时设置
        original_timeout = self.conn.timeout

        for attempt in range(retries + 1):
            last_data_time = time.time()
            try:
                # 清空缓冲区
                if not self._safe_clear_buffer():
                    log.warning("Buffer clearance failed, proceeding anyway")

                # 发送数据
                written = self.conn.write(data)
                if written != len(data):
                    log.error(f"TX: Write incomplete ({written}/{len(data)} bytes)")
                    continue

                log.info(f"TX: {bytes_to_spaced_hex(data)}")

                # 初始化数据缓冲区和接收状态
                data_buffer = bytearray()
                max_buffer_size = 1024  # 增加缓冲区大小以处理较大的数据

                # 持续读取直到收到完整帧或超时
                while not self._check_timeout(last_data_time):
                    # 读取数据, 在没有数据时等待直到超时
                    chunk = self.conn.read(256)

                    if chunk:
                        data_buffer.extend(chunk)
                        last_data_time = time.time()
                        log.info(f"RX: {bytes_to_spaced_hex(chunk)} len{len(chunk)}")

                    # 无论是否收到数据，只要缓冲区不为空就尝试解析
                    if data_buffer:
                        try:
                            # 使用deserialize_with_remaining解析分片数据
                            remaining_data, frame = (
                                DLT645Protocol.deserialize_with_remaining(data_buffer)
                            )

                            if frame is not None:
                                # 成功解析到完整帧
                                log.info(
                                    f"RX: Successfully parsed frame, buffer size after parsing: {len(remaining_data)}"
                                )
                                return bytes(data_buffer)
                            else:
                                # 更新缓冲区为未解析的剩余数据
                                data_buffer = remaining_data

                                # 检查缓冲区大小限制
                                if len(data_buffer) > max_buffer_size:
                                    log.warning(
                                        f"RX: Buffer overflow, clearing {len(data_buffer)} bytes"
                                    )
                                    data_buffer.clear()
                        except Exception as e:
                            log.error(
                                f"Error parsing data: {type(e).__name__}: {str(e)}"
                            )
                            # 出错时保留数据继续尝试

                    # 小延迟避免CPU占用过高
                    time.sleep(0.001)

                log.warning(
                    f"RX: Timeout after {original_timeout} seconds, received incomplete data"
                )

            except Exception as e:
                log.error(f"Attempt {attempt} failed: {type(e).__name__}: {str(e)}")

            # 非最后一次尝试时延迟重试
            if attempt < retries:
                log.info(f"Retrying ({attempt + 1}/{retries})...")
                time.sleep(0.5 * (attempt + 1))  # 指数退避

        log.error("All attempts failed")
        return None

    def _safe_clear_buffer(self) -> bool:
        """安全清空串口缓冲区
        
        清空输入和输出缓冲区，避免旧数据干扰新的通信。
        
        Returns:
            bool: 清空成功返回True，失败返回False
        """
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
                log.info(
                    "Connection lost or not established, attempting to reconnect..."
                )
                return self.connect()
            return True
        except Exception as e:
            log.error(f"Connection check failed: {str(e)}")
            # 尝试重新连接
            return self.connect()
