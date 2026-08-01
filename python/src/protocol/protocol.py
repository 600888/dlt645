"""DL/T 645-2007 数据帧编码、校验与流式解析。"""

from typing import Optional

from .frame import FRAME_END_BYTE, FRAME_START_BYTE, Frame
from .log import log


class DLT645Protocol:
    """无状态的 DL/T 645 帧编解码器。"""

    MAX_DATA_LENGTH = 0xFF
    MAX_PREAMBLE_LENGTH = 4
    MIN_FRAME_LENGTH = 12

    @classmethod
    def decode_data(cls, data: bytes) -> bytes:
        """移除数据域逐字节增加的 ``0x33`` 偏移。"""
        return bytes((value - 0x33) & 0xFF for value in data)

    @classmethod
    def encode_data(cls, data: bytes) -> bytes:
        """按协议为数据域逐字节增加 ``0x33`` 偏移。"""
        return bytes((value + 0x33) & 0xFF for value in data)

    @classmethod
    def calculate_checksum(cls, data: bytes) -> int:
        """计算从第一个 ``0x68`` 到数据域末尾的模 256 累加和。"""
        return sum(data) & 0xFF

    @classmethod
    def build_frame(
        cls,
        addr: bytes,
        ctrl_code: int,
        data: Optional[bytes],
        preamble_count: int = 4,
    ) -> bytearray:
        """从解码后的地址、控制码和数据域构建完整帧。"""
        data = data or b""
        if len(addr) != 6:
            raise ValueError("地址长度必须为6字节")
        if not 0 <= ctrl_code <= 0xFF:
            raise ValueError("控制码必须在0~255范围内")
        if len(data) > cls.MAX_DATA_LENGTH:
            raise ValueError("数据域长度不能超过255字节")
        if not 0 <= preamble_count <= cls.MAX_PREAMBLE_LENGTH:
            raise ValueError("前导字节数量必须在0~4范围内")

        frame = Frame(
            preamble=bytes([0xFE] * preamble_count),
            start_flag=FRAME_START_BYTE,
            addr=addr,
            ctrl_code=ctrl_code,
            data_len=len(data),
            data=data,
            end_flag=FRAME_END_BYTE,
        )
        return bytearray(cls.serialize(frame))

    @classmethod
    def deserialize(cls, raw: bytes) -> Optional[Frame]:
        """解析第一帧；数据不完整或没有合法帧时抛出 ``ValueError``。"""
        _, frame = cls.deserialize_with_remaining(raw)
        if frame is None:
            raise ValueError("No complete frame found")
        return frame

    @staticmethod
    def _trailing_preamble(raw: bytes) -> bytes:
        count = len(raw) - len(raw.rstrip(b"\xFE"))
        if not count:
            return b""
        return raw[-min(count, DLT645Protocol.MAX_PREAMBLE_LENGTH) :]

    @classmethod
    def _candidate_start(cls, raw: bytes, start_idx: int) -> int:
        """返回候选帧前连续前导码的起始位置。"""
        candidate_start = start_idx
        while (
            candidate_start > 0
            and start_idx - candidate_start < cls.MAX_PREAMBLE_LENGTH
            and raw[candidate_start - 1] == 0xFE
        ):
            candidate_start -= 1
        return candidate_start

    @classmethod
    def deserialize_with_remaining(cls, raw: bytes) -> tuple[bytes, Optional[Frame]]:
        """从字节流中解析一帧，并返回帧后的剩余数据。

        无效噪声和损坏帧会被丢弃；不完整帧会从首个有效候选 ``0x68``
        起保留，供下一批数据继续拼接。
        """
        raw = bytes(raw)
        search_from = 0

        while True:
            start_idx = raw.find(bytes([FRAME_START_BYTE]), search_from)
            if start_idx < 0:
                return cls._trailing_preamble(raw), None

            # 固定头部尚未收齐，必须保留候选帧。
            if len(raw) < start_idx + 10:
                return raw[cls._candidate_start(raw, start_idx) :], None

            # 第二个起始符位置不匹配，当前 0x68 只是噪声或地址内容。
            if raw[start_idx + 7] != FRAME_START_BYTE:
                search_from = start_idx + 1
                continue

            data_len = raw[start_idx + 9]
            data_start = start_idx + 10
            checksum_idx = data_start + data_len
            frame_end = checksum_idx + 2
            if len(raw) < frame_end:
                return raw[cls._candidate_start(raw, start_idx) :], None

            expected_checksum = cls.calculate_checksum(raw[start_idx:checksum_idx])
            if raw[checksum_idx] != expected_checksum:
                log.warning(
                    f"Checksum error, skipping frame starting at index {start_idx}"
                )
                search_from = start_idx + 1
                continue
            if raw[checksum_idx + 1] != FRAME_END_BYTE:
                log.warning(
                    f"End flag error, skipping frame starting at index {start_idx}"
                )
                search_from = start_idx + 1
                continue

            preamble_start = cls._candidate_start(raw, start_idx)

            frame = Frame(
                preamble=raw[preamble_start:start_idx],
                start_flag=FRAME_START_BYTE,
                addr=raw[start_idx + 1 : start_idx + 7],
                ctrl_code=raw[start_idx + 8],
                data_len=data_len,
                data=cls.decode_data(raw[data_start:checksum_idx]),
                check_sum=raw[checksum_idx],
                end_flag=FRAME_END_BYTE,
            )
            log.debug(f"frame: {frame}")
            return raw[frame_end:], frame

    @classmethod
    def serialize(cls, frame: Frame) -> bytes:
        """序列化帧；前导 ``0xFE`` 不参与校验和计算。"""
        if frame.start_flag != FRAME_START_BYTE or frame.end_flag != FRAME_END_BYTE:
            raise ValueError(
                f"invalid start or end flag: {frame.start_flag} {frame.end_flag}"
            )
        if len(frame.addr) != 6:
            raise ValueError("地址长度必须为6字节")
        if not 0 <= frame.ctrl_code <= 0xFF:
            raise ValueError("控制码必须在0~255范围内")
        if len(frame.preamble) > cls.MAX_PREAMBLE_LENGTH or any(
            value != 0xFE for value in frame.preamble
        ):
            raise ValueError("前导字节必须是0~4个0xFE")

        encoded_data = cls.encode_data(bytes(frame.data))
        if len(encoded_data) > cls.MAX_DATA_LENGTH:
            raise ValueError("数据域长度不能超过255字节")

        body = bytearray([FRAME_START_BYTE])
        body.extend(frame.addr)
        body.append(FRAME_START_BYTE)
        body.append(frame.ctrl_code)
        body.append(len(encoded_data))
        body.extend(encoded_data)

        checksum = cls.calculate_checksum(bytes(body))
        body.extend((checksum, FRAME_END_BYTE))
        frame.data_len = len(frame.data)
        frame.check_sum = checksum
        return bytes(frame.preamble) + bytes(body)
