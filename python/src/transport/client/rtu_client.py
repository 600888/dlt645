import time
import serial
from typing import Optional
from ...common.transform import bytes_to_spaced_hex
from ...transport.client.log import log


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
        write_timeout: float = 2.0,
        read_timeout: float = 5.0,
        total_timeout: float = 10.0,
        min_response_len: int = 1,
        retries: int = 1,
    ) -> Optional[bytes]:
        """增强版串口请求-响应（带完整超时控制）

        Args:
            data: 要发送的请求数据
            write_timeout: 数据写入超时(秒)
            read_timeout: 单次读取操作的超时(秒)
            total_timeout: 整个请求-响应的总超时(秒)
            min_response_len: 最小有效响应长度
            retries: 失败重试次数

        Returns:
            bytes: 成功接收的响应数据
            None: 超时或失败时返回
        """
        if self.conn is None:
            log.error("Serial port not connected")
            return None

        original_timeout = self.conn.timeout  # 保存原始超时设置
        response = bytearray()

        for attempt in range(retries + 1):
            try:
                # 0. 初始化计时器
                start_time = time.time()
                response.clear()

                # 1. 设置读取超时（影响每次read操作）
                self.conn.timeout = read_timeout

                # 2. 安全清空缓冲区
                if not self._safe_clear_buffer():
                    log.warning("Buffer clearance failed, proceeding anyway")

                # 3. 带超时的数据写入
                write_start = time.time()
                written = self.conn.write(data)
                if written != len(data):
                    log.error(f"Write incomplete ({written}/{len(data)} bytes)")
                    continue

                log.info(f"Sent: {bytes_to_spaced_hex(data)}")

                # 4. 接收数据（带总超时控制）
                while (time.time() - start_time) < total_timeout:
                    # 单次读取（受read_timeout限制）
                    chunk = self.conn.read(256)
                    if chunk:
                        response.extend(chunk)
                        # 协议完整性检查（示例：MODBUS RTU）
                        if self._is_valid_response(response):
                            log.info(f"Received: {bytes_to_spaced_hex(response)}")
                            return bytes(response)

                    # 检查超时
                    if (time.time() - start_time) >= total_timeout:
                        break

                    # 避免忙等待
                    time.sleep(0.01)

                # 超时处理
                if len(response) >= min_response_len:
                    log.warning(
                        f"Incomplete response ({len(response)} bytes): {bytes_to_spaced_hex(response)}"
                    )
                else:
                    log.error(f"No valid response within {total_timeout}s")

            except serial.SerialTimeoutException:
                log.error(f"Write timeout after {write_timeout}s")
            except Exception as e:
                log.error(f"Attempt {attempt} failed: {type(e).__name__}: {str(e)}")

            # 非最后一次尝试时延迟重试
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))  # 指数退避

        # 恢复原始超时设置
        self.conn.timeout = original_timeout
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
