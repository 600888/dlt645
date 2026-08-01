"""基于 pySerial-asyncio 的 DLT645 RTU 服务端。"""

import asyncio
import inspect
from typing import Any, Optional

import serial

from ...common.message_capture import MessageCapture
from ...common.transform import bytes_to_spaced_hex
from ...protocol.protocol import DLT645Protocol
from ...transport.server.log import log


class AsyncRtuServer:
    """在单个串口流上依次处理 DLT645 请求。"""

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
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[Any] = None
        self._task: Optional[asyncio.Task[Any]] = None
        self._running = False
        self._message_capture: Optional[MessageCapture] = None

    async def start(self) -> bool:
        if self._running:
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
            self._running = True
            self._task = asyncio.create_task(
                self._run(), name=f"dlt645-rtu-server-{self.port}"
            )
            log.info(f"异步 RTU 服务端已启动 {self.port}")
            return True
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.reader = None
            self.writer = None
            log.error(f"异步 RTU 服务端启动失败: {exc}")
            return False

    async def stop(self) -> bool:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        writer, self.writer = self.writer, None
        self.reader = None
        if writer is not None:
            writer.close()
            wait_closed = getattr(writer, "wait_closed", None)
            if wait_closed is not None:
                await asyncio.gather(wait_closed(), return_exceptions=True)
        log.info("异步 RTU 服务端已停止")
        return True

    def is_running(self) -> bool:
        return self._running

    async def _dispatch(self, frame: Any) -> Any:
        if self.service is None:
            raise RuntimeError("异步 RTU 服务端未绑定业务服务")
        response = self.service.handle_request(frame)
        if inspect.isawaitable(response):
            response = await response
        return response

    async def _run(self) -> None:
        assert self.reader is not None
        assert self.writer is not None
        data_buffer = bytearray()
        try:
            while self._running:
                try:
                    chunk = await asyncio.wait_for(self.reader.read(256), self.timeout)
                except asyncio.TimeoutError:
                    if data_buffer:
                        log.warning("异步 RTU 半帧接收超时，已清空缓冲区")
                        data_buffer.clear()
                    continue
                if not chunk:
                    break
                data_buffer.extend(chunk)
                log.info(f"RX: {bytes_to_spaced_hex(chunk)}")
                if len(data_buffer) > 4096:
                    log.warning("异步 RTU 服务端缓冲区溢出，已清空")
                    data_buffer.clear()
                    continue

                while data_buffer:
                    original = bytes(data_buffer)
                    remaining, frame = DLT645Protocol.deserialize_with_remaining(
                        original
                    )
                    if frame is None:
                        if remaining != original:
                            data_buffer = bytearray(remaining)
                            continue
                        break
                    consumed = len(original) - len(remaining)
                    request = original[:consumed]
                    data_buffer = bytearray(remaining)
                    current_tx_id: Optional[str] = None
                    if self._message_capture:
                        current_tx_id = self._message_capture.capture_rx_for_server(
                            request
                        )
                    response = await self._dispatch(frame)
                    if response:
                        self.writer.write(response)
                        await asyncio.wait_for(self.writer.drain(), self.timeout)
                        log.info(f"TX: {bytes_to_spaced_hex(response)}")
                        if self._message_capture:
                            self._message_capture.capture_tx_for_server(
                                response, current_tx_id
                            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if self._running:
                log.error(f"异步 RTU 服务端处理失败: {exc}")
        finally:
            self._running = False

    async def __aenter__(self) -> "AsyncRtuServer":
        if not await self.start():
            raise OSError(f"无法打开串口 {self.port}")
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.stop()
