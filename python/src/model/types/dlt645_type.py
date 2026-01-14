"""DLT645 协议类型定义模块。

本模块定义了 DLT645 协议所需的各种类型，包括：
- 数据标识分类枚举 (DICategory)
- 控制码枚举 (CtrlCode)
- 错误码枚举 (ErrorCode)
- 需量数据类 (Demand)
- 事件记录类 (EventRecord)
- 密码管理器类 (PasswordManager)
"""

from enum import IntEnum
from datetime import datetime

from ...common.transform import bytes_to_spaced_hex
from ...model.log import log


class DICategory(IntEnum):
    """数据标识分类枚举。

    DLT645 协议中数据项按功能分为多个类别，
    数据标识 (DI) 的高字节决定了数据所属的类别。

    :cvar CategoryEnergy: 电能量数据（0x00）
    :cvar CategoryDemand: 需量数据（0x01）
    :cvar CategoryVariable: 变量数据（0x02）
    :cvar CategoryEvent: 事件记录数据（0x03）
    :cvar CategoryParameter: 参变量数据（0x04）
    :cvar CategoryFreeze: 冻结量数据（0x05）
    :cvar CategoryLoad: 负荷记录数据（0x06）
    """

    CategoryEnergy = 0  # 电能
    CategoryDemand = 1  # 需量
    CategoryVariable = 2  # 变量
    CategoryEvent = 3  # 事件记录
    CategoryParameter = 4  # 参变量
    CategoryFreeze = 5  # 冻结量
    CategoryLoad = 6  # 负荷纪录


class CtrlCode(IntEnum):
    """控制码枚举。

    DLT645 协议中控制码用于标识帧的功能类型。

    :cvar BroadcastTimeSync: 广播校时命令（0x08）
    :cvar ReadData: 读数据命令（0x11）
    :cvar ReadAddress: 读通讯地址命令（0x13）
    :cvar WriteData: 写数据命令（0x14）
    :cvar WriteAddress: 写通讯地址命令（0x15）
    :cvar FreezeCmd: 冻结命令（0x16）
    :cvar ChangeBaudRate: 修改通信速率命令（0x17）
    :cvar ChangePassword: 修改密码命令（0x18）
    """

    BroadcastTimeSync = 0x08  # 广播校时
    ReadData = 0x11  # 读数据
    ReadAddress = 0x13  # 读通讯地址
    WriteData = 0x14  # 写数据
    WriteAddress = 0x15  # 写通讯地址
    FreezeCmd = 0x16  # 冻结命令
    ChangeBaudRate = 0x17  # 修改通信速率
    ChangePassword = 0x18  # 改变密码


class ErrorCode(IntEnum):
    """错误码枚举。

    DLT645 协议中从站响应异常时返回的错误码。
    错误码采用位域方式，可以组合多个错误。

    :cvar OtherError: 其他错误（bit0）
    :cvar RequestDataEmpty: 无请求数据（bit1）
    :cvar AuthFailed: 认证失败/密码错误（bit2）
    :cvar CommRateImmutable: 通信速率不可改变（bit3）
    :cvar YearZoneNumExceeded: 年时区数超出范围（bit4）
    :cvar DaySlotNumExceeded: 日时段数超出范围（bit5）
    :cvar RateNumExceeded: 费率数超出范围（bit6）
    """

    OtherError = 0b0000001  # 其他错误
    RequestDataEmpty = 0b0000010  # 无请求数据
    AuthFailed = 0b0000100  # 认证失败
    CommRateImmutable = 0b0001000  # 通信速率不可改变
    YearZoneNumExceeded = 0b0010000  # 年区数超出范围
    DaySlotNumExceeded = 0b0100000  # 日区数超出范围
    RateNumExceeded = 0b1000000  # 速率数超出范围


#: 错误码对应的中文错误信息映射表
error_messages = {
    ErrorCode.OtherError: "其他错误",
    ErrorCode.RequestDataEmpty: "无请求数据",
    ErrorCode.AuthFailed: "认证失败",
    ErrorCode.CommRateImmutable: "通信速率不可改变",
    ErrorCode.YearZoneNumExceeded: "年区数超出范围",
    ErrorCode.DaySlotNumExceeded: "日区数超出范围",
    ErrorCode.RateNumExceeded: "速率数超出范围",
}


def get_error_msg(error_code: ErrorCode) -> str:
    """根据错误码获取对应的中文错误信息。

    :param error_code: 错误码。
    :type error_code: ErrorCode
    :return: 对应的中文错误信息，如果错误码未知则返回 "未知错误码"。
    :rtype: str
    """
    return error_messages.get(error_code, "未知错误码")


#: 数据标识长度（4字节）
DI_LEN = 4
#: 设备地址长度（6字节）
ADDRESS_LEN = 6
#: 密码长度（4字节）
PASSWORD_LEN = 4
#: 操作者代码长度（4字节）
OPERATOR_CODE_LEN = 4


class Demand:
    """需量数据类。

    用于表示最大需量及其发生时间。

    :ivar value: 需量值（单位由具体数据项定义）。
    :ivar time: 需量发生时间。
    """

    def __init__(self, value: float, time: datetime):
        """初始化 Demand 实例。

        :param value: 需量值。
        :type value: float
        :param time: 需量发生时间。
        :type time: datetime
        """
        self.value = value
        self.time = time

    def __repr__(self) -> str:
        """返回 Demand 的字符串表示。

        :return: 字符串表示。
        :rtype: str
        """
        return f"Demand(value={self.value}, time={self.time.strftime('%Y-%m-%d %H:%M:%S')})"


class EventRecord:
    """事件记录类。

    用于表示电表的事件记录数据。

    :ivar di: 数据标识 (DI)。
    :ivar event: 事件数据，可以是元组、浮点数或字符串。
    """

    def __init__(self, di: int, event: tuple | float | str):
        """初始化 EventRecord 实例。

        :param di: 数据标识。
        :type di: int
        :param event: 事件数据。
        :type event: tuple | float | str
        """
        self.di = di
        self.event = event

    def __repr__(self) -> str:
        """返回 EventRecord 的字符串表示。

        :return: 字符串表示。
        :rtype: str
        """
        return f"EventRecord(di={self.di}, event={self.event})"


class PasswordManager:
    """密码管理器类。

    用于管理 DLT645 协议中的九级密码。
    密码级别从 0-8，数字越小权限越高。

    :ivar _password_map: 密码映射表，键为密码级别，值为密码字节数组。
    """

    def __init__(self):
        """初始化 PasswordManager 实例。

        创建九级密码映射表，每级密码初始化为全零。
        """
        self._password_map: dict[int, bytearray] = {}  # 九级密码
        for i in range(9):
            self._password_map[i] = bytearray(PASSWORD_LEN)

    def is_password_valid(self, password: bytearray) -> bool:
        """验证密码格式是否有效。

        检查密码长度是否为4字节，以及密码级别是否在有效范围内（0-8）。

        :param password: 待验证的密码字节数组。
        :type password: bytearray
        :return: 密码格式有效返回 True，否则返回 False。
        :rtype: bool
        """
        if len(password) != PASSWORD_LEN:
            log.error(f"密码长度错误，长度：{len(password)}, 要求长度：{PASSWORD_LEN}")
            return False

        # 密码级别不能超过9
        level = password[0]
        if level >= 9:
            log.error(f"密码级别错误，级别：{level}, 超出密码权限级别")
            return False
        return True

    def set_password(self, password: bytearray) -> bool:
        """设置指定级别的密码。

        :param password: 密码字节数组，第一个字节为密码级别。
        :type password: bytearray
        :return: 设置成功返回 True，失败返回 False。
        :rtype: bool
        """
        if not self.is_password_valid(password):
            return False
        level = password[0]
        self._password_map[level] = password
        log.debug(f"设置密码成功，级别：{level}, 密码：{bytes_to_spaced_hex(password)}")
        return True

    def get_password(self, level: int) -> bytearray:
        """获取指定级别的密码。

        :param level: 密码级别（0-8）。
        :type level: int
        :return: 密码字节数组，如果级别不存在则返回全零密码。
        :rtype: bytearray
        """
        return self._password_map.get(level, bytearray(PASSWORD_LEN))

    def check_password(self, password: bytearray) -> bool:
        """验证密码是否正确。

        :param password: 待验证的密码字节数组。
        :type password: bytearray
        :return: 密码正确返回 True，错误返回 False。
        :rtype: bool
        """
        if not self.is_password_valid(password):
            return False
        level = password[0]
        return password == self._password_map.get(level, bytearray(PASSWORD_LEN))

    def change_password(self, old_password: bytearray, new_password: bytearray) -> bool:
        """修改密码。

        只有当旧密码正确且旧密码权限等级不低于新密码权限等级时才能修改成功。
        权限等级数字越小权限越高（0级最高，8级最低）。

        :param old_password: 旧密码字节数组。
        :type old_password: bytearray
        :param new_password: 新密码字节数组。
        :type new_password: bytearray
        :return: 修改成功返回 True，失败返回 False。
        :rtype: bool
        """
        log.debug(
            f"尝试修改密码，旧密码：{bytes_to_spaced_hex(old_password)}, 新密码：{bytes_to_spaced_hex(new_password)}"
        )
        # 新密码权限
        new_level = new_password[0]
        old_level = old_password[0]
        if not self.is_password_valid(new_password):
            return False

        if old_password != self.get_password(old_level):
            log.error(f"旧密码错误，旧密码：{bytes_to_spaced_hex(old_password)}")
            return False

        if old_level <= new_level:  # 数字越小，权限越高
            return self.set_password(new_password)
        else:
            log.error(
                f"旧密码权限等级不能低于新密码权限等级，旧密码权限等级：{old_level}, 新密码权限等级：{new_level}, 权限不足!"
            )
            return False

