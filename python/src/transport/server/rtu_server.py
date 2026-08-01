"""线程式 DL/T 645 串口服务端。"""

import threading
import time
from typing import Any, Optional

import serial

from ...common.message_capture import MessageCapture
from ...common.transform import bytes_to_spaced_hex
from ...protocol.protocol import DLT645Protocol
from ...transport.server.log import log


class RtuServer:
    """在后台线程中读取和处理串口帧。"""

    MAX_BUFFER_SIZE = 4096

    def __init__(
        self,
        port: str,
        data_bits: int = 8,
        stop_bits: int = 1,
        baud_rate: int = 9600,
        parity: str = serial.PARITY_NONE,
        timeout: float = 5.0,
        service: Any = None,
    ) -> None:
        self.port = port
        self.data_bits = data_bits
        self.stop_bits = stop_bits
        self.baud_rate = baud_rate
        self.parity = parity
        self.timeout = timeout
        self.service = service
        self.conn: Optional[serial.SerialBase] = None
        self._server_thread: Optional[threading.Thread] = None
        self._running = False
        self._stop_event = threading.Event()
        self._started_event = threading.Event()
        self._message_capture: Optional[MessageCapture] = None

    def start(self) -> bool:
        if self._running:
            return True
        self._stop_event.clear()
        self._started_event.clear()
        self._server_thread = threading.Thread(
            target=self._run_server,
            name=f"dlt645-rtu-{self.port}",
            daemon=True,
        )
        self._server_thread.start()
        if not self._started_event.wait(timeout=min(max(self.timeout, 1.0), 5.0)):
            self.stop()
            return False
        return self._running

    def _run_server(self) -> None:
        conn: Optional[serial.SerialBase] = None
        try:
            conn = serial.serial_for_url(
                self.port,
                baudrate=self.baud_rate,
                bytesize=self.data_bits,
                stopbits=self.stop_bits,
                parity=self.parity,
                timeout=min(self.timeout, 0.1),
                write_timeout=self.timeout,
            )
            self.conn = conn
            self._running = True
            self._started_event.set()
            log.info(f"RTU server started on {self.port}")
            self.handle_connection(conn)
        except BaseException as exc:
            log.error(f"Failed to open serial port {self.port}: {exc}")
        finally:
            self._running = False
            self._started_event.set()
            self.conn = None
            if conn is not None:
                try:
                    conn.close()
                except (OSError, serial.SerialException):
                    pass

    def stop(self) -> bool:
        self._stop_event.set()
        conn, self.conn = self.conn, None
        if conn is not None:
            try:
                conn.cancel_read()
            except (AttributeError, OSError, serial.SerialException):
                pass
            try:
                conn.close()
            except (OSError, serial.SerialException):
                pass
        if self._server_thread and self._server_thread is not threading.current_thread():
            self._server_thread.join(timeout=5.0)
        self._running = False
        return self._server_thread is None or not self._server_thread.is_alive()

    def is_running(self) -> bool:
        return self._running

    def _dispatch(self, frame: Any) -> Optional[bytes]:
        if self.service is None:
            raise RuntimeError("RTU server is not bound to a service")
        result = self.service.handle_request(frame)
        return None if result is None else bytes(result)

    def handle_connection(self, conn: serial.SerialBase) -> None:
        data_buffer = bytearray()
        last_data_time = time.monotonic()
        while not self._stop_event.is_set() and conn.is_open:
            try:
                chunk = conn.read(max(1, min(conn.in_waiting, 256)))
            except (OSError, serial.SerialException) as exc:
                if not self._stop_event.is_set():
                    log.error(f"RTU read failed: {exc}")
                break

            if chunk:
                data_buffer.extend(chunk)
                last_data_time = time.monotonic()
                log.info(f"RX: {bytes_to_spaced_hex(chunk)}")
                if len(data_buffer) > self.MAX_BUFFER_SIZE:
                    log.warning("RTU receive buffer overflow; buffer cleared")
                    data_buffer.clear()
                    continue
            elif data_buffer and time.monotonic() - last_data_time >= self.timeout:
                log.warning("RTU incomplete frame timed out; buffer cleared")
                data_buffer.clear()
                continue

            while data_buffer:
                original = bytes(data_buffer)
                remaining, frame = DLT645Protocol.deserialize_with_remaining(original)
                if frame is None:
                    if remaining != original:
                        data_buffer = bytearray(remaining)
                        continue
                    break

                consumed = len(original) - len(remaining)
                request = original[:consumed]
                data_buffer = bytearray(remaining)
                pair_id: Optional[str] = None
                if self._message_capture:
                    pair_id = self._message_capture.capture_rx_for_server(request)

                try:
                    response = self._dispatch(frame)
                    if response:
                        written = conn.write(response)
                        conn.flush()
                        if written != len(response):
                            raise OSError(
                                f"incomplete serial write: {written}/{len(response)}"
                            )
                        log.info(f"TX: {bytes_to_spaced_hex(response)}")
                        if self._message_capture:
                            self._message_capture.capture_tx_for_server(
                                response, pair_id
                            )
                except (OSError, serial.SerialException, RuntimeError) as exc:
                    log.error(f"RTU request handling failed: {exc}")

    def __enter__(self) -> "RtuServer":
        if not self.start():
            raise OSError(f"无法打开串口 {self.port}")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()
