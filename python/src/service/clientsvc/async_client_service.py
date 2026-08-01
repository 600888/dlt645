"""DLT645 异步客户端业务服务。"""

import inspect
from datetime import datetime
from typing import Any, Optional, Union

from ...common.transform import bytes_to_spaced_hex, uint8_to_bcd
from ...model.types.data_type import DataFormat, DataItem
from ...model.types.dlt645_type import BroadcastAddr, CtrlCode, PasswordManager
from ...protocol.protocol import DLT645Protocol
from ...service.clientsvc.client_service import MeterClientService
from ...service.clientsvc.log import log
from ...transport.client.async_rtu_client import AsyncRtuClient
from ...transport.client.async_tcp_client import AsyncTcpClient

AsyncClient = Union[AsyncTcpClient, AsyncRtuClient]


class AsyncMeterClientService(MeterClientService):
    """异步电表客户端服务。

    响应解析和本地状态方法继承同步服务；网络方法在本类中显式转换为
    协程。初始化时不创建同步服务使用的线程池。
    """

    def __init__(self, client: AsyncClient):
        self.address = bytearray(6)
        self.password_manager = PasswordManager()
        self.operation_code = bytearray(4)
        self.client = client

    @classmethod
    def new_tcp_client(
        cls, ip: str, port: int, timeout: float = 30.0
    ) -> "AsyncMeterClientService":
        return cls(AsyncTcpClient(ip=ip, port=port, timeout=timeout))

    @classmethod
    def new_rtu_client(
        cls,
        port: str,
        baudrate: int = 9600,
        databits: int = 8,
        stopbits: int = 1,
        parity: str = "N",
        timeout: float = 1.0,
    ) -> "AsyncMeterClientService":
        return cls(
            AsyncRtuClient(
                port=port,
                baud_rate=baudrate,
                data_bits=databits,
                stop_bits=stopbits,
                parity=parity,
                timeout=timeout,
            )
        )

    @classmethod
    def new_meter_client_service(cls, client: AsyncClient) -> "AsyncMeterClientService":
        return cls(client)

    async def connect(self) -> bool:
        return await self.client.connect()

    async def disconnect(self) -> bool:
        return await self.client.disconnect()

    async def _resolve_parent_result(self, result: Any):
        """兼容父类在参数校验失败时直接返回 None/False 的行为。"""
        if inspect.isawaitable(result):
            return await result
        return result

    async def change_password(self, old_password: str, new_password: str):
        return await self._resolve_parent_result(
            super().change_password(old_password, new_password)
        )

    async def read_00(self, di: int) -> Optional[DataItem]:
        return await self._resolve_parent_result(super().read_00(di))

    async def read_01(self, di: int) -> Optional[DataItem]:
        return await self._resolve_parent_result(super().read_01(di))

    async def read_02(self, di: int) -> Optional[DataItem]:
        return await self._resolve_parent_result(super().read_02(di))

    async def read_03(self, di: int) -> Optional[DataItem]:
        return await self._resolve_parent_result(super().read_03(di))

    async def read_04(self, di: int) -> Optional[DataItem]:
        return await self._resolve_parent_result(super().read_04(di))

    async def write_04(self, di: int, value: str, password: str) -> Optional[DataItem]:
        return await self._resolve_parent_result(super().write_04(di, value, password))

    async def read_address(self) -> Optional[DataItem]:
        return await self._resolve_parent_result(super().read_address())

    async def write_address(self, new_address: bytes) -> Optional[DataItem]:
        return await self._resolve_parent_result(super().write_address(new_address))

    async def broadcast_time_sync(self, dt: Optional[datetime] = None) -> bool:
        return bool(await self._resolve_parent_result(super().broadcast_time_sync(dt)))

    async def freeze(
        self,
        month: Optional[int] = None,
        day: Optional[int] = None,
        hour: Optional[int] = None,
        minute: Optional[int] = None,
        broadcast: bool = False,
    ) -> Optional[DataItem]:
        # 父类广播分支会立即判断返回值，无法直接复用异步 _send_broadcast。
        now = datetime.now()
        data = bytearray(
            [
                uint8_to_bcd(now.month if month is None else month),
                uint8_to_bcd(now.day if day is None else day),
                uint8_to_bcd(now.hour if hour is None else hour),
                uint8_to_bcd(now.minute if minute is None else minute),
            ]
        )
        address = BroadcastAddr.TimeSync if broadcast else self.address
        frame_bytes = DLT645Protocol.build_frame(address, CtrlCode.FreezeCmd, data)
        if broadcast:
            log.info(f"异步广播冻结: {bytes_to_spaced_hex(data)}")
            if not await self._send_broadcast(frame_bytes):
                return None
            return DataItem(
                di=0,
                name="广播冻结",
                data_format=DataFormat.YYMMDDhhmm.value,
                value=bytes_to_spaced_hex(data),
                unit="",
                update_time=datetime.now(),
            )
        return await self.send_and_handle_request(frame_bytes)

    async def change_baud_rate(self, baud: int) -> Optional[DataItem]:
        return await self._resolve_parent_result(super().change_baud_rate(baud))

    async def clear_demand(self, di: int, password: str) -> Optional[DataItem]:
        return await self._resolve_parent_result(super().clear_demand(di, password))

    async def clear_meter(self, password: str) -> Optional[DataItem]:
        return await self._resolve_parent_result(super().clear_meter(password))

    async def clear_event(
        self,
        password: str,
        operator_code: str = "00000000",
        di: int = 0xFFFFFFFF,
    ) -> Optional[DataItem]:
        return await self._resolve_parent_result(
            super().clear_event(password, operator_code, di)
        )

    async def _send_broadcast(self, frame_bytes: bytes) -> bool:
        try:
            if self.client is None:
                return False
            if not await self.client._ensure_connection():
                log.error("异步客户端连接失败")
                return False
            return await self.client.send_only(frame_bytes)
        except Exception as exc:
            log.error(f"异步广播发送失败: {exc}")
            return False

    async def send_and_handle_request(self, frame_bytes: bytes) -> Optional[DataItem]:
        try:
            if self.client is None:
                log.error("异步客户端连接未初始化")
                return None
            if not await self.client._ensure_connection():
                log.error("异步客户端连接失败")
                return None
            response = await self.client.send_request(frame_bytes)
            if response is None:
                return None
            frame = DLT645Protocol.deserialize(response)
            if frame is None:
                return None
            return self.handle_response(frame)
        except Exception as exc:
            log.error(f"异步请求处理失败: {exc}")
            return None

    async def __aenter__(self):
        if not await self.connect():
            raise ConnectionError("无法建立异步 DLT645 客户端连接")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
