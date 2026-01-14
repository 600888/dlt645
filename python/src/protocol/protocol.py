"""
DLT645 协议实现模块。

本模块实现了 DLT645 协议的核心功能，包括：
- 数据域编码/解码（±0x33H 转换）
- 校验和计算
- 帧构建和解析
"""

from typing import Optional

from .frame import FRAME_START_BYTE, FRAME_END_BYTE, Frame
from .log import log


class DLT645Protocol:
    """
    DLT645 协议实现类。

    该类实现了 DLT645 协议的核心功能，包括数据编码/解码、校验和计算、
    帧构建和解析等操作。所有方法均为类方法，可直接调用。
    """

    @classmethod
    def decode_data(cls, data: bytes) -> bytes:
        """
        数据域解码（-0x33H 转换）。

        按照 DLT645 协议规定，对数据域进行解码处理，
        每个字节减去 0x33H，并使用模 256 运算确保结果在 0-255 范围内。

        :param data: 需要解码的数据字节。
        :type data: bytes
        :return: 解码后的原始数据。
        :rtype: bytes
        """
        if not data:
            return b""
        # 使用模256运算确保结果在0-255范围内，防止出现负数
        return bytes([(b - 0x33) % 256 for b in data])

    @classmethod
    def calculate_checksum(cls, data: bytes) -> int:
        """
        校验和计算（模 256 求和）。

        按照 DLT645 协议规定，计算数据的校验和，
        对所有字节进行累加，然后对结果取模 256。

        :param data: 需要计算校验和的数据字节。
        :type data: bytes
        :return: 计算得到的校验和值（0-255 范围）。
        :rtype: int
        """
        return sum(data) % 256

    @classmethod
    def encode_data(cls, data: bytes) -> bytes:
        """
        数据域编码（+0x33H 转换）。

        按照 DLT645 协议规定，对数据域进行编码处理，
        每个字节加上 0x33H，并使用模 256 运算确保结果在 0-255 范围内。

        :param data: 需要编码的原始数据字节。
        :type data: bytes
        :return: 编码后的数据。
        :rtype: bytes
        """
        if not data:
            return b""
        # 使用模256运算确保结果在0-255范围内，防止溢出
        return bytes([(b + 0x33) % 256 for b in data])

    @classmethod
    def build_frame(
        cls, addr: bytes, ctrl_code: int, data: bytes
    ) -> bytearray:
        """
        构建 DLT645 协议帧。

        按照 DLT645 协议规定，构建完整的协议帧，包括前导字节、
        地址域、控制码、数据域、校验和和结束标志。

        :param addr: 设备地址（6字节）。
        :type addr: bytes
        :param ctrl_code: 控制码。
        :type ctrl_code: int
        :param data: 原始数据域（未编码）。
        :type data: bytes
        :return: 完整的 DLT645 协议帧。
        :rtype: bytearray
        :raises ValueError: 当地址长度不为6字节时抛出。
        """
        if len(addr) != 6:
            raise ValueError("地址长度必须为6字节")

        buf = []
        buf.append(FRAME_START_BYTE)
        buf.extend(addr)
        buf.append(FRAME_START_BYTE)
        buf.append(ctrl_code)

        # 数据域编码
        encoded_data = DLT645Protocol.encode_data(data)
        buf.append(len(encoded_data))
        buf.extend(encoded_data)

        # 计算校验和
        check_sum = DLT645Protocol.calculate_checksum(bytes(buf))
        buf.append(check_sum)
        buf.append(FRAME_END_BYTE)

        # 前导字节添加
        preamble = [0xFE, 0xFE, 0xFE, 0xFE]
        buf = preamble + buf
        return bytearray(buf)

    @classmethod
    def deserialize(cls, raw: bytes) -> Optional[Frame]:
        """
        将字节数据反序列化为 Frame 对象。

        从原始字节数据中解析出 DLT645 协议帧。如果无法找到完整的帧，
        则抛出异常。

        :param raw: 输入的原始字节数据。
        :type raw: bytes
        :return: 解析出的 Frame 对象。
        :rtype: Optional[Frame]
        :raises Exception: 当无法找到完整帧时抛出。
        """
        remaining, frame = cls.deserialize_with_remaining(raw)
        if frame is None:
            raise Exception("No complete frame found")
        return frame

    @classmethod
    def deserialize_with_remaining(cls, raw: bytes) -> tuple[bytes, Optional[Frame]]:
        """
        将字节数据反序列化为 Frame 对象，并返回未解析的剩余数据。

        从原始字节数据中解析出 DLT645 协议帧，并返回未解析的剩余数据。
        如果数据不完整或无法解析，返回 (原始数据, None)。

        :param raw: 输入的原始字节数据。
        :type raw: bytes
        :return: 元组 (未解析的剩余数据, 解析出的帧)。
                 如果数据不完整或无法解析，返回 (原始数据, None)。
        :rtype: tuple[bytes, Optional[Frame]]
        """
        # 基础校验 - 不完整的数据不会抛出异常，而是返回None
        if len(raw) < 12:
            return raw, None

        # 帧边界检查（需考虑前导FE）
        try:
            start_idx = raw.index(FRAME_START_BYTE)
        except ValueError:
            # 未找到起始标志，返回原始数据
            return raw, None

        # 检查是否有足够的数据解析基本帧结构
        if start_idx + 10 >= len(raw):
            # 数据不完整，返回原始数据
            return raw, None

        if start_idx + 7 >= len(raw) or raw[start_idx + 7] != FRAME_START_BYTE:
            # 缺少第二个起始标志，可能是数据不完整或损坏
            # 跳过当前起始标志，尝试查找下一个
            return raw[start_idx + 1 :], None

        # 构建帧结构
        frame = Frame()
        frame.start_flag = raw[start_idx]
        frame.addr = raw[start_idx + 1 : start_idx + 7]
        frame.ctrl_code = raw[start_idx + 8]
        frame.data_len = raw[start_idx + 9]

        # 数据域提取（严格按协议1.2.5节处理）
        data_start = start_idx + 10
        data_end = data_start + frame.data_len

        # 检查是否有足够的数据解析完整帧
        if data_end + 2 > len(raw):  # 至少需要校验和和结束符
            # 数据不完整，返回原始数据
            return raw, None

        # 数据域解码（需处理加33H/减33H）
        frame.data = DLT645Protocol.decode_data(raw[data_start:data_end])

        # 校验和验证（从第一个68H到校验码前）
        checksum_start = start_idx
        checksum_end = data_end

        calculated_sum = DLT645Protocol.calculate_checksum(
            raw[checksum_start:checksum_end]
        )

        if calculated_sum != raw[checksum_end]:
            # 校验和错误，跳过当前起始标志，尝试查找下一个
            log.warning(f"Checksum error, skipping frame starting at index {start_idx}")
            return raw[start_idx + 1 :], None
        frame.checksum = raw[checksum_end]

        # 结束符验证
        if raw[checksum_end + 1] != FRAME_END_BYTE:
            # 结束符错误，跳过当前起始标志，尝试查找下一个
            log.warning(f"End flag error, skipping frame starting at index {start_idx}")
            return raw[start_idx + 1 :], None
        frame.end_flag = raw[checksum_end + 1]

        # 解析成功，计算剩余数据
        remaining_data = raw[checksum_end + 2 :]

        # 转换为带缩进的JSON
        log.debug(f"frame: {frame}")
        return remaining_data, frame

    @classmethod
    def serialize(cls, frame: Frame) -> Optional[bytes]:
        """
        将 Frame 对象序列化为字节数据。

        按照 DLT645 协议规定，将 Frame 对象序列化为完整的协议帧字节。

        :param frame: 需要序列化的 Frame 对象。
        :type frame: Frame
        :return: 序列化后的协议帧字节。
        :rtype: Optional[bytes]
        :raises Exception: 当起始或结束标志无效时抛出。
        """
        if frame.start_flag != FRAME_START_BYTE or frame.end_flag != FRAME_END_BYTE:
            log.error(f"invalid start or end flag: {frame.start_flag} {frame.end_flag}")
            raise Exception(
                f"invalid start or end flag: {frame.start_flag} {frame.end_flag}"
            )

        buf = []
        # 写入前导字节
        buf.extend(frame.preamble)
        # 写入起始符
        buf.append(frame.start_flag)
        # 写入地址
        buf.extend(frame.addr)
        # 写入第二个起始符
        buf.append(frame.start_flag)
        # 写入控制码
        buf.append(frame.ctrl_code)
        # 数据域编码
        encoded_data = DLT645Protocol.encode_data(frame.data)
        # 写入数据长度
        buf.append(len(encoded_data))
        # 写入编码后的数据
        buf.extend(encoded_data)
        # 计算并写入校验和
        check_sum = DLT645Protocol.calculate_checksum(bytearray(buf))
        buf.append(check_sum)
        # 写入结束符
        buf.append(frame.end_flag)

        return bytearray(buf)
