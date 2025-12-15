import binascii
import struct
from datetime import datetime
from typing import Union


# 根据长度补0
def pad_with_zeros(length: int) -> str:
    return "0" * length


def bytes_to_int(byte_array: bytearray) -> int:
    """将字节数组转换为无符号整数"""
    if len(byte_array) < 4:
        # 补零操作
        byte_array = byte_array.ljust(4, b"\x00")
    return int.from_bytes(byte_array, byteorder="little", signed=False)


def bytes_to_float(byte_array: bytearray) -> float:
    """将字节数组转换为浮点数"""
    if len(byte_array) < 4:
        # 补零操作
        byte_array = byte_array.ljust(4, b"\x00")
    return struct.unpack("<f", byte_array)[0]


def bytes_to_spaced_hex(data: bytearray) -> str:
    """将字节切片转换为每两个字符用空格分隔的十六进制字符串，不足的补 0"""
    hex_str = binascii.hexlify(data).decode("utf-8")
    # 若十六进制字符串长度为奇数，在前面补 0
    if len(hex_str) % 2 == 1:
        hex_str = "0" + hex_str
    # 每两个字符用空格分隔
    spaced_hex = " ".join([hex_str[i : i + 2] for i in range(0, len(hex_str), 2)])
    return spaced_hex


def bcd_to_string(bcd: bytearray, endian="big") -> str:
    """将 BCD 码字节数组转换为数字字符串"""
    digits = []
    if endian == "little":
        bcd = bcd[::-1]
    for b in bcd:
        high = (b >> 4) & 0x0F
        low = b & 0x0F
        digits.append(str(high))
        digits.append(str(low))

    return "".join(digits)


def parse_format(format_str: str) -> (int, int):
    """解析格式字符串，返回小数位数和总位数"""
    if format_str.find(".") == -1:
        return 0, len(format_str)
    parts = format_str.split(".")
    if len(parts) != 2:
        raise ValueError(f"invalid format: {format_str}")
    decimal_places = len(parts[1])
    total_digits = len(parts[0]) + len(parts[1])
    return decimal_places, total_digits


def round_float(value: float, decimal_places: int) -> float:
    """浮点数四舍五入到指定小数位"""
    scale = 10**decimal_places
    return round(value * scale) / scale


def format_float(value: float, decimal_places: int, total_digits: int) -> str:
    """格式化浮点数为固定长度字符串（补零对齐）"""
    format_str = f"{{:0{total_digits}.{decimal_places}f}}"
    return format_str.format(value)


def string_to_bcd(digits: str, endian="big") -> bytearray:
    """将数字字符串转换为BCD码（支持大小端序）"""
    if len(digits) % 2 != 0:
        digits = "0" + digits  # 奇数位补零

    bcd = bytearray(len(digits) // 2)
    # 从字符串末尾开始处理（低位优先）
    for i in range(0, len(digits), 2):
        digit1 = int(digits[i])
        digit2 = int(digits[i + 1])
        byte_index = i // 2
        if endian == "little":
            byte_index = len(digits) // 2 - 1 - byte_index
        bcd[byte_index] = (digit1 << 4) | digit2
    return bytearray(bcd)


def bcd_to_value(bcd: bytearray, format_str: str, endian="big") -> Union[str, float]:
    """将BCD码字节数组转换为数值，支持不同数据格式和字节序"""
    if format_str.find(".") == -1:
        # 无小数点格式，转换为字符串
        return bcd_to_string(bcd, endian)
    else:
        # 有小数点格式，转换为浮点数
        return bcd_to_float(bcd, format_str, endian)


def float_to_bcd(value: float, format_str: str, endian="big") -> bytearray:
    """将float数值转换为BCD码字节数组，支持不同数据格式和字节序"""
    # 判断正负
    is_negative = value < 0
    abs_value = abs(value)

    # 解析格式获取小数位数和总长度
    decimal_places, total_length = parse_format(format_str)

    if decimal_places == 0:
        bcd = string_to_bcd(format_float(abs_value, 0, total_length), endian)
    else:
        # 四舍五入并格式化为字符串
        rounded = round_float(abs_value, decimal_places)
        str_value = format_float(rounded, decimal_places, 0)  # 不需要总长度参数

        # 分离整数部分和小数部分
        integer_part, decimal_part = str_value.split(".")

        # 计算整数部分和小数部分需要的长度
        int_length = total_length - decimal_places

        # 整数部分往前补 0
        if len(integer_part) < int_length:
            integer_part = "0" * (int_length - len(integer_part)) + integer_part

        # 小数部分往后补 0
        if len(decimal_part) < decimal_places:
            decimal_part += "0" * (decimal_places - len(decimal_part))

        # 合并整数部分和小数部分并移除小数点
        digits = integer_part + decimal_part

        # 转换为BCD码
        bcd = string_to_bcd(digits, endian)

    # 设置符号位
    if is_negative and bcd:
        if endian == "big":
            bcd = bytes([bcd[0] | 0x80]) + bcd[1:]
        else:
            bcd = bcd[:-1] + bytes([bcd[-1] | 0x80])
    return bcd


def bcd_to_float(bcd, format_str, endian="big") -> float:
    """将BCD码字节数组转换为float数值，支持不同字节序"""
    # 检查符号位
    is_negative = False
    if bcd:
        if endian == "big":
            is_negative = (bcd[0] & 0x80) != 0
            bcd = bytes([bcd[0] & 0x7F]) + bcd[1:]
        else:
            is_negative = (bcd[-1] & 0x80) != 0
            bcd = bcd[:-1] + bytes([bcd[-1] & 0x7F])

    # 根据字节序调整BCD码顺序, 默认转换成大端序处理
    if endian == "little":
        bcd = bcd[::-1]

    # 转换为字符串
    digits = bcd_to_string(bcd)

    # 解析格式获取小数位数和总长度
    decimal_places, total_length = parse_format(format_str)

    # 若总长度不足，往前补 0
    if len(digits) < total_length:
        digits = "0" * (total_length - len(digits)) + digits

    # 分离整数部分和小数部分
    integer_part = digits[: len(digits) - decimal_places]
    decimal_part = digits[len(digits) - decimal_places :]

    # 重新组合并插入小数点
    value_str = integer_part + "." + decimal_part

    # 解析为浮点数
    value = float(value_str)
    if is_negative:
        value = -value
    return value


def datetime_to_bcd(t: datetime) -> bytearray:
    """将时间转换为BCD码字节数组（小端序）"""
    # 获取当前时间（年月日时分）
    year = t.year % 100  # 取年份后两位（如2025→25）
    month = t.month  # 月份（1-12）
    day = t.day  # 日（1-31）
    hour = t.hour  # 时（0-23）
    minute = t.minute  # 分（0-59）

    # 组合为BCD格式：YYMMDDHHmm（每个字段占1字节BCD码）
    time_bcd = bytearray(
        [
            uint8_to_bcd(year),  # 年（后两位）
            uint8_to_bcd(month),  # 月
            uint8_to_bcd(day),  # 日
            uint8_to_bcd(hour),  # 时
            uint8_to_bcd(minute),  # 分
        ]
    )
    return reverse_bytes(time_bcd)


def bcd_to_byte(b: int) -> int:
    """将一个字节的BCD码转换为对应的整数"""
    return ((b >> 4) * 10) + (b & 0x0F)


def bcd_to_time(bcd: Union[bytearray, bytes]) -> datetime:
    """将BCD码字节数组转换为时间"""
    if len(bcd) < 5:  # 至少需要5字节（YY MM DD HH mm）
        raise ValueError("invalid BCD length")

    year = bcd_to_byte(bcd[0]) + 2000  # 假设为21世纪年份
    month = bcd_to_byte(bcd[1])
    day = bcd_to_byte(bcd[2])
    hour = bcd_to_byte(bcd[3])
    minute = bcd_to_byte(bcd[4])

    # 直接构造datetime对象
    return datetime(year, month, day, hour, minute)


# 辅助函数
def uint8_to_bcd(n: int) -> int:
    """将0-99的整数转换为BCD码"""
    if n < 0 or n > 99:
        raise ValueError("Number must be between 0 and 99")
    return ((n // 10) << 4) | (n % 10)


def reverse_bytes(data: Union[bytearray, bytes]) -> bytearray:
    """反转字节数组"""
    return bytearray(reversed(data))
