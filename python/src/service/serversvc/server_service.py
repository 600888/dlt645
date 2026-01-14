"""
DLT645 服务端服务模块。

本模块实现了 DLT645 协议的服务端业务服务功能，包括：
- 处理客户端数据读取请求
- 处理客户端数据写入请求
- 通讯地址管理
- 密码验证和管理
"""

import struct
from typing import Optional, Union, List

from ...common.transform import (
    bytes_to_spaced_hex,
    float_to_bcd,
    datetime_to_bcd,
    string_to_bcd,
    bcd_to_value,
    bcd_to_string,
)
from ...model.data.data_handler import set_data_item, get_data_item
from ...model.types.data_type import DataItem
from ...model.validators import validate_device
from ...model.types.dlt645_type import (
    DI_LEN,
    PASSWORD_LEN,
    ADDRESS_LEN,
    OPERATOR_CODE_LEN,
    CtrlCode,
    Demand,
    ErrorCode,
    EventRecord,
    PasswordManager,
)
from ...protocol.protocol import DLT645Protocol
from ...model.data import data_handler as data
from ...service.serversvc.log import log
from ...transport.server.rtu_server import RtuServer
from ...transport.server.tcp_server import TcpServer


class MeterServerService:
    """
    电表服务端服务类。

    用于模拟 DLT645 电表设备，响应客户端的数据读写请求。

    :ivar server: 通信服务器（TCP 或 RTU）。
    :ivar address: 设备地址（6字节）。
    :ivar password_manager: 密码管理器。
    :ivar clear_meter_event_records: 电表清零事件记录列表。
    :ivar event_records: 事件记录列表。
    """

    def __init__(
        self,
        server: Union[TcpServer, RtuServer],
        address: Optional[bytearray] = bytearray([0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
        password_manager: Optional[PasswordManager] = PasswordManager(),
    ):
        """
        初始化电表服务端服务。

        :param server: 通信服务器实例（TcpServer 或 RtuServer）。
        :type server: Union[TcpServer, RtuServer]
        :param address: 设备地址，默认为全零。
        :type address: Optional[bytearray]
        :param password_manager: 密码管理器，默认创建新实例。
        :type password_manager: Optional[PasswordManager]
        """
        self.server = server
        self.address = address
        self.password_manager = password_manager
        self.clear_meter_event_records = []  # 记录电表清零事件
        self.event_records = []  # 记录事件

    @classmethod
    def new_tcp_server(
        cls, ip: str, port: int, timeout: float = 5.0
    ) -> "MeterServerService":
        """
        创建 TCP 服务器
        :param ip: IP 地址
        :param port: 端口
        :param timeout: 超时时间
        :return:
        """
        # 1. 先创建 TcpServer
        tcp_server = TcpServer(ip, port, timeout, None)
        # 2. 创建 MeterServerService，注入 TcpServer（作为 Server 接口）
        return cls.new_meter_server_service(tcp_server)

    @classmethod
    def new_rtu_server(
        cls,
        port: str,
        data_bits: int,
        stop_bits: int,
        baud_rate: int,
        parity: str,
        timeout: float,
    ) -> "MeterServerService":
        """
        创建 RTU 服务器
        :param port: 端口
        :param data_bits: 数据位
        :param stop_bits: 停止位
        :param baud_rate: 波特率
        :param parity: 校验位
        :param timeout: 超时时间
        :return:
        """
        # 1. 先创建 RtuServer
        rtu_server = RtuServer(port, data_bits, stop_bits, baud_rate, parity, timeout)
        # 2. 创建 MeterServerService，注入 RtuServer（作为 Server 接口）
        return cls.new_meter_server_service(rtu_server)

    @classmethod
    def new_meter_server_service(
        cls, server: Union[TcpServer, RtuServer]
    ) -> "MeterServerService":
        """
        创建新的MeterServerService实例
        :param server: 服务器实例（TCP或RTU）
        :return: MeterServerService实例
        """
        # 创建业务服务实例
        meter_service = cls(server)
        # 将服务实例注入回服务器
        server.service = meter_service
        return meter_service

    # 设置时间，需根据实际情况实现
    def set_time(self, data_bytes):
        pass

    def set_address(self, address: str):
        """
        写通讯地址
        :param address:
        :return:
        """
        address = string_to_bcd(address)
        if len(address) != ADDRESS_LEN:
            raise ValueError("invalid address length")
        self.address = address

    def set_password(self, password: str) -> None:
        """
        写密码
        :param password:
        :return:
        """
        password = string_to_bcd(password)
        self.password_manager.set_password(password)
        log.info(f"设置密码: {bytes_to_spaced_hex(password)}")

    def set_00(self, di: int, value: float) -> bool:
        """
        写电能量
        :param di: 数据项
        :param value: 值
        :return:
        """
        ok = set_data_item(di, value)
        if not ok:
            log.error(f"写电能量失败")
        return ok

    def set_01(self, di: int, demand: Demand) -> bool:
        """
        写最大需量及发生时间
        :param di: 数据项
        :param demand: 值
        :return:
        """
        ok = set_data_item(di, demand)
        if not ok:
            log.error(f"写最大需量及发生时间失败")
        return ok

    def set_02(self, di: int, value: float) -> bool:
        """
        写变量
        :param di: 数据项
        :param value: 值
        :return:
        """
        data_item = get_data_item(di)
        if data_item is None:
            log.error(f"获取变量数据项失败")
            return False

        ok = set_data_item(di, value)
        if not ok:
            log.error(f"写变量失败")
            return False
        return ok

    def set_03(self, di: int, value: list[str, tuple[str, str]]) -> bool:
        """
        写事件记录
        :param di: 数据项
        :param value: 值
        :return:
        """
        data_item = get_data_item(di)
        if data_item is None:
            log.error(f"获取事件记录数据项失败")
            return False

        if not set_data_item(di, value):
            log.error(f"写事件记录失败")
            return False
        return True

    def set_04(self, di: int, value: str | list) -> bool:
        """
        写参变量
        :param di: 数据项
        :param value: 值
        :return:
        """
        data_item = get_data_item(di)
        if data_item is None:
            log.error(f"获取参变量数据项失败")
            return False

        if not set_data_item(di, value):
            log.error(f"写参变量失败")
            return False
        return True

    def get_data_item(self, di: int) -> Optional[DataItem]:
        """
        获取数据项
        :param di: 数据项
        :return:
        """
        return get_data_item(di)

    def handle_request(self, frame):
        """
        处理读数据请求
        :param frame:
        :return:
        """
        try:
            # 1. 验证设备
            if not validate_device(self.address, frame.ctrl_code, frame.addr):
                log.error(f"验证设备地址: {bytes_to_spaced_hex(frame.addr)} 失败")
                # 返回未授权异常帧
                return self._build_error_response(
                    frame, error_code=ErrorCode.OtherError
                )

            # 2. 根据控制码判断请求类型
            if frame.ctrl_code == CtrlCode.BroadcastTimeSync:  # 广播校时
                log.info(f"广播校时: {bytes_to_spaced_hex(frame.data)}")
                self.set_time(frame.data)
                return DLT645Protocol.build_frame(
                    frame.addr, frame.ctrl_code | 0x80, frame.data
                )
            elif frame.ctrl_code == CtrlCode.ReadData:
                # 解析数据标识
                di = frame.data
                di3 = di[3]
                if di3 == 0x00:  # 读取电能
                    # 构建响应帧
                    res_data = bytearray(8)
                    # 解析数据标识为 32 位无符号整数
                    data_id = struct.unpack("<I", frame.data[:DI_LEN])[0]
                    data_item = get_data_item(data_id)
                    if data_item is None:
                        log.error(f"数据项未找到: {data_id}")
                        return self._build_error_response(
                            frame, error_code=ErrorCode.RequestDataEmpty
                        )
                    res_data[:DI_LEN] = frame.data[:DI_LEN]  # 仅复制前 4 字节数据标识
                    value = data_item.value
                    # 转换为 BCD 码
                    bcd_value = float_to_bcd(value, data_item.data_format, "little")
                    res_data[DI_LEN:] = bcd_value
                    return DLT645Protocol.build_frame(
                        frame.addr, frame.ctrl_code | 0x80, bytes(res_data)
                    )
                elif di3 == 0x01:  # 读取最大需量及发生时间
                    res_data = bytearray(12)
                    # 解析数据标识为 32 位无符号整数
                    data_id = struct.unpack("<I", frame.data[:DI_LEN])[0]
                    data_item = get_data_item(data_id)
                    if data_item is None:
                        log.error(f"数据项未找到: {data_id}")
                        return self._build_error_response(
                            frame, error_code=ErrorCode.RequestDataEmpty
                        )
                    res_data[:DI_LEN] = frame.data[:DI_LEN]  # 返回数据标识
                    demand: Demand = data_item.value
                    # 转换为 BCD 码
                    bcd_value = float_to_bcd(
                        demand.value, data_item.data_format, "little"
                    )
                    res_data[DI_LEN : DI_LEN + 3] = bcd_value[:3]
                    # 需量发生时间
                    res_data[DI_LEN + 3 : 12] = datetime_to_bcd(demand.time)
                    return DLT645Protocol.build_frame(
                        frame.addr, frame.ctrl_code | 0x80, bytes(res_data)
                    )
                elif di3 == 0x02:  # 读变量
                    # 解析数据标识为 32 位无符号整数
                    data_id = struct.unpack("<I", frame.data[:DI_LEN])[0]
                    data_item = get_data_item(data_id)
                    if data_item is None:
                        log.error(f"数据项未找到: {data_id}")
                        return self._build_error_response(
                            frame, error_code=ErrorCode.RequestDataEmpty
                        )
                    # 变量数据长度
                    data_len = DI_LEN
                    data_len += (
                        len(data_item.data_format) - 1
                    ) // 2  # (数据格式长度 - 1 位小数点)/2
                    # 构建响应帧
                    res_data = bytearray(data_len)
                    res_data[:DI_LEN] = frame.data[:DI_LEN]  # 仅复制前 DI_LEN 字节
                    value = data_item.value
                    # 转换为 BCD 码（小端序）
                    bcd_value = float_to_bcd(value, data_item.data_format, "little")
                    res_data[DI_LEN:data_len] = bcd_value
                    return DLT645Protocol.build_frame(
                        frame.addr, frame.ctrl_code | 0x80, bytes(res_data)
                    )
                elif di3 == 0x03:  # 读事件记录
                    # 解析数据标识为 32 位无符号整数
                    data_id = struct.unpack("<I", frame.data[:DI_LEN])[0]
                    data_item: Optional[List[DataItem]] = get_data_item(data_id)
                    if data_item is None:
                        log.error(f"数据项未找到: {data_id}")
                        return self._build_error_response(
                            frame, error_code=ErrorCode.RequestDataEmpty
                        )

                    res_data = bytearray()
                    res_data.extend(frame.data[:DI_LEN])  # 仅复制前 DI_LEN 字节
                    for item in data_item:
                        event_record: EventRecord = item.value
                        if isinstance(event_record.event, tuple):
                            for event_item in reversed(event_record.event):
                                value = string_to_bcd(event_item, "little")
                                res_data.extend(value)
                        elif isinstance(event_record.event, str):
                            value = string_to_bcd(event_record.event, "little")
                            res_data.extend(value)
                        elif isinstance(event_record.event, float):
                            value = float_to_bcd(event_record.event, "little")
                            res_data.extend(value)
                    return DLT645Protocol.build_frame(
                        frame.addr, frame.ctrl_code | 0x80, bytes(res_data)
                    )
                elif di3 == 0x04:  # 读参变量
                    # 解析数据标识为 32 位无符号整数
                    data_id = struct.unpack("<I", frame.data[:DI_LEN])[0]
                    data_item = get_data_item(data_id)
                    if data_item is None:
                        log.error(f"数据项未找到: {data_id}")
                        return self._build_error_response(
                            frame, error_code=ErrorCode.RequestDataEmpty
                        )

                    # 变量数据长度
                    data_len = DI_LEN
                    # 时段表数据
                    if (
                        0x04010000
                        <= int.from_bytes(di, byteorder="little")
                        <= 0x04020008
                    ):
                        res_data = bytearray(DI_LEN + len(data_item) * 2)
                        for i, item in enumerate(data_item):
                            step = len(item.data_format) // 2
                            data_len += step
                            res_data[:DI_LEN] = frame.data[:DI_LEN]  # 复制数据标识
                            value = item.value
                            bcd_value = string_to_bcd(value, "little")

                            # 扩展res_data以容纳BCD数据
                            res_data[DI_LEN + step * i : DI_LEN + step * (i + 1)] = (
                                bcd_value
                            )
                        return DLT645Protocol.build_frame(
                            frame.addr, frame.ctrl_code | 0x80, bytes(res_data)
                        )
                    else:
                        # 根据数据格式确定数据长度
                        data_format = data_item.data_format
                        data_len += len(data_format) // 2

                        # 构建响应帧
                        res_data = bytearray(data_len)
                        res_data[:DI_LEN] = frame.data[:DI_LEN]  # 复制数据标识
                        value = data_item.value

                        bcd_value = string_to_bcd(value, "little")

                        # 扩展res_data以容纳BCD数据
                        res_data[DI_LEN : DI_LEN + data_len] = bcd_value

                        return DLT645Protocol.build_frame(
                            frame.addr, frame.ctrl_code | 0x80, bytes(res_data)
                        )
                else:
                    log.error(f"未知的数据标识类型: {hex(di3)}")
                    return self._build_error_response(
                        frame, error_code=ErrorCode.OtherError
                    )
            elif frame.ctrl_code == CtrlCode.WriteData:
                log.debug(f"收到写数据请求: {bytes_to_spaced_hex(frame.data)}")
                # 解析数据标识为 32 位无符号整数
                data_id = struct.unpack("<I", frame.data[:DI_LEN])[0]
                data_item = get_data_item(data_id)
                if data_item is None:
                    log.error(f"数据项未找到: {data_id}")
                    return self._build_error_response(
                        frame, error_code=ErrorCode.RequestDataEmpty
                    )

                # 提取密码
                password = frame.data[DI_LEN : DI_LEN + PASSWORD_LEN]
                if not self.password_manager.check_password(password):
                    log.error(f"密码错误: {bytes_to_spaced_hex(password)}")
                    return self._build_error_response(
                        frame, error_code=ErrorCode.AuthFailed
                    )

                # 提取操作者代码
                operator_code = frame.data[
                    DI_LEN + PASSWORD_LEN : DI_LEN + PASSWORD_LEN + OPERATOR_CODE_LEN
                ]

                # 提取数据
                data_len = len(frame.data) - DI_LEN - PASSWORD_LEN
                data = frame.data[
                    DI_LEN
                    + PASSWORD_LEN
                    + OPERATOR_CODE_LEN : DI_LEN
                    + PASSWORD_LEN
                    + OPERATOR_CODE_LEN
                    + data_len
                ]
                # 解析数据
                value = bcd_to_value(data, data_item.data_format, "little")
                if not set_data_item(data_id, value):
                    log.error(f"设置数据项 {data_id} 失败")
                    return self._build_error_response(
                        frame, error_code=ErrorCode.OtherError
                    )

                # 构建响应帧
                res_data = bytearray()  # 广播校时不需要返回数据
                return DLT645Protocol.build_frame(
                    frame.addr, frame.ctrl_code | 0x80, res_data
                )
            elif frame.ctrl_code == CtrlCode.ReadAddress:
                # 构建响应帧
                res_data = self.address[:ADDRESS_LEN]
                return DLT645Protocol.build_frame(
                    bytes(self.address), frame.ctrl_code | 0x80, bytes(res_data)
                )
            elif frame.ctrl_code == CtrlCode.WriteAddress:
                res_data = bytearray()
                # 解析数据
                addr = frame.data[:ADDRESS_LEN]
                self.set_address(addr)  # 设置通讯地址
                return DLT645Protocol.build_frame(
                    bytes(self.address), frame.ctrl_code | 0x80, res_data
                )
            elif frame.ctrl_code == CtrlCode.ChangePassword:
                # 解析数据
                res_data = bytearray()
                old_password = frame.data[DI_LEN : DI_LEN + PASSWORD_LEN]
                new_password = frame.data[
                    DI_LEN + PASSWORD_LEN : DI_LEN + PASSWORD_LEN * 2
                ]
                if not self.password_manager.change_password(
                    old_password, new_password
                ):
                    log.error(f"修改密码失败")
                    return self._build_error_response(
                        frame, error_code=ErrorCode.AuthFailed
                    )
                res_data = new_password  # 返回新密码响应
                return DLT645Protocol.build_frame(
                    bytes(self.address), frame.ctrl_code | 0x80, res_data
                )
            else:
                log.error(f"未知的控制码: {hex(frame.ctrl_code)}")
                return self._build_error_response(
                    frame, error_code=ErrorCode.OtherError
                )
        except Exception as e:
            # 捕获其他未预期的异常
            log.error(f"处理请求时发生未预期异常: {str(e)}")
            # 返回通用错误异常帧
            return self._build_error_response(frame, error_code=ErrorCode.OtherError)

    def _build_error_response(self, frame, error_code: int):
        """
        构建异常响应帧
        :param frame: 原始请求帧
        :param error_code: 错误码
        :return: 异常响应帧
        """
        # 构建异常响应帧，控制码最高位设为1表示响应
        log.debug(
            f"构建异常响应帧: 地址={frame.addr.hex()}, 控制码={hex(frame.ctrl_code | 0xC0)}, 错误码={error_code}"
        )
        error_data = bytes([error_code])
        return DLT645Protocol.build_frame(  # D7=1, D6=1表示异常响应, C=1100
            frame.addr, frame.ctrl_code | 0xC0, error_data
        )
