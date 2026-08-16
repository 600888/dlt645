"""DLT645 服务端服务模块。

本模块实现了 DLT645 协议的服务端业务服务功能，包括：
- 处理客户端数据读取请求
- 处理客户端数据写入请求
- 通讯地址管理
- 密码验证和管理
"""

import struct
from datetime import datetime
from typing import Any, List, Optional, Union

from ...common.transform import (
    bytes_to_spaced_hex,
    float_to_bcd,
    datetime_to_bcd,
    string_to_bcd,
    bcd_to_value,
    bcd_to_string,
    bcd_to_byte,
    parse_format,
)
from ...model.data.data_handler import clone_data_map, get_data_item, set_data_item
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
    CodeToBaudRate,
    BroadcastAddr,
)
from ...protocol.protocol import DLT645Protocol
from ...service.serversvc.log import log
from ...transport.server.rtu_server import RtuServer
from ...transport.server.tcp_server import TcpServer
from ...common.message_capture import MessageCapture
from ...common.message_types import MessageRecord, MessagePair


class MeterServerService:
    """电表服务端服务类。

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
        address: Optional[bytearray] = None,
        password_manager: Optional[PasswordManager] = None,
    ):
        """初始化电表服务端服务。

        :param server: 通信服务器实例（TcpServer 或 RtuServer）。
        :type server: Union[TcpServer, RtuServer]
        :param address: 设备地址，默认为全零。
        :type address: Optional[bytearray]
        :param password_manager: 密码管理器，默认创建新实例。
        :type password_manager: Optional[PasswordManager]
        """
        self.server = server
        self.address = bytearray(address if address is not None else bytes(6))
        self.password_manager = password_manager or PasswordManager()
        self.data_map = clone_data_map()
        self.clear_meter_event_records = []  # 记录电表清零事件
        self.event_records = []  # 记录事件
        # 当前表内时钟（广播校时后更新）
        self.time: Optional[datetime] = None
        # 最近一次冻结命令的原始数据域（MMDDhhmm）
        self.last_freeze_time: Optional[bytearray] = None
        # 当前通信速率（bps）
        self.baud_rate: int = 9600

    @classmethod
    def new_tcp_server(
        cls, ip: str, port: int, timeout: float = 5.0
    ) -> "MeterServerService":
        """创建 TCP 服务器

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
        """创建 RTU 服务器

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
        """创建新的MeterServerService实例

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
        """广播校时：解析 YYMMDDhhmmss 并设置表内时钟。

        按 DL/T645-2007 第6节：广播校时数据域为 6 字节压缩 BCD 码，
        依次为年（后两位）、月、日、时、分、秒（自然顺序）。

        :param data_bytes: 数据域（6字节）。
        :type data_bytes: bytearray
        """
        if data_bytes is None or len(data_bytes) < 6:
            log.warning(
                f"广播校时数据长度无效: {bytes_to_spaced_hex(data_bytes) if data_bytes else 'None'}"
            )
            return
        year = bcd_to_byte(data_bytes[0]) + 2000
        month = bcd_to_byte(data_bytes[1])
        day = bcd_to_byte(data_bytes[2])
        hour = bcd_to_byte(data_bytes[3])
        minute = bcd_to_byte(data_bytes[4])
        second = bcd_to_byte(data_bytes[5])
        try:
            self.time = datetime(year, month, day, hour, minute, second)
            log.info(f"广播校时成功: {self.time.strftime('%Y-%m-%d %H:%M:%S')}")
        except ValueError as e:
            log.error(f"广播校时时间无效: {e}")

    def set_address(self, address: Union[str, bytes, bytearray]) -> bool:
        """写通讯地址

        :param address:
        :return:
        """
        encoded = string_to_bcd(address) if isinstance(address, str) else bytearray(address)
        if len(encoded) != ADDRESS_LEN:
            raise ValueError("invalid address length")
        self.address = bytearray(encoded)
        return True

    def set_password(self, password: str) -> bool:
        """写密码

        :param password:
        :return:
        """
        password = string_to_bcd(password)
        if not self.password_manager.set_password(password):
            return False
        log.info(f"设置密码: {bytes_to_spaced_hex(password)}")
        return True

    def set_00(self, di: int, value: float) -> bool:
        """写电能量

        :param di: 数据项
        :param value: 值
        :return:
        """
        ok = set_data_item(di, value, self.data_map)
        if not ok:
            log.error("写电能量失败")
        return ok

    def set_01(self, di: int, demand: Demand) -> bool:
        """写最大需量及发生时间

        :param di: 数据项
        :param demand: 值
        :return:
        """
        ok = set_data_item(di, demand, self.data_map)
        if not ok:
            log.error("写最大需量及发生时间失败")
        return ok

    def set_02(self, di: int, value: float) -> bool:
        """写变量

        :param di: 数据项
        :param value: 值
        :return:
        """
        data_item = get_data_item(di, self.data_map)
        if data_item is None:
            log.error("获取变量数据项失败")
            return False

        ok = set_data_item(di, value, self.data_map)
        if not ok:
            log.error("写变量失败")
            return False
        return ok

    def set_03(self, di: int, value: list[str, tuple[str, str]]) -> bool:
        """写事件记录

        :param di: 数据项
        :param value: 值
        :return:
        """
        data_item = get_data_item(di, self.data_map)
        if data_item is None:
            log.error("获取事件记录数据项失败")
            return False

        if not set_data_item(di, value, self.data_map):
            log.error("写事件记录失败")
            return False
        return True

    def set_04(self, di: int, value: str | list) -> bool:
        """写参变量

        :param di: 数据项
        :param value: 值
        :return:
        """
        data_item = get_data_item(di, self.data_map)
        if data_item is None:
            log.error("获取参变量数据项失败")
            return False

        if not set_data_item(di, value, self.data_map):
            log.error("写参变量失败")
            return False
        return True

    def get_data_item(self, di: int) -> Optional[DataItem]:
        """获取数据项

        :param di: 数据项
        :return:
        """
        return get_data_item(di, self.data_map)

    def _check_password_with_level(self, password: bytearray, max_level: int) -> bool:
        """校验密码是否匹配且权限级别满足要求。

        按 DL/T645-2007 第9节：密码首字节为权限级别（00 最高，数值越大权限越低），
        02 级可执行电表清零、事件清零，04 级可执行写数据、最大需量清零。

        :param password: 密码字节数组（首字节为权限级别）。
        :type password: bytearray
        :param max_level: 允许的最大权限级别（数字越小权限越高）。
        :type max_level: int
        :return: 校验通过返回 True，否则返回 False。
        :rtype: bool
        """
        if not self.password_manager.check_password(password):
            return False
        return password[0] <= max_level

    def _reset_energy_data(self) -> None:
        """清空累计量数据（电表清零）。

        按 DL/T645-2007 第11节：电表清零清空电能表内电能量、最大需量及
        发生时间、冻结量、事件记录、负荷记录等累计数据；
        运行变量（0x02 当前电压/电流/功率等瞬时量）不属于清零范围。
        """
        for di, item in self.data_map.items():
            di3 = (di >> 24) & 0xFF  # DI 高字节为数据分类
            if di3 not in (0x00, 0x01, 0x05):  # 电能/需量/冻结量
                continue
            if isinstance(item, list):
                continue
            if isinstance(item.value, Demand):
                item.value = Demand(0.0, datetime.now())
            elif isinstance(item.value, (int, float)):
                item.value = 0.0

    def _reset_event_records(self, di: int) -> None:
        """清空事件记录数据（事件清零）。

        按 DL/T645-2007 第12节：事件总清零（di=FFFFFFFF）清空全部事件记录；
        分项事件清零仅清空指定数据标识的事件。执行时不允许清空事件清零记录
        和电表清零记录数据（DI 0x03300100~0x033002FF）。
        清零后事件值置为与 data_format 等长的全零字符串，保证 BCD 长度不变。

        :param di: 数据标识，FFFFFFFF 表示事件总清零。
        :type di: int
        """
        for d, item in self.data_map.items():
            di3 = (d >> 24) & 0xFF
            if di3 != 0x03:  # 事件记录
                continue
            # 分项事件清零：仅清空指定数据标识
            if di != 0xFFFFFFFF and d != di:
                continue
            # 保留事件清零记录和电表清零记录
            if 0x03300100 <= d <= 0x033002FF:
                continue
            if isinstance(item, list):
                for sub in item:
                    event_record: EventRecord = sub.value
                    if isinstance(event_record.event, tuple):
                        # data_format 如 "XXXXXX,XXXXXX"，每字段字符数即其长度
                        step = len(sub.data_format.split(",")[0])
                        event_record.event = tuple("0" * step for _ in event_record.event)
                    else:
                        step = len(sub.data_format)
                        event_record.event = "0" * step
            elif isinstance(item.value, EventRecord):
                step = len(item.data_format)
                item.value.event = "0" * step

    def _record_event_clear(self, operator_code: bytearray) -> None:
        """记录事件清零事件（DL/T645-2007 第12节）。

        递增 0x03300200 事件清零总次数，并更新 0x03300201 上1次事件清零记录
        中的发生时刻与操作者代码。

        :param operator_code: 操作者代码（4字节）。
        :type operator_code: bytearray
        """
        # 事件清零总次数（0x03300200）加 1
        total = self.data_map.get(0x03300200)
        if total is not None:
            if isinstance(total, list):
                total = total[0]
            try:
                count = int(str(total.value.event)) + 1
                total.value.event = str(count).zfill(6)
            except (ValueError, TypeError):
                log.warning("事件清零总次数解析失败，跳过")
        # 上1次事件清零记录（0x03300201）：更新发生时刻与操作者代码
        record = self.data_map.get(0x03300201)
        if isinstance(record, list):
            for item in record:
                if "发生时刻" in item.name:
                    item.value.event = datetime.now().strftime("%y%m%d%H%M%S")
                elif "操作者代码" in item.name:
                    item.value.event = bcd_to_string(operator_code, "little")

    def handle_request(self, frame):
        """处理读数据请求

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
                # 广播校时不要求应答（DL/T645-2007 第6节），一律不返回响应
                return None
            elif frame.ctrl_code == CtrlCode.FreezeCmd:  # 冻结命令
                # 数据域：MMDDhhmm（月.日.时.分，各1字节压缩BCD，自然顺序）
                log.info(f"冻结命令: {bytes_to_spaced_hex(frame.data)}")
                self.last_freeze_time = bytearray(frame.data)
                # 广播冻结不要求应答（DL/T645-2007 第7节）
                if bytes(frame.addr) == bytes(BroadcastAddr.TimeSync):
                    return None
                return DLT645Protocol.build_frame(
                    frame.addr, frame.ctrl_code | 0x80, b""
                )
            elif frame.ctrl_code == CtrlCode.ChangeBaudRate:  # 更改通信速率
                # 数据域：1字节通信速率特征字（附录C）
                if len(frame.data) < 1:
                    return self._build_error_response(
                        frame, error_code=ErrorCode.RequestDataEmpty
                    )
                feature = frame.data[0]
                baud = CodeToBaudRate.get(feature)
                if baud is None:
                    log.error(f"无效的通信速率特征字: {hex(feature)}")
                    return self._build_error_response(
                        frame, error_code=ErrorCode.CommRateImmutable
                    )
                self.baud_rate = baud
                log.info(f"更改通信速率成功: {baud} bps (特征字 {hex(feature)})")
                # 正常应答帧中的特征字必须与请求帧相同（DL/T645-2007 第8节）
                return DLT645Protocol.build_frame(
                    frame.addr, frame.ctrl_code | 0x80, bytes([feature])
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
                    data_item = get_data_item(data_id, self.data_map)
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
                    data_item = get_data_item(data_id, self.data_map)
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
                    data_item = get_data_item(data_id, self.data_map)
                    if data_item is None:
                        log.error(f"数据项未找到: {data_id}")
                        return self._build_error_response(
                            frame, error_code=ErrorCode.RequestDataEmpty
                        )
                    # 变量数据长度：总位数 (含小数点前后) 加 1 后整除 2，
                    # 对无小数点格式（如 XXXXXXXX）同样成立
                    _, total_digits = parse_format(data_item.data_format)
                    data_len = DI_LEN + (total_digits + 1) // 2
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
                    data_item: Optional[List[DataItem]] = get_data_item(
                        data_id, self.data_map
                    )
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
                    data_item = get_data_item(data_id, self.data_map)
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
                data_item = get_data_item(data_id, self.data_map)
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
                if not set_data_item(data_id, value, self.data_map):
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
                    log.error("修改密码失败")
                    return self._build_error_response(
                        frame, error_code=ErrorCode.AuthFailed
                    )
                res_data = new_password  # 返回新密码响应
                return DLT645Protocol.build_frame(
                    bytes(self.address), frame.ctrl_code | 0x80, res_data
                )
            elif frame.ctrl_code == CtrlCode.ClearDemand:
                log.debug(f"收到需量清零请求: {bytes_to_spaced_hex(frame.data)}")
                # 数据域：DI(4字节) + 密码(4字节)，需 04 级及以上权限
                if len(frame.data) < DI_LEN + PASSWORD_LEN:
                    return self._build_error_response(
                        frame, error_code=ErrorCode.RequestDataEmpty
                    )
                # 解析数据标识为 32 位无符号整数
                data_id = struct.unpack("<I", frame.data[:DI_LEN])[0]
                # 需量清零仅作用于需量类数据标识（DI3=01）
                if (data_id >> 24) & 0xFF != 0x01:
                    log.error(f"需量清零数据标识必须为需量类(0x01xxxxxx): {hex(data_id)}")
                    return self._build_error_response(
                        frame, error_code=ErrorCode.OtherError
                    )
                data_item = get_data_item(data_id, self.data_map)
                if data_item is None:
                    log.error(f"数据项未找到: {data_id}")
                    return self._build_error_response(
                        frame, error_code=ErrorCode.RequestDataEmpty
                    )

                # 提取密码并校验权限（04级及以上）
                password = frame.data[DI_LEN : DI_LEN + PASSWORD_LEN]
                if not self._check_password_with_level(password, max_level=4):
                    log.error(f"密码错误或权限不足: {bytes_to_spaced_hex(password)}")
                    return self._build_error_response(
                        frame, error_code=ErrorCode.AuthFailed
                    )

                # 执行需量清零：将需量值设为0，时间设为当前时间
                cleared_demand = Demand(0.0, datetime.now())
                if not set_data_item(data_id, cleared_demand, self.data_map):
                    log.error(f"需量清零失败: {data_id}")
                    return self._build_error_response(
                        frame, error_code=ErrorCode.OtherError
                    )

                log.info(f"最大需量清零成功: DI={hex(data_id)}")

                # 构建响应帧
                res_data = bytearray()
                return DLT645Protocol.build_frame(
                    frame.addr, frame.ctrl_code | 0x80, res_data
                )
            elif frame.ctrl_code == CtrlCode.ClearMeter:  # 电表清零
                log.debug(f"收到电表清零请求: {bytes_to_spaced_hex(frame.data)}")
                if len(frame.data) < DI_LEN + PASSWORD_LEN:
                    return self._build_error_response(
                        frame, error_code=ErrorCode.RequestDataEmpty
                    )
                # 数据域：DI(4字节，规范固定为00000000H) + 密码(4字节)，02级及以上权限
                data_id = struct.unpack("<I", frame.data[:DI_LEN])[0]
                if data_id != 0x00000000:
                    log.error(f"电表清零数据标识必须为00000000H: {hex(data_id)}")
                    return self._build_error_response(
                        frame, error_code=ErrorCode.OtherError
                    )
                password = frame.data[DI_LEN : DI_LEN + PASSWORD_LEN]
                if not self._check_password_with_level(password, max_level=2):
                    log.error(f"密码错误或权限不足: {bytes_to_spaced_hex(password)}")
                    return self._build_error_response(
                        frame, error_code=ErrorCode.AuthFailed
                    )
                # 清空电能量、最大需量、冻结量、事件记录、负荷记录（保留清零类记录）
                self._reset_energy_data()
                self._reset_event_records(0xFFFFFFFF)
                self.clear_meter_event_records.append(
                    {"time": datetime.now(), "di": data_id}
                )
                log.info(f"电表清零成功: DI={hex(data_id)}")
                return DLT645Protocol.build_frame(
                    frame.addr, frame.ctrl_code | 0x80, b""
                )
            elif frame.ctrl_code == CtrlCode.ClearEvent:  # 事件清零
                log.debug(f"收到事件清零请求: {bytes_to_spaced_hex(frame.data)}")
                if len(frame.data) < PASSWORD_LEN + OPERATOR_CODE_LEN + DI_LEN:
                    return self._build_error_response(
                        frame, error_code=ErrorCode.RequestDataEmpty
                    )
                # 数据域：密码(4字节) + 操作者代码(4字节) + DI(4字节)，02级及以上权限
                password = frame.data[:PASSWORD_LEN]
                operator_code = frame.data[
                    PASSWORD_LEN : PASSWORD_LEN + OPERATOR_CODE_LEN
                ]
                data_id = struct.unpack(
                    "<I",
                    frame.data[
                        PASSWORD_LEN + OPERATOR_CODE_LEN :
                        PASSWORD_LEN + OPERATOR_CODE_LEN + DI_LEN
                    ],
                )[0]
                if not self._check_password_with_level(password, max_level=2):
                    log.error(f"密码错误或权限不足: {bytes_to_spaced_hex(password)}")
                    return self._build_error_response(
                        frame, error_code=ErrorCode.AuthFailed
                    )
                # 清空事件记录（保留事件清零记录和电表清零记录）
                self._reset_event_records(data_id)
                # 记录事件清零事件（总次数 +1，更新上1次记录）
                self._record_event_clear(operator_code)
                log.info(
                    f"事件清零成功: DI={hex(data_id)}, 操作者代码={bytes_to_spaced_hex(operator_code)}"
                )
                return DLT645Protocol.build_frame(
                    frame.addr, frame.ctrl_code | 0x80, b""
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
        """构建异常响应帧

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

    def start(self) -> bool:
        """启动底层服务端。"""
        return bool(self.server.start())

    def stop(self) -> bool:
        """停止底层服务端。"""
        return bool(self.server.stop())

    close = stop

    def __enter__(self) -> "MeterServerService":
        if not self.start():
            raise OSError("无法启动 DLT645 服务端")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()

    # ==================== 报文捕获方法 ====================

    def enable_message_capture(self, queue_size: int = 100) -> None:
        """启用报文捕获功能。

        :param queue_size: 报文队列大小，默认100
        :type queue_size: int
        """
        if self.server._message_capture is None:
            self.server._message_capture = MessageCapture(enabled=True, queue_size=queue_size)
        else:
            self.server._message_capture.enable()
            self.server._message_capture.set_queue_size(queue_size)
        log.info(f"报文捕获已启用，队列大小: {queue_size}")

    def disable_message_capture(self) -> None:
        """禁用报文捕获功能。"""
        if self.server._message_capture:
            self.server._message_capture.disable()
        log.info("报文捕获已禁用")

    def get_captured_messages(self, count: int = 0) -> List[MessageRecord]:
        """获取捕获的报文列表。

        :param count: 要获取的数量，0表示全部
        :type count: int
        :return: 报文列表
        :rtype: List[MessageRecord]
        """
        if self.server._message_capture:
            return self.server._message_capture.get_all_messages(count)
        return []

    def get_captured_tx_messages(self, count: int = 0) -> List[MessageRecord]:
        """获取捕获的发送报文列表。

        :param count: 要获取的数量，0表示全部
        :type count: int
        :return: 发送报文列表
        :rtype: List[MessageRecord]
        """
        if self.server._message_capture:
            return self.server._message_capture.get_tx_messages(count)
        return []

    def get_captured_rx_messages(self, count: int = 0) -> List[MessageRecord]:
        """获取捕获的接收报文列表。

        :param count: 要获取的数量，0表示全部
        :type count: int
        :return: 接收报文列表
        :rtype: List[MessageRecord]
        """
        if self.server._message_capture:
            return self.server._message_capture.get_rx_messages(count)
        return []

    def get_captured_pairs(self, count: int = 0) -> List[MessagePair]:
        """获取捕获的TX/RX配对列表。

        :param count: 要获取的数量，0表示全部
        :type count: int
        :return: 配对列表
        :rtype: List[MessagePair]
        """
        if self.server._message_capture:
            return self.server._message_capture.get_pairs(count)
        return []

    def clear_captured_messages(self) -> None:
        """清空所有捕获的报文。"""
        if self.server._message_capture:
            self.server._message_capture.clear()
        log.info("捕获的报文已清空")

    def get_message_capture_stats(self) -> dict:
        """获取报文捕获统计信息。

        :return: 统计信息字典
        :rtype: dict
        """
        if self.server._message_capture:
            return self.server._message_capture.get_stats()
        return {"enabled": False}
