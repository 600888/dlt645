from typing import List

# 常量定义
FRAME_START_BYTE = 0x68
FRAME_END_BYTE = 0x16
BROADCAST_ADDR = 0xAA

class Frame:
    def __init__(self, preamble: List[int] = [], start_flag: int = 0, addr: List[int] = [],
                 ctrl_code: int = 0, data_len: int = 0, data: List[int] = [],
                 check_sum: int = 0, end_flag: int = 0):
        self.preamble = preamble if preamble is not None else []
        self.start_flag = start_flag
        self.addr = addr if addr is not None else [0] * 6
        self.ctrl_code = ctrl_code
        self.data_len = data_len
        self.data = data if data is not None else []
        self.check_sum = check_sum
        self.end_flag = end_flag

    def __repr__(self):
        return (f"Frame(preamble={self.preamble}, start_flag=0x{self.start_flag:02X}, "
                f"addr={[hex(x) for x in self.addr]}, ctrl_code=0x{self.ctrl_code:02X}, "
                f"data_len={self.data_len}, data={[hex(x) for x in self.data]}, "
                f"check_sum=0x{self.check_sum:02X}, end_flag=0x{self.end_flag:02X})" )