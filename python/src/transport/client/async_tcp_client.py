"""基于 :mod:`asyncio` 的 DLT645 TCP 客户端。"""

import asyncio
from typing import Any, Optional

from ...common.message_capture import MessageCapture
from ...common.transform import bytes_to_spaced_hex
from ...protocol.protocol import DLT645Protocol
from ...transport.client.log import log


class AsyncTcpClient:
    """异步 TCP 客户端。

    同一条 DLT645 连接上的请求使用锁串行执行，防止并发请求的响应
    相互串线。不同客户端实例之间不共享锁。
    """

    def __init__(self, ip: str = "", port: int = 0, timeout: float = 5.0):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._connection_lock = asyncio.Lock()
        self._request_lock = asyncio.Lock()
        self._read_buffer = bytearray()
        self._message_capture: Optional[MessageCapture] = None

    async def connect(self) -> bool:
        """连接服务器。重复调用时复用有效连接。"""
        async with self._connection_lock:
            if self.writer is not None and not self.writer.is_closing():
                return True
            try:
                self.reader, self.writer = await asyncio.wait_for(
                    asyncio.open_connection(self.ip, self.port), self.timeout
                )
                self._read_buffer.clear()
                log.info(f"异步 TCP 客户端已连接 {self.ip}:{self.port}")
                return True
            except (OSError, asyncio.TimeoutError) as exc:
                self.reader = None
                self.writer = None
                log.error(f"异步 TCP 客户端连接失败: {exc}")
                return False

    async def disconnect(self) -> bool:
        """关闭连接；该操作是幂等的。"""
        async with self._connection_lock:
            writer, self.writer = self.writer, None
            self.reader = None
            self._read_buffer.clear()
            if writer is None:
                return True
            try:
                writer.close()
                await writer.wait_closed()
                log.info("异步 TCP 客户端连接已关闭")
                return True
            except OSError as exc:
                transport = getattr(writer, "transport", None)
                if transport is not None:
                    transport.abort()
                await asyncio.sleep(0)
                log.error(f"关闭异步 TCP 连接失败: {exc}")
                return False

    async def _ensure_connection(self) -> bool:
        if self.writer is None or self.writer.is_closing() or self.reader is None:
            return await self.connect()
        return True

    def _take_complete_frame(self) -> Optional[bytes]:
        """从持久缓冲区取出一帧，保留后续粘连的数据。"""
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

    async def send_request(
        self,
        data: bytes,
        write_timeout: Optional[float] = None,
        read_timeout: Optional[float] = None,
        total_timeout: Optional[float] = None,
        min_response_len: int = 1,
        retries: int = 1,
    ) -> Optional[bytes]:
        """发送请求并异步等待一个完整响应帧。"""
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
        async with self._request_lock:
            for attempt in range(retries + 1):
                if not await self._ensure_connection():
                    if attempt < retries:
                        await asyncio.sleep(0.5 * (attempt + 1))
                    continue

                current_tx_id: Optional[str] = None
                try:
                    assert self.writer is not None
                    assert self.reader is not None
                    self.writer.write(data)
                    await asyncio.wait_for(
                        self.writer.drain(), effective_write_timeout
                    )
                    log.info(f"TX: {bytes_to_spaced_hex(data)}")
                    if self._message_capture:
                        current_tx_id = self._message_capture.capture_tx(data)

                    loop = asyncio.get_running_loop()
                    deadline = loop.time() + effective_total_timeout
                    while True:
                        response = self._take_complete_frame()
                        if response is not None:
                            log.info(f"RX: {bytes_to_spaced_hex(response)}")
                            if self._message_capture:
                                self._message_capture.capture_rx(
                                    response, current_tx_id
                                )
                            return response

                        remaining_time = deadline - loop.time()
                        if remaining_time <= 0:
                            break
                        try:
                            chunk = await asyncio.wait_for(
                                self.reader.read(1024),
                                min(effective_read_timeout, remaining_time),
                            )
                        except asyncio.TimeoutError:
                            # 单次读取超时不等于整个请求超时，继续等到总期限。
                            continue
                        if not chunk:
                            raise ConnectionError("服务端已关闭连接")
                        self._read_buffer.extend(chunk)
                        if len(self._read_buffer) > 4096:
                            log.warning("异步 TCP 接收缓冲区溢出，已清空")
                            self._read_buffer.clear()

                    if len(self._read_buffer) >= min_response_len:
                        log.warning("异步 TCP 响应不完整")
                    else:
                        log.error(
                            f"异步 TCP 请求在 {effective_total_timeout}s 内无响应"
                        )
                except asyncio.CancelledError:
                    raise
                except (OSError, ConnectionError, asyncio.TimeoutError) as exc:
                    log.error(f"异步 TCP 请求失败: {exc}")
                    await self.disconnect()
                except Exception as exc:
                    log.error(f"异步 TCP 请求解析失败: {exc}")

                if attempt < retries:
                    await asyncio.sleep(0.5 * (attempt + 1))
            return None

    async def send_only(self, data: bytes, timeout: float = 2.0) -> bool:
        """只发送数据，不等待响应。"""
        async with self._request_lock:
            if not await self._ensure_connection():
                return False
            try:
                assert self.writer is not None
                self.writer.write(data)
                await asyncio.wait_for(self.writer.drain(), timeout)
                log.info(f"TX (no response expected): {bytes_to_spaced_hex(data)}")
                if self._message_capture:
                    self._message_capture.capture_tx(data)
                return True
            except asyncio.CancelledError:
                raise
            except (OSError, asyncio.TimeoutError) as exc:
                log.error(f"异步 TCP 只发送失败: {exc}")
                await self.disconnect()
                return False

    async def __aenter__(self) -> "AsyncTcpClient":
        if not await self.connect():
            raise ConnectionError(f"无法连接 {self.ip}:{self.port}")
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.disconnect()
