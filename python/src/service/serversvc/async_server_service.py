"""DLT645 异步服务端业务服务。"""

from typing import Any

from ...service.serversvc.server_service import MeterServerService
from ...transport.server.async_rtu_server import AsyncRtuServer
from ...transport.server.async_tcp_server import AsyncTcpServer


class AsyncMeterServerService(MeterServerService):
    """复用现有命令处理逻辑、使用异步传输层的电表服务。"""

    def __init__(self, server: Any) -> None:
        super().__init__(server)

    @classmethod
    def new_tcp_server(
        cls, ip: str, port: int, timeout: float = 5.0
    ) -> "AsyncMeterServerService":
        return cls.new_meter_server_service(
            AsyncTcpServer(ip=ip, port=port, timeout=timeout)
        )

    @classmethod
    def new_rtu_server(
        cls,
        port: str,
        data_bits: int = 8,
        stop_bits: int = 1,
        baud_rate: int = 9600,
        parity: str = "N",
        timeout: float = 5.0,
    ) -> "AsyncMeterServerService":
        return cls.new_meter_server_service(
            AsyncRtuServer(
                port=port,
                data_bits=data_bits,
                stop_bits=stop_bits,
                baud_rate=baud_rate,
                parity=parity,
                timeout=timeout,
            )
        )

    @classmethod
    def new_meter_server_service(cls, server) -> "AsyncMeterServerService":
        service = cls(server)
        server.service = service
        return service

    async def start(self) -> bool:
        return await self.server.start()

    async def stop(self) -> bool:
        return await self.server.stop()

    close = stop

    async def __aenter__(self) -> "AsyncMeterServerService":
        if not await self.start():
            raise OSError("无法启动异步 DLT645 服务端")
        return self

    async def __aexit__(
        self, exc_type: Any, exc_val: Any, exc_tb: Any
    ) -> None:
        await self.stop()
