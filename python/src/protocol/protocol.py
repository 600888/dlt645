from typing import Optional

from .frame import FRAME_START_BYTE, FRAME_END_BYTE, Frame
from .log import log


class DLT645Protocol:
    @classmethod
    def decode_data(cls, data: bytes) -> bytes:
        """数据域解码（±33H转换）"""
        return bytes([b - 0x33 for b in data])

    @classmethod
    def calculate_checksum(cls, data: bytes) -> int:
        """校验和计算（模256求和）"""
        return sum(data) % 256

    @classmethod
    def encode_data(cls, data: bytes) -> bytes:
        """数据域编码"""
        return bytes([b + 0x33 for b in data])

    @classmethod
    def build_frame(cls, addr: bytes, ctrl_code: int, data: bytes) -> bytearray:
        """帧构建（支持广播和单播）"""
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

        return bytearray(buf)

    @classmethod
    def deserialize(cls, raw: bytes) -> Optional[Frame]:
        """将字节切片反序列化为 Frame 结构体"""
        # 基础校验
        if len(raw) < 12:
            raise Exception(f"frame too short: {raw}")

        # 帧边界检查（需考虑前导FE）
        try:
            start_idx = raw.index(FRAME_START_BYTE)
        except ValueError:
            log.error(f"invalid start flag: {raw}")
            raise Exception("invalid start flag")

        if start_idx == -1 or start_idx + 10 >= len(raw):
            log.error(f"invalid start flag: {raw}")
            raise Exception("invalid start flag")
        if start_idx + 7 >= len(raw) or raw[start_idx + 7] != FRAME_START_BYTE:
            log.error(f"missing second start flag: {raw}")
            raise Exception("missing second start flag")

        # 构建帧结构
        frame = Frame()
        frame.start_flag = raw[start_idx]
        frame.addr = raw[start_idx + 1:start_idx + 7]
        frame.ctrl_code = raw[start_idx + 8]
        frame.data_len = raw[start_idx + 9]

        # 数据域提取（严格按协议1.2.5节处理）
        data_start = start_idx + 10
        data_end = data_start + frame.data_len
        if data_end > len(raw) - 2:
            log.error(f"invalid data length {frame.data_len}")
            raise Exception(f"invalid data length {frame.data_len}")

        # 数据域解码（需处理加33H/减33H）
        frame.data = DLT645Protocol.decode_data(raw[data_start:data_end])

        # 校验和验证（从第一个68H到校验码前）
        checksum_start = start_idx
        checksum_end = data_end
        if checksum_end >= len(raw):
            log.error(f"frame truncated: {raw}")
            raise Exception(f"frame truncated: {raw}")

        calculated_sum = DLT645Protocol.calculate_checksum(raw[checksum_start:checksum_end])
        if calculated_sum != raw[checksum_end]:
            log.error(f"checksum error: calc=0x{calculated_sum:02X}, actual=0x{raw[checksum_end]:02X}")
            raise Exception(f"checksum error: calc=0x{calculated_sum:02X}, actual=0x{raw[checksum_end]:02X}")

        # 结束符验证
        if checksum_end + 1 >= len(raw) or raw[checksum_end + 1] != FRAME_END_BYTE:
            log.error(f"invalid end flag: {raw[checksum_end + 1]}")
            raise Exception(f"invalid end flag: {raw[checksum_end + 1]}")

        # 转换为带缩进的JSON
        log.info(f"frame: {frame}")
        return frame

    @classmethod
    def serialize(cls, frame: Frame) -> Optional[bytes]:
        """将 Frame 结构体序列化为字节切片"""
        if frame.start_flag != FRAME_START_BYTE or frame.end_flag != FRAME_END_BYTE:
            log.error(f"invalid start or end flag: {frame.start_flag} {frame.end_flag}")
            raise Exception(f"invalid start or end flag: {frame.start_flag} {frame.end_flag}")

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
