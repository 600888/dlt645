"""同步 DL/T 645 串口客户端。"""

import threading
import time
from typing import Any, Optional

import serial

from ...common.message_capture import MessageCapture
from ...common.transform import bytes_to_spaced_hex
from ...protocol.protocol import DLT645Protocol
from ...transport.client.log import log


class RtuClient:
    """支持分片读取、总超时与重试的串口客户端。"""

    MAX_BUFFER_SIZE = 4096

    def __init__(
        self,
        port: str = "",
        baud_rate: int = 9600,
        data_bits: int = 8,
        stop_bits: int = 1,
        parity: str = serial.PARITY_NONE,
        timeout: float = 1.0,
    ) -> None:
        self.port = port
        self.baud_rate = baud_rate
        self.data_bits = data_bits
        self.stop_bits = stop_bits
        self.parity = parity
        self.timeout = timeout
        self.conn: Optional[serial.SerialBase] = None
        self._request_lock = threading.Lock()
        self._read_buffer = bytearray()
        self._message_capture: Optional[MessageCapture] = None

    def connect(self) -> bool:
        if self.conn is not None and self.conn.is_open:
            return True
        try:
            self.conn = serial.serial_for_url(
                self.port,
                baudrate=self.baud_rate,
                bytesize=self.data_bits,
                stopbits=self.stop_bits,
                parity=self.parity,
                timeout=self.timeout,
                write_timeout=self.timeout,
            )
            self._read_buffer.clear()
            log.info(f"RTU client connected to {self.port}")
            return True
        except (OSError, serial.SerialException, ValueError) as exc:
            self.conn = None
            log.error(f"Failed to open serial port {self.port}: {exc}")
            return False

    def disconnect(self) -> bool:
        conn, self.conn = self.conn, None
        self._read_buffer.clear()
        if conn is None:
            return True
        try:
            conn.close()
            return True
        except (OSError, serial.SerialException) as exc:
            log.error(f"Failed to close serial port: {exc}")
            return False

    def _ensure_connection(self) -> bool:
        if self.conn is None or not self.conn.is_open:
            return self.connect()
        return True

    def _clear_input_buffer(self) -> None:
        self._read_buffer.clear()
        if self.conn is not None:
            self.conn.reset_input_buffer()

    def _take_complete_frame(self) -> Optional[bytes]:
        while self._read_buffer:
            original = bytes(self._read_buffer)
            remaining, frame = DLT645Protocol.deserialize_with_remaining(original)
            if frame is not None:
                consumed = len(original) - len(remaining)
                response = original[:consumed]
                self._read_buffer = bytearray(remaining)
                return response
            if remaining != original:
                self._read_buffer = bytearray(remaining)
                continue
            return None
        return None

    def send_request(self, data: bytes, retries: int = 1) -> Optional[bytes]:
        with self._request_lock:
            for attempt in range(retries + 1):
                if not self._ensure_connection():
                    if attempt < retries:
                        time.sleep(0.5 * (attempt + 1))
                    continue
                conn = self.conn
                assert conn is not None
                original_timeout = conn.timeout
                tx_id: Optional[str] = None
                try:
                    self._clear_input_buffer()
                    written = conn.write(data)
                    conn.flush()
                    if written != len(data):
                        raise OSError(f"incomplete serial write: {written}/{len(data)}")
                    log.info(f"TX: {bytes_to_spaced_hex(data)}")
                    if self._message_capture:
                        tx_id = self._message_capture.capture_tx(data)

                    deadline = time.monotonic() + self.timeout
                    while True:
                        response = self._take_complete_frame()
                        if response is not None:
                            log.info(f"RX: {bytes_to_spaced_hex(response)}")
                            if self._message_capture:
                                self._message_capture.capture_rx(response, tx_id)
                            return response

                        remaining_time = deadline - time.monotonic()
                        if remaining_time <= 0:
                            break
                        conn.timeout = remaining_time
                        chunk = conn.read(max(1, min(conn.in_waiting, 256)))
                        if chunk:
                            self._read_buffer.extend(chunk)
                            if len(self._read_buffer) > self.MAX_BUFFER_SIZE:
                                raise ValueError(
                                    "RTU receive buffer exceeded 4096 bytes"
                                )
                    log.warning("RTU response timed out or was incomplete")
                except (OSError, serial.SerialException, ValueError) as exc:
                    log.error(f"RTU request attempt {attempt + 1} failed: {exc}")
                finally:
                    if conn is not None and self.conn is conn:
                        setattr(conn, "timeout", original_timeout)

                if attempt < retries:
                    time.sleep(0.5 * (attempt + 1))
            return None

    def send_only(self, data: bytes) -> bool:
        with self._request_lock:
            if not self._ensure_connection():
                return False
            conn = self.conn
            assert conn is not None
            try:
                self._clear_input_buffer()
                written = conn.write(data)
                conn.flush()
                if written != len(data):
                    return False
                log.info(f"TX (no response expected): {bytes_to_spaced_hex(data)}")
                if self._message_capture:
                    self._message_capture.capture_tx(data)
                return True
            except (OSError, serial.SerialException) as exc:
                log.error(f"RTU send failed: {exc}")
                return False

    def __enter__(self) -> "RtuClient":
        if not self.connect():
            raise OSError(f"无法打开串口 {self.port}")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.disconnect()
