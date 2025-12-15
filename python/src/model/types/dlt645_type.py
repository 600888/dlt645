from enum import IntEnum
from datetime import datetime

from ...common.transform import bytes_to_spaced_hex
from ...model.log import log


# 模拟 DICategory 枚举
class DICategory(IntEnum):
    CategoryEnergy = 0  # 电能
    CategoryDemand = 1  # 需量
    CategoryVariable = 2  # 变量
    CategoryEvent = 3  # 事件记录
    CategoryParameter = 4  # 参变量
    CategoryFreeze = 5  # 冻结量
    CategoryLoad = 6  # 负荷纪录


class CtrlCode(IntEnum):
    BroadcastTimeSync = 0x08  # 广播校时
    ReadData = 0x11  # 读数据
    ReadAddress = 0x13  # 读通讯地址
    WriteData = 0x14  # 写数据
    WriteAddress = 0x15  # 写通讯地址
    FreezeCmd = 0x16  # 冻结命令
    ChangeBaudRate = 0x17  # 修改通信速率
    ChangePassword = 0x18  # 改变密码


class ErrorCode(IntEnum):
    OtherError = 0b0000001  # 其他错误
    RequestDataEmpty = 0b0000010  # 无请求数据
    AuthFailed = 0b0000100  # 认证失败
    CommRateImmutable = 0b0001000  # 通信速率不可改变
    YearZoneNumExceeded = 0b0010000  # 年区数超出范围
    DaySlotNumExceeded = 0b0100000  # 日区数超出范围
    RateNumExceeded = 0b1000000  # 速率数超出范围


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
    return error_messages.get(error_code, "未知错误码")


DI_LEN = 4  # 数据标识长度
ADDRESS_LEN = 6  # 地址长度
PASSWORD_LEN = 4  # 密码长度
OPERATOR_CODE_LEN = 4  # 操作者代码长度


class Demand:
    def __init__(self, value: float, time: datetime):
        self.value = value
        self.time = time

    def __repr__(self) -> str:
        return f"Demand(value={self.value}, time={self.time.strftime('%Y-%m-%d %H:%M:%S')})"


class EventRecord:
    def __init__(self, di: int, event: tuple | float | str):
        self.di = di
        self.event = event

    def __repr__(self) -> str:
        return f"EventRecord(di={self.di}, event={self.event})"


class PasswordManager:
    def __init__(self):
        self._password_map: dict[int, bytearray] = {}  # 九级密码
        for i in range(9):
            self._password_map[i] = bytearray(PASSWORD_LEN)

    def is_password_valid(self, password: bytearray) -> bool:
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
        if not self.is_password_valid(password):
            return False
        level = password[0]
        self._password_map[level] = password
        log.debug(f"设置密码成功，级别：{level}, 密码：{bytes_to_spaced_hex(password)}")
        return True

    def get_password(self, level: int) -> bytearray:
        return self._password_map.get(level, bytearray(PASSWORD_LEN))

    def check_password(self, password: bytearray) -> bool:
        if not self.is_password_valid(password):
            return False
        level = password[0]
        return password == self._password_map.get(level, bytearray(PASSWORD_LEN))

    def change_password(self, old_password: bytearray, new_password: bytearray) -> bool:
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
