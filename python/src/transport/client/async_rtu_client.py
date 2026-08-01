"""基于 pySerial-asyncio 的 DLT645 RTU 客户端。"""

import asyncio
from typing import Any, Optional

import serial

from ...common.message_capture import MessageCapture
from ...common.transform import bytes_to_spaced_hex
from ...protocol.protocol import DLT645Protocol
from ...transport.client.log import log


class AsyncRtuClient:
    """异步串口客户端；同一串口的请求严格串行。"""

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
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[Any] = None
        self._connection_lock = asyncio.Lock()
        self._request_lock = asyncio.Lock()
        self._read_buffer = bytearray()
        self._message_capture: Optional[MessageCapture] = None

    async def connect(self) -> bool:
        async with self._connection_lock:
            if self.writer is not None and not self.writer.is_closing():
                return True
            try:
                try:
                    import serial_asyncio
                except ImportError as exc:
                    raise RuntimeError(
                        "异步 RTU 需要安装可选依赖：pip install 'dlt645[async]'"
                    ) from exc

                self.reader, self.writer = await asyncio.wait_for(
                    serial_asyncio.open_serial_connection(
                        url=self.port,
                        baudrate=self.baud_rate,
                        bytesize=self.data_bits,
                        stopbits=self.stop_bits,
                        parity=self.parity,
                    ),
                    self.timeout,
                )
                self._read_buffer.clear()
                log.info(f"异步 RTU 客户端已连接 {self.port}")
                return True
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.reader = None
                self.writer = None
                log.error(f"异步 RTU 客户端连接失败: {exc}")
                return False

    async def disconnect(self) -> bool:
        async with self._connection_lock:
            writer, self.writer = self.writer, None
            self.reader = None
            self._read_buffer.clear()
            if writer is None:
                return True
            try:
                writer.close()
                wait_closed = getattr(writer, "wait_closed", None)
                if wait_closed is not None:
                    await wait_closed()
                log.info(f"异步 RTU 客户端已断开 {self.port}")
                return True
            except OSError as exc:
                log.error(f"关闭异步 RTU 连接失败: {exc}")
                return False

    async def _ensure_connection(self) -> bool:
        if self.writer is None or self.reader is None or self.writer.is_closing():
            return await self.connect()
        return True

    def _clear_input_buffer(self) -> None:
        """清除 pySerial 底层输入缓冲区（连接存在时）。"""
        self._read_buffer.clear()
        if self.writer is None:
            return
        transport = getattr(self.writer, "transport", None)
        serial_port = getattr(transport, "serial", None)
        if serial_port is not None:
            serial_port.reset_input_buffer()

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

    async def send_request(self, data: bytes, retries: int = 1) -> Optional[bytes]:
        async with self._request_lock:
            for attempt in range(retries + 1):
                if not await self._ensure_connection():
                    if attempt < retries:
                        await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                current_tx_id: Optional[str] = None
                try:
                    assert self.reader is not None
                    assert self.writer is not None
                    self._clear_input_buffer()
                    self.writer.write(data)
                    await asyncio.wait_for(self.writer.drain(), self.timeout)
                    log.info(f"TX: {bytes_to_spaced_hex(data)}")
                    if self._message_capture:
                        current_tx_id = self._message_capture.capture_tx(data)

                    while True:
                        response = self._take_complete_frame()
                        if response is not None:
                            log.info(f"RX: {bytes_to_spaced_hex(response)}")
                            if self._message_capture:
                                self._message_capture.capture_rx(
                                    response, current_tx_id
                                )
                            return response
                        chunk = await asyncio.wait_for(
                            self.reader.read(256), self.timeout
                        )
                        if not chunk:
                            raise ConnectionError("串口流已关闭")
                        self._read_buffer.extend(chunk)
                        if len(self._read_buffer) > 4096:
                            log.warning("异步 RTU 接收缓冲区溢出，已清空")
                            self._read_buffer.clear()
                except asyncio.CancelledError:
                    raise
                except (OSError, ConnectionError, asyncio.TimeoutError) as exc:
                    log.error(f"异步 RTU 请求失败: {exc}")
                except Exception as exc:
                    log.error(f"异步 RTU 请求处理失败: {exc}")

                if attempt < retries:
                    await asyncio.sleep(0.5 * (attempt + 1))
            return None

    async def send_only(self, data: bytes) -> bool:
        async with self._request_lock:
            if not await self._ensure_connection():
                return False
            try:
                assert self.writer is not None
                self._clear_input_buffer()
                self.writer.write(data)
                await asyncio.wait_for(self.writer.drain(), self.timeout)
                log.info(f"TX (no response expected): {bytes_to_spaced_hex(data)}")
                if self._message_capture:
                    self._message_capture.capture_tx(data)
                return True
            except asyncio.CancelledError:
                raise
            except (OSError, asyncio.TimeoutError) as exc:
                log.error(f"异步 RTU 只发送失败: {exc}")
                return False

    async def __aenter__(self):
        if not await self.connect():
            raise ConnectionError(f"无法打开串口 {self.port}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
