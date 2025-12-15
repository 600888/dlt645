from typing import Optional, Any
import serial
import threading
import time

from ...common.transform import bytes_to_spaced_hex
from ...protocol.protocol import DLT645Protocol
from ...transport.server.log import log


class RtuServer:
    def __init__(
        self,
        port: str,
        data_bits: int = 8,
        stop_bits: int = 1,
        baud_rate: int = 9600,
        parity: str = serial.PARITY_NONE,
        timeout: float = 5.0,
        service=None,
    ):
        self.port = port
        self.data_bits = data_bits
        self.stop_bits = stop_bits
        self.baud_rate = baud_rate
        self.parity = parity
        self.timeout = timeout
        self.service = service
        self.conn: Optional[serial.Serial] = None
        self._server_thread = None
        self._running = False
        self._stop_event = threading.Event()

    def start(self) -> bool:
        """启动RTU服务器（非阻塞，在后台线程中运行）"""
        if self._running:
            log.warning("RTU server is already running")
            return True

        self._stop_event.clear()
        self._running = True

        # 在后台线程中启动服务器
        self._server_thread = threading.Thread(target=self._run_server, daemon=True)
        self._server_thread.start()

        # 等待服务器启动完成
        time.sleep(0.1)
        log.info(
            f"RTU server starting in background on {self.port}, baud_rate={self.baud_rate}, data_bits={self.data_bits}, stop_bits={self.stop_bits}, parity={self.parity}, timeout={self.timeout}"
        )
        return True

    def _run_server(self):
        """服务器主循环（在后台线程中运行）"""
        try:
            self.conn = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                bytesize=self.data_bits,
                stopbits=self.stop_bits,
                parity=self.parity,
                timeout=self.timeout,
            )

            log.info(f"RTU server started on port {self.port}")

            # 启动连接处理循环
            self.handle_connection(self.conn)

        except Exception as e:
            log.error(f"Failed to open serial port: {e}")
        finally:
            self._running = False
            if self.conn:
                try:
                    self.conn.close()
                    self.conn = None
                except:
                    pass
            log.info("RTU server stopped")

    def stop(self) -> bool:
        """停止RTU服务器"""
        if not self._running:
            log.warning("RTU server is not running")
            return True

        log.info("Shutting down RTU server...")

        # 设置停止信号
        self._stop_event.set()

        # 关闭串口连接
        if self.conn is not None:
            try:
                self.conn.close()
                self.conn = None
            except Exception as e:
                log.error(f"Error closing serial connection: {e}")

        # 等待服务器线程结束
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=5.0)
            if self._server_thread.is_alive():
                log.warning("Server thread did not stop gracefully")

        self._running = False
        log.info("RTU server shutdown complete")
        return True

    def is_running(self) -> bool:
        """检查服务器是否正在运行"""
        return self._running

    def _check_timeout(self, last_data_time: float) -> bool:
        """检查是否超时"""
        current_time = time.time()
        if current_time - last_data_time > self.timeout:
            log.error(
                f"Buffer timeout: clearing {len(data_buffer)} bytes of incomplete data: {bytes_to_spaced_hex(data_buffer)}"
            )
            return True
        return False

    def handle_connection(self, conn: Any) -> None:
        if not isinstance(conn, serial.Serial):
            log.error(f"Invalid connection type: {type(conn)}")
            return

        log.debug(
            f"Starting to handle connection on {self.port} - Baud rate: {conn.baudrate}, Data bits: {conn.bytesize}, "
            f"Stop bits: {conn.stopbits}, Parity: {conn.parity}, Timeout: {conn.timeout}"
        )

        # 初始化数据缓冲区，用于累积接收的数据
        data_buffer = bytearray()
        # 记录最后一次收到数据的时间
        last_data_time = time.time()

        try:
            # 确保串口已经打开
            if not conn.is_open:
                log.error("Serial port is not open")
                return

            log.info("Waiting for data...")
            while not self._stop_event.is_set():
                # 检查串口是否仍然打开
                if not conn.is_open:
                    log.error("Serial port was closed unexpectedly")
                    break

                # 使用较短的超时，以便定期检查停止信号
                try:
                    # 检查缓冲区超时 - 如果缓冲区有数据但超过timeout时间没有收到新数据，清空缓冲区
                    if len(data_buffer) > 0 and self._check_timeout(last_data_time):
                        data_buffer = bytearray()
                        continue

                    # 先检查是否有数据可读
                    if conn.in_waiting > 0:
                        # 读取所有可用数据
                        data = conn.read(conn.in_waiting)

                        # 将新接收的数据添加到缓冲区
                        data_buffer.extend(data)
                        log.info(f"RX: {bytes_to_spaced_hex(data)} ({len(data)} bytes)")
                        # 更新最后收到数据的时间
                        last_data_time = time.time()

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
                                    f"Successfully parsed frame, remaining buffer size: {len(data_buffer)}"
                                )

                                # 业务处理
                                try:
                                    resp = self.service.handle_request(frame)

                                    # 响应
                                    if resp is not None:
                                        try:
                                            bytes_written = conn.write(resp)
                                            log.info(
                                                f"TX: {bytes_to_spaced_hex(resp)} ({bytes_written} bytes)"
                                            )
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
                    else:
                        # 没有数据可读，短暂等待以避免CPU占用过高
                        time.sleep(0.01)

                except Exception as read_error:
                    log.error(f"Error reading from serial port: {read_error}")
                    # 短暂暂停后继续尝试
                    time.sleep(0.1)

        except Exception as e:
            if not self._stop_event.is_set():
                log.error(f"Connection handling error: {e}")
        finally:
            try:
                if conn and conn.is_open:
                    conn.close()
                    log.info("Serial connection closed")
            except Exception as e:
                log.error(f"Error closing connection: {e}")
