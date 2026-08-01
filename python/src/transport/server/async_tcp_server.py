"""基于 :mod:`asyncio` 的 DLT645 TCP 服务端。"""

import asyncio
import inspect
from typing import Optional, Set

from ...common.message_capture import MessageCapture
from ...common.transform import bytes_to_spaced_hex
from ...protocol.protocol import DLT645Protocol
from ...transport.server.log import log


class AsyncTcpServer:
    """使用任务而非线程处理 TCP 连接的异步服务端。"""

    def __init__(self, ip: str, port: int, timeout: float, service=None):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.service = service
        self._server: Optional[asyncio.AbstractServer] = None
        self._running = False
        self._client_tasks: Set[asyncio.Task] = set()
        self._writers: Set[asyncio.StreamWriter] = set()
        self._message_capture: Optional[MessageCapture] = None

    async def start(self) -> bool:
        """启动监听；方法返回后端口已经可用。"""
        if self._running:
            return True
        try:
            self._server = await asyncio.start_server(
                self.handle_connection, self.ip, self.port
            )
            self._running = True
            sockets = self._server.sockets or []
            if sockets and self.port == 0:
                self.port = sockets[0].getsockname()[1]
            log.info(f"异步 TCP 服务端已启动 {self.ip}:{self.port}")
            return True
        except OSError as exc:
            log.error(f"异步 TCP 服务端启动失败: {exc}")
            self._server = None
            return False

    async def stop(self) -> bool:
        """停止监听并回收所有连接任务。"""
        self._running = False
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        for writer in list(self._writers):
            writer.close()

        current = asyncio.current_task()
        tasks = [task for task in self._client_tasks if task is not current]
        if tasks:
            _, pending = await asyncio.wait(tasks, timeout=min(self.timeout, 1.0))
            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)

        # 正常情况下连接任务已经完成关闭；兜底终止异常 transport。
        for writer in list(self._writers):
            transport = getattr(writer, "transport", None)
            if transport is not None:
                transport.abort()
        await asyncio.sleep(0)
        self._client_tasks.clear()
        self._writers.clear()
        log.info("异步 TCP 服务端已停止")
        return True

    def is_running(self) -> bool:
        return self._running

    async def _dispatch(self, frame):
        if self.service is None:
            raise RuntimeError("异步 TCP 服务端未绑定业务服务")
        result = self.service.handle_request(frame)
        if inspect.isawaitable(result):
            result = await result
        return result

    async def handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        task = asyncio.current_task()
        if task is not None:
            self._client_tasks.add(task)
        self._writers.add(writer)
        peer = writer.get_extra_info("peername")
        log.info(f"异步 TCP 接入连接: {peer}")
        data_buffer = bytearray()
        try:
            while self._running:
                try:
                    chunk = await asyncio.wait_for(reader.read(1024), self.timeout)
                except asyncio.TimeoutError:
                    if data_buffer:
                        log.warning("异步 TCP 半帧接收超时，已清空缓冲区")
                        data_buffer.clear()
                    continue
                if not chunk:
                    break
                data_buffer.extend(chunk)
                log.info(f"RX: {bytes_to_spaced_hex(chunk)}")
                if len(data_buffer) > 4096:
                    log.warning("异步 TCP 服务端接收缓冲区溢出，已清空")
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
                        writer.write(response)
                        await writer.drain()
                        log.info(f"TX: {bytes_to_spaced_hex(response)}")
                        if self._message_capture:
                            self._message_capture.capture_tx_for_server(
                                response, current_tx_id
                            )
        except asyncio.CancelledError:
            raise
        except (ConnectionError, OSError) as exc:
            log.error(f"异步 TCP 连接异常: {exc}")
        except Exception as exc:
            log.error(f"异步 TCP 处理请求失败: {exc}")
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                transport = getattr(writer, "transport", None)
                if transport is not None:
                    transport.abort()
                await asyncio.sleep(0)
            self._writers.discard(writer)
            if task is not None:
                self._client_tasks.discard(task)
            log.info(f"异步 TCP 连接已关闭: {peer}")

    async def __aenter__(self):
        if not await self.start():
            raise OSError(f"无法监听 {self.ip}:{self.port}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
