"""
DLT645 客户端服务模块。

本模块实现了 DLT645 协议的客户端业务服务功能，包括：
- 电能数据读取
- 需量数据读取
- 变量数据读取
- 事件记录读取
- 参变量读写
- 通讯地址读写
- 密码管理
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import time
import struct
from typing import Optional, Union

from ...common.transform import (
    bcd_to_float,
    bcd_to_time,
    bcd_to_string,
    bytes_to_int,
    bytes_to_spaced_hex,
    string_to_bcd,
)
from ...model.validators import validate_device
from ...model.types.data_type import DataFormat, DataItem
from ...model.types.dlt645_type import (
    DI_LEN,
    ADDRESS_LEN,
    PASSWORD_LEN,
    CtrlCode,
    Demand,
    EventRecord,
    PasswordManager,
    ErrorCode,
    get_error_msg,
)
from ...protocol.protocol import DLT645Protocol
from ...protocol.frame import Frame
from ...model.data import data_handler as data
from ...service.clientsvc.log import log
from ...transport.client.rtu_client import RtuClient
from ...transport.client.tcp_client import TcpClient


class MeterClientService:
    """
    电表客户端服务类。

    用于与 DLT645 电表设备进行通信，提供数据读写等业务功能。

    :ivar address: 设备地址（6字节）。
    :ivar password_manager: 密码管理器。
    :ivar operation_code: 操作码（4字节）。
    :ivar client: 通信客户端（TCP 或 RTU）。
    """

    def __init__(self, client: Union[TcpClient, RtuClient]):
        """
        初始化电表客户端服务。

        :param client: 通信客户端实例（TcpClient 或 RtuClient）。
        :type client: Union[TcpClient, RtuClient]
        """
        self.address = bytearray(6)  # 6字节地址
        self.password_manager: PasswordManager = PasswordManager()  # 4字节密码
        self.operation_code = bytearray(4)  # 4字节操作码
        self.client = client
        self._executor = ThreadPoolExecutor(max_workers=1)  # 用于超时控制

    @classmethod
    def new_tcp_client(
        cls, ip: str, port: int, timeout: float = 30.0
    ) -> Optional["MeterClientService"]:
        """创建TCP客户端"""
        tcp_client = TcpClient(ip=ip, port=port, timeout=timeout)

        # 创建业务服务实例
        return cls.new_meter_client_service(tcp_client)

    @classmethod
    def new_rtu_client(
        cls,
        port: str,
        baudrate: int,
        databits: int,
        stopbits: int,
        parity: str,
        timeout: float,
    ) -> Optional["MeterClientService"]:
        """创建RTU客户端"""
        rtu_client = RtuClient(
            port=port,
            baud_rate=baudrate,
            data_bits=databits,
            stop_bits=stopbits,
            parity=parity,
            timeout=timeout,
        )

        # 创建业务服务实例
        return cls.new_meter_client_service(rtu_client)

    @classmethod
    def new_meter_client_service(
        cls, client: Union[TcpClient, RtuClient]
    ) -> Optional["MeterClientService"]:
        """创建新的MeterService实例"""
        service = cls(client)
        return service

    def get_time(self, t: bytes) -> datetime:
        """从字节数据获取时间"""
        timestamp = bytes_to_int(t)
        log.debug(f"timestamp: {timestamp}")
        return datetime.fromtimestamp(timestamp)

    def set_address(self, address: str) -> bool:
        """设置设备地址"""
        address = string_to_bcd(address)
        if len(address) != ADDRESS_LEN:
            log.error("无效的地址长度")
            return False

        self.address = address
        log.info(f"设置客户端通讯地址: {bytes_to_spaced_hex(self.address)}")
        return True

    def set_password(self, password: str) -> bool:
        """设置设备密码, 修改数据的命令会带上密码发送出去"""
        password = string_to_bcd(password)
        self.password_manager.set_password(password)
        log.info(f"设置客户端密码: {bytes_to_spaced_hex(password)}")
        return True

    def change_password(self, old_password: str, new_password: str) -> bool:
        """修改设备密码"""
        old_password = string_to_bcd(old_password)
        new_password = string_to_bcd(new_password)
        if not self.password_manager.is_password_valid(old_password):
            return False
        if not self.password_manager.is_password_valid(new_password):
            return False

        new_level = new_password[0]
        di = 0x40000C00 | new_level  # 新密码的DI
        write_data = old_password + new_password
        data_bytes = struct.pack("<I", di) + write_data  # 小端序
        frame_bytes = DLT645Protocol.build_frame(
            self.address, CtrlCode.ChangePassword, data_bytes
        )
        return self.send_and_handle_request(frame_bytes)

    def read_00(self, di: int) -> Optional[DataItem]:
        """读取电能"""
        data_bytes = struct.pack("<I", di)  # 小端序
        frame_bytes = DLT645Protocol.build_frame(
            self.address, CtrlCode.ReadData, data_bytes
        )
        return self.send_and_handle_request(frame_bytes)

    def read_01(self, di: int) -> Optional[DataItem]:
        """读取最大需量及发生时间"""
        data_bytes = struct.pack("<I", di)  # 小端序
        frame_bytes = DLT645Protocol.build_frame(
            self.address, CtrlCode.ReadData, data_bytes
        )
        return self.send_and_handle_request(frame_bytes)

    def read_02(self, di: int) -> Optional[DataItem]:
        """读取变量"""
        data_bytes = struct.pack("<I", di)  # 小端序
        frame_bytes = DLT645Protocol.build_frame(
            self.address, CtrlCode.ReadData, data_bytes
        )
        return self.send_and_handle_request(frame_bytes)

    def read_03(self, di: int) -> Optional[DataItem]:
        """读取事件记录"""
        data_bytes = struct.pack("<I", di)  # 小端序
        frame_bytes = DLT645Protocol.build_frame(
            self.address, CtrlCode.ReadData, data_bytes
        )
        return self.send_and_handle_request(frame_bytes)

    def read_04(self, di: int) -> Optional[DataItem]:
        """读取参变量"""
        data_bytes = struct.pack("<I", di)  # 小端序
        frame_bytes = DLT645Protocol.build_frame(
            self.address, CtrlCode.ReadData, data_bytes
        )
        return self.send_and_handle_request(frame_bytes)

    def write_04(self, di: int, value: str, password: str) -> Optional[DataItem]:
        """写参变量"""
        # 密码 + 操作码 + 值
        password = string_to_bcd(password)
        write_data = (
            password + self.operation_code + string_to_bcd(value, endian="little")
        )
        data_bytes = struct.pack("<I", di) + write_data  # 小端序
        frame_bytes = DLT645Protocol.build_frame(
            self.address, CtrlCode.WriteData, data_bytes
        )
        return self.send_and_handle_request(frame_bytes)

    def read_address(self) -> Optional[DataItem]:
        """读取通讯地址"""
        # 读取通讯地址需要使用特殊的广播地址0xAAAAAAAAAAAA
        broadcast_address = bytearray([0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA])
        frame_bytes = DLT645Protocol.build_frame(
            broadcast_address, CtrlCode.ReadAddress, None
        )
        return self.send_and_handle_request(frame_bytes)

    def write_address(self, new_address: bytes) -> Optional[DataItem]:
        """写通讯地址"""
        if len(new_address) != ADDRESS_LEN:
            log.error("无效的新地址长度")
            return None

        frame_bytes = DLT645Protocol.build_frame(
            self.address, CtrlCode.WriteAddress, new_address
        )
        return self.send_and_handle_request(frame_bytes)

    def send_and_handle_request(
        self,
        frame_bytes: bytes,
    ) -> Optional[DataItem]:
        """发送请求并处理响应（带超时控制）

        Args:
            frame_bytes: 要发送的帧数据

        Returns:
            DataItem: 成功时返回数据项
            None: 超时或失败时返回
        """
        try:
            if self.client is None:
                log.error("连接未初始化")
                return None

            # 确保连接有效（重用连接，如果断开则重新连接）
            if not self.client._ensure_connection():
                log.error("连接失败")
                return None

            # 请求阶段超时控制
            response = self.client.send_request(frame_bytes)

            if response is None:
                return None

            # 解析阶段
            frame = DLT645Protocol.deserialize(response)
            if frame is None:
                log.error("解析响应失败")
                return None

            # 处理响应
            data_item = self.handle_response(frame)
            return data_item
        except Exception as e:
            log.error(f"未知错误: {str(e)}", exc_info=True)
            return None

    def _is_valid_response(self, frame: Frame) -> bool:
        """验证响应帧是否有效"""
        # 检测异常处理帧 (DLT645协议中，异常响应的控制码次高位为1)
        if (frame.ctrl_code & 0x40) == 0x40:  # 检查次高位
            error_code = frame.data[0] if len(frame.data) > 0 else None
            error_msg = "设备返回异常响应"

            # 如果数据域不为空，尝试解析错误码
            if frame.data:
                error_code = frame.data[0] if len(frame.data) > 0 else None
                # 根据常见的DLT645错误码定义错误信息
                if any(error_code == ec for ec in ErrorCode):
                    error_msg = f"设备返回异常响应: {get_error_msg(error_code)} (错误码: {error_code:02X})"
                else:
                    error_msg = f"设备返回异常响应: 未知错误码"

            log.error(error_msg)
            return False
        return True

    def handle_response(self, frame: Frame) -> Optional[DataItem]:
        """处理响应帧，包括异常帧检测"""
        try:
            if not self._is_valid_response(frame):
                return None

            # 验证设备地址 - 特殊控制码不需要验证
            if not validate_device(self.address, frame.ctrl_code, frame.addr):
                log.warning(f"验证设备地址: {bytes_to_spaced_hex(frame.addr)} 失败")
                return None

            # 根据控制码判断响应类型
            if frame.ctrl_code == (CtrlCode.BroadcastTimeSync | 0x80):  # 广播校时响应
                log.debug(f"广播校时响应: {bytes_to_spaced_hex(frame.data)}")
                time_value = self.get_time(frame.data[0:4])
                data_item = data.get_data_item(bytes_to_int(frame.data[0:4]))
                if not data_item:
                    log.warning("获取数据项失败")
                    return None
                data_item.value = time_value
                return data_item

            elif frame.ctrl_code == (CtrlCode.ReadData | 0x80):  # 读数据响应
                # 解析数据标识
                if len(frame.data) < DI_LEN:
                    log.warning("读数据响应数据长度无效")
                    return None

                di = frame.data[0:DI_LEN]
                di3 = di[3]

                if di3 == 0x00:  # 读取电能响应
                    log.debug(f"读取电能响应: {bytes_to_spaced_hex(frame.data)}")
                    data_item = data.get_data_item(bytes_to_int(di))
                    if not data_item:
                        log.error("获取电能数据项失败")
                        return None
                    data_item.value = bcd_to_float(
                        frame.data[4:8], data_item.data_format, "little"
                    )
                    return data_item

                elif di3 == 0x01:  # 读取最大需量及发生时间响应
                    log.debug(
                        f"读取最大需量及发生时间响应: {bytes_to_spaced_hex(frame.data)}"
                    )
                    data_item = data.get_data_item(bytes_to_int(di))
                    if not data_item:
                        log.error("获取最大需量数据项失败")
                        return None

                    # 转换时间
                    occur_time = bcd_to_time(frame.data[7:12])

                    # 转换需量值
                    demand_value = bcd_to_float(
                        frame.data[DI_LEN : DI_LEN + 3], data_item.data_format, "little"
                    )

                    data_item.value = Demand(value=demand_value, time=occur_time)
                    return data_item

                elif di3 == 0x02:
                    data_item = data.get_data_item(bytes_to_int(di))
                    if not data_item:
                        log.error("获取变量数据项失败")
                        return None
                    data_item.value = bcd_to_float(
                        frame.data[DI_LEN : DI_LEN + 4], data_item.data_format, "little"
                    )
                    return data_item
                elif di3 == 0x03:
                    log.debug(f"读取事件记录响应: {bytes_to_spaced_hex(frame.data)}")
                    data_item = data.get_data_item(bytes_to_int(di))
                    if not data_item:
                        log.error("获取事件记录数据项失败")
                        return None

                    start_len = DI_LEN
                    for i, item in enumerate(data_item):
                        event_record: EventRecord = item.value
                        if isinstance(event_record.event, tuple):
                            step = len(item.data_format.split(",")[0]) // 2
                            event_list = list(event_record.event)
                            for i, _ in enumerate(event_list):
                                # 提取BCD数据部分
                                bcd_data = frame.data[start_len : start_len + step]
                                start_len += step
                                event_list[i] = bcd_to_string(bcd_data, "little")
                            event_record.event = tuple(reversed(event_list))
                        else:
                            step = len(item.data_format) // 2
                            # 提取BCD数据部分
                            bcd_data = frame.data[start_len : start_len + step]
                            start_len += step
                            item.value = bcd_to_string(bcd_data, "little")
                    return data_item
                elif di3 == 0x04:  # 读参变量响应
                    log.debug(f"读取参变量响应: {bytes_to_spaced_hex(frame.data)}")
                    data_item = data.get_data_item(bytes_to_int(di))
                    if not data_item:
                        log.error("获取参变量数据项失败")
                        return None

                    start_len = DI_LEN
                    # 时段表数据
                    if (
                        0x04010000
                        <= int.from_bytes(di, byteorder="little")
                        <= 0x04020008
                    ):
                        for i, item in enumerate(data_item):
                            step = len(item.data_format) // 2
                            # 提取BCD数据部分
                            bcd_data = frame.data[start_len : start_len + step]
                            start_len += step
                            item.value = bcd_to_string(bcd_data, "little")
                    else:
                        # 提取BCD数据部分
                        bcd_data = frame.data[start_len:]
                        start_len += len(bcd_data)
                        data_item.value = bcd_to_string(bcd_data, "little")
                    return data_item
                else:
                    log.warning(f"未知数据项: {bytes_to_spaced_hex(di)}")
                    return None
            elif frame.ctrl_code == (CtrlCode.WriteData | 0x80):  # 写参变量响应
                log.debug(f"写参变量")
                return None
            elif frame.ctrl_code == (CtrlCode.ReadAddress | 0x80):  # 读通讯地址响应
                log.debug(f"读通讯地址响应: {bytes_to_spaced_hex(frame.data)}")
                if len(frame.data) == ADDRESS_LEN:
                    self.address = frame.data[:ADDRESS_LEN]
                return DataItem(
                    di=bytes_to_int(frame.data[0:DI_LEN]),
                    name="通讯地址",
                    data_format=DataFormat.XXXXXXXX.value,
                    value=bcd_to_string(frame.data),
                    unit="",
                    update_time=datetime.now(),
                )

            elif frame.ctrl_code == (CtrlCode.WriteAddress | 0x80):  # 写通讯地址响应
                log.debug(f"写通讯地址响应: {bytes_to_spaced_hex(frame.data)}")
                return DataItem(
                    di=bytes_to_int(frame.data[0:DI_LEN]),
                    name="通讯地址",
                    data_format=DataFormat.XXXXXXXX.value,
                    value=bcd_to_string(frame.data),
                    unit="",
                    update_time=datetime.now(),
                )
            elif frame.ctrl_code == (CtrlCode.ChangePassword | 0x80):  # 写密码响应
                log.debug(f"写密码响应: {bytes_to_spaced_hex(frame.data)}")
                password = frame.data[:DI_LEN]
                self.password_manager.set_password(password)
            else:
                log.warning(f"Unknown control code: {frame.ctrl_code}")
                return None
        except Exception as e:
            log.error(f"处理响应帧时出错: {e}")
            raise
