from .types.dlt645_type import CtrlCode, PASSWORD_LEN


def validate_device(address: bytearray, ctrl_code: CtrlCode, addr: bytes) -> bool:
    """验证设备地址"""
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
