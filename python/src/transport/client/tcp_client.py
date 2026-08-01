"""同步 DL/T 645 TCP 客户端。"""

import socket
import threading
import time
from typing import Any, Optional

from ...common.message_capture import MessageCapture
from ...common.transform import bytes_to_spaced_hex
from ...protocol.protocol import DLT645Protocol
from ...transport.client.log import log


class TcpClient:
    """支持分片响应、总超时和串行请求的 TCP 客户端。"""

    MAX_BUFFER_SIZE = 4096

    def __init__(self, ip: str = "", port: int = 0, timeout: float = 5.0) -> None:
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.conn: Optional[socket.socket] = None
        self._request_lock = threading.Lock()
        self._read_buffer = bytearray()
        self._message_capture: Optional[MessageCapture] = None

    def connect(self) -> bool:
        """建立连接；已有有效连接时直接复用。"""
        if self.conn is not None and self.conn.fileno() >= 0:
            return True
        candidate: Optional[socket.socket] = None
        try:
            candidate = socket.create_connection((self.ip, self.port), self.timeout)
            candidate.settimeout(self.timeout)
            self.conn = candidate
            self._read_buffer.clear()
            log.info(f"Connected to {self.ip}:{self.port}")
            return True
        except OSError as exc:
            if candidate is not None:
                candidate.close()
            self.conn = None
            log.error(f"Failed to connect to {self.ip}:{self.port}: {exc}")
            return False

    def disconnect(self) -> bool:
        """关闭连接；重复调用是幂等的。"""
        conn, self.conn = self.conn, None
        self._read_buffer.clear()
        if conn is None:
            return True
        try:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            conn.close()
            return True
        except OSError as exc:
            log.error(f"Failed to close TCP connection: {exc}")
            return False

    def _ensure_connection(self) -> bool:
        conn = self.conn
        if conn is None or conn.fileno() < 0:
            return self.connect()
        try:
            if conn.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR) != 0:
                raise OSError("socket has a pending error")
            return True
        except OSError:
            self.disconnect()
            return self.connect()

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

    def send_request(
        self,
        data: bytes,
        write_timeout: Optional[float] = None,
        read_timeout: Optional[float] = None,
        total_timeout: Optional[float] = None,
        min_response_len: int = 1,
        retries: int = 1,
    ) -> Optional[bytes]:
        """发送请求并返回一个经过校验的完整响应帧。"""
        effective_write_timeout = self.timeout if write_timeout is None else write_timeout
        effective_read_timeout = self.timeout if read_timeout is None else read_timeout
        effective_total_timeout = self.timeout if total_timeout is None else total_timeout
        if min(
            effective_write_timeout,
            effective_read_timeout,
            effective_total_timeout,
        ) <= 0:
            raise ValueError("timeout must be greater than zero")
        if retries < 0:
            raise ValueError("retries cannot be negative")
        with self._request_lock:
            for attempt in range(retries + 1):
                if not self._ensure_connection():
                    if attempt < retries:
                        time.sleep(0.5 * (attempt + 1))
                    continue

                conn = self.conn
                assert conn is not None
                original_timeout = conn.gettimeout()
                tx_id: Optional[str] = None
                self._read_buffer.clear()
                try:
                    conn.settimeout(effective_write_timeout)
                    conn.sendall(data)
                    log.info(f"TX: {bytes_to_spaced_hex(data)}")
                    if self._message_capture:
                        tx_id = self._message_capture.capture_tx(data)

                    deadline = time.monotonic() + effective_total_timeout
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
                        conn.settimeout(min(effective_read_timeout, remaining_time))
                        try:
                            chunk = conn.recv(1024)
                        except socket.timeout:
                            continue
                        if not chunk:
                            raise ConnectionError("server closed the connection")
                        self._read_buffer.extend(chunk)
                        if len(self._read_buffer) > self.MAX_BUFFER_SIZE:
                            raise ValueError("TCP receive buffer exceeded 4096 bytes")

                    if len(self._read_buffer) >= min_response_len:
                        log.warning("TCP response timed out with an incomplete frame")
                    else:
                        log.error(
                            f"No valid response within {effective_total_timeout}s"
                        )
                except (ConnectionError, OSError, ValueError) as exc:
                    log.error(f"TCP request attempt {attempt + 1} failed: {exc}")
                    self.disconnect()
                finally:
                    if self.conn is conn:
                        conn.settimeout(original_timeout)

                if attempt < retries:
                    time.sleep(0.5 * (attempt + 1))
            return None

    def send_only(self, data: bytes, timeout: float = 2.0) -> bool:
        """只发送数据，不等待响应。"""
        with self._request_lock:
            if not self._ensure_connection():
                return False
            conn = self.conn
            assert conn is not None
            original_timeout = conn.gettimeout()
            try:
                conn.settimeout(timeout)
                conn.sendall(data)
                log.info(f"TX (no response expected): {bytes_to_spaced_hex(data)}")
                if self._message_capture:
                    self._message_capture.capture_tx(data)
                return True
            except OSError as exc:
                log.error(f"TCP send failed: {exc}")
                self.disconnect()
                return False
            finally:
                if self.conn is conn:
                    conn.settimeout(original_timeout)

    def __enter__(self) -> "TcpClient":
        if not self.connect():
            raise ConnectionError(f"无法连接 {self.ip}:{self.port}")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.disconnect()
