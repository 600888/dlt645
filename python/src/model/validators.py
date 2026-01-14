"""设备验证模块。

本模块提供设备地址验证功能。
"""

from .types.dlt645_type import CtrlCode, PASSWORD_LEN


def validate_device(address: bytearray, ctrl_code: CtrlCode, addr: bytes) -> bool:
    """验证设备地址是否匹配。

    以下情况验证通过：
    1. 读/写通讯地址命令的响应帧（控制码带 0x80 应答标志）
    2. 广播地址（0xAA AA AA AA AA AA）
    3. 广播校时地址（0x99 99 99 99 99 99）
    4. 地址与预期地址完全匹配

    :param address: 预期的设备地址（6字节）。
    :type address: bytearray
    :param ctrl_code: 帧的控制码。
    :type ctrl_code: CtrlCode
    :param addr: 帧中的实际地址（6字节）。
    :type addr: bytes
    :return: 验证通过返回 True，否则返回 False。
    :rtype: bool
    """
    if (
        ctrl_code == CtrlCode.ReadAddress | 0x80
        or ctrl_code == CtrlCode.WriteAddress | 0x80
    ):  # 读通讯地址命令
        return True
    # 广播地址和广播时间同步地址
    if addr == bytearray([0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA]) or addr == bytearray(
        [0x99, 0x99, 0x99, 0x99, 0x99, 0x99]
    ):
        return True
    return address == addr

