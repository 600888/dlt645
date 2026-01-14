"""
DLT645 协议帧结构模块。

本模块定义了 DLT645 协议帧的数据结构和相关常量。
"""

from typing import List

#: 帧起始字节
FRAME_START_BYTE = 0x68
#: 帧结束字节
FRAME_END_BYTE = 0x16
#: 广播地址
BROADCAST_ADDR = 0xAA


class Frame:
    """
    DLT645 协议帧结构类。

    表示一个完整的 DLT645 协议数据帧。

    帧格式::

        前导码(FE) | 起始符(68H) | 地址域(6B) | 起始符(68H) | 控制码(1B) |
        数据长度(1B) | 数据域(NB) | 校验和(1B) | 结束符(16H)

    :ivar preamble: 前导字节（通常为 0xFE 0xFE 0xFE 0xFE）。
    :ivar start_flag: 起始标志（0x68）。
    :ivar addr: 地址域（6字节）。
    :ivar ctrl_code: 控制码。
    :ivar data_len: 数据域长度。
    :ivar data: 数据域内容（已解码）。
    :ivar check_sum: 校验和。
    :ivar end_flag: 结束标志（0x16）。
    """

    def __init__(
        self,
        preamble: bytearray = bytearray(),
        start_flag: int = 0,
        addr: bytearray = bytearray(),
        ctrl_code: int = 0,
        data_len: int = 0,
        data: bytearray = bytearray(),
        check_sum: int = 0,
        end_flag: int = 0,
    ):
        """
        初始化 Frame 实例。

        :param preamble: 前导字节，默认为空。
        :type preamble: bytearray
        :param start_flag: 起始标志，默认为 0。
        :type start_flag: int
        :param addr: 地址域，默认为空（将初始化为6个0）。
        :type addr: bytearray
        :param ctrl_code: 控制码，默认为 0。
        :type ctrl_code: int
        :param data_len: 数据域长度，默认为 0。
        :type data_len: int
        :param data: 数据域内容，默认为空。
        :type data: bytearray
        :param check_sum: 校验和，默认为 0。
        :type check_sum: int
        :param end_flag: 结束标志，默认为 0。
        :type end_flag: int
        """
        self.preamble = preamble if preamble is not None else bytearray()
        self.start_flag = start_flag
        self.addr = addr if addr is not None else bytearray([0] * 6)
        self.ctrl_code = ctrl_code
        self.data_len = data_len
        self.data = data if data is not None else bytearray()
        self.check_sum = check_sum
        self.end_flag = end_flag

    def __repr__(self):
        """
        返回 Frame 的字符串表示。

        :return: 格式化的帧信息字符串。
        :rtype: str
        """
        return (
            f"Frame(preamble={self.preamble}, start_flag=0x{self.start_flag:02X}, "
            f"addr={[hex(x) for x in self.addr]}, ctrl_code=0x{self.ctrl_code:02X}, "
            f"data_len={self.data_len}, data={[hex(x) for x in self.data]}, "
            f"check_sum=0x{self.check_sum:02X}, end_flag=0x{self.end_flag:02X})"
        )