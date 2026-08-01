"""DLT645 异步服务端业务服务。"""

from ...service.serversvc.server_service import MeterServerService
from ...model.types.dlt645_type import ADDRESS_LEN, CtrlCode, ErrorCode, PasswordManager
from ...model.validators import validate_device
from ...protocol.protocol import DLT645Protocol
from ...transport.server.async_rtu_server import AsyncRtuServer
from ...transport.server.async_tcp_server import AsyncTcpServer


class AsyncMeterServerService(MeterServerService):
    """复用现有命令处理逻辑、使用异步传输层的电表服务。"""

    def __init__(self, server):
        # 避免沿用同步类构造函数中的可变默认参数，同时不修改同步实现。
        super().__init__(
            server,
            address=bytearray([0x00] * 6),
            password_manager=PasswordManager(),
        )

    def handle_request(self, frame):
        """处理请求，并修正异步写地址路径中的字节地址赋值。"""
        if frame.ctrl_code != CtrlCode.WriteAddress:
            return super().handle_request(frame)
        if not validate_device(self.address, frame.ctrl_code, frame.addr):
            return self._build_error_response(frame, ErrorCode.OtherError)
        if len(frame.data) < ADDRESS_LEN:
            return self._build_error_response(frame, ErrorCode.RequestDataEmpty)
        self.address = bytearray(frame.data[:ADDRESS_LEN])
        return DLT645Protocol.build_frame(
            bytes(self.address), frame.ctrl_code | 0x80, b""
        )

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

    async def __aenter__(self):
        if not await self.start():
            raise OSError("无法启动异步 DLT645 服务端")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
