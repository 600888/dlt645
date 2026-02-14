"""DLT645 协议帧结构模块。

本模块定义了 DLT645 协议帧的数据结构和相关常量。
"""

from typing import List
import struct
from ..model.data.define import DIMap
from ..model.types.dlt645_type import CtrlCode, ErrorCode, get_error_msg

#: 帧起始字节
FRAME_START_BYTE = 0x68
#: 帧结束字节
FRAME_END_BYTE = 0x16
#: 广播地址
BROADCAST_ADDR = 0xAA


class Frame:
    """DLT645 协议帧结构类。

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
        """初始化 Frame 实例。

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
        """返回 Frame 的字符串表示。

        :return: 格式化的帧信息字符串。
        :rtype: str
        """
        return (
            f"Frame(preamble={self.preamble}, start_flag=0x{self.start_flag:02X}, "
            f"addr={[hex(x) for x in self.addr]}, ctrl_code=0x{self.ctrl_code:02X}, "
            f"data_len={self.data_len}, data={[hex(x) for x in self.data]}, "
            f"check_sum=0x{self.check_sum:02X}, end_flag=0x{self.end_flag:02X})"
        )

    @property
    def description(self) -> str:
        """获取帧的描述信息。

        解析控制码和数据标识，返回易读的操作描述。

        :return: 描述字符串。
        :rtype: str
        """
        try:
            # 检查是否为错误响应 (最高两位为 11)
            if (self.ctrl_code & 0xC0) == 0xC0:
                original_ctrl = self.ctrl_code & 0x1F
                err_code_val = self.data[0] if self.data else 0
                err_msg = []
                for err in ErrorCode:
                    if err_code_val & err.value:
                        err_msg.append(get_error_msg(err))
                err_str = " | ".join(err_msg) if err_msg else f"未知错误(0x{err_code_val:02X})"
                
                op_name = "未知操作"
                if original_ctrl == CtrlCode.ReadData:
                    op_name = "读取数据"
                elif original_ctrl == CtrlCode.ReadAddress:
                    op_name = "读取通信地址"
                elif original_ctrl == CtrlCode.WriteData:
                    op_name = "写入数据"
                elif original_ctrl == CtrlCode.WriteAddress:
                    op_name = "写入通信地址"
                elif original_ctrl == CtrlCode.FreezeCmd:
                    op_name = "冻结命令"
                elif original_ctrl == CtrlCode.ChangeBaudRate:
                    op_name = "修改波特率"
                elif original_ctrl == CtrlCode.ChangePassword:
                    op_name = "修改密码"
                elif original_ctrl == CtrlCode.ClearDemand:
                    op_name = "需量清零"
                
                return f"{op_name}失败响应: {err_str}"

            is_response = (self.ctrl_code & 0x80) == 0x80
            func_code = self.ctrl_code & 0x7F  # 去除响应标志

            if func_code == CtrlCode.BroadcastTimeSync:
                return "广播校时"
            
            elif func_code == CtrlCode.ReadData:
                if len(self.data) < 4:
                    return "读取数据(数据长度不足)"
                
                # 提取 DI (前4字节)
                di_bytes = self.data[:4]
                # DLT645 DI 是小端序存储
                di_val = struct.unpack("<I", di_bytes)[0]
                
                # 查找数据项定义
                item = DIMap.get(di_val)
                name = item.name if item else "未知数据项"
                
                if is_response:
                    return f"读取{name}响应(DI={di_val:08X})"
                else:
                    return f"读取{name}(DI={di_val:08X})"

            elif func_code == CtrlCode.ReadAddress:
                if is_response:
                    addr_str = "".join([f"{b:02X}" for b in reversed(self.data[:6])])
                    return f"读取通信地址响应: {addr_str}"
                return "读取通信地址"

            elif func_code == CtrlCode.WriteData:
                if len(self.data) < 4:
                    return "写入数据(数据长度不足)"
                
                di_bytes = self.data[:4]
                di_val = struct.unpack("<I", di_bytes)[0]
                
                item = DIMap.get(di_val)
                name = item.name if item else "未知数据项"
                
                if is_response:
                    return f"写入{name}响应(DI={di_val:08X})"
                else:
                    return f"写入{name}(DI={di_val:08X})"

            elif func_code == CtrlCode.WriteAddress:
                if is_response:
                    return "写入通信地址响应"
                return "写入通信地址"
            
            elif func_code == CtrlCode.FreezeCmd:
                if len(self.data) < 4:
                     return "冻结命令(数据长度不足)"
                
                di_bytes = self.data[:4]
                di_val = struct.unpack("<I", di_bytes)[0]
                if is_response:
                     return f"冻结命令响应(DI={di_val:08X})"
                return f"冻结命令(DI={di_val:08X})"

            elif func_code == CtrlCode.ChangeBaudRate:
                 if is_response:
                    return "修改通信速率响应"
                 return "修改通信速率"
            
            elif func_code == CtrlCode.ChangePassword:
                if is_response:
                    return "修改密码响应"
                return "修改密码"
            
            elif func_code == CtrlCode.ClearDemand:
                if is_response:
                    return "需量清零响应"
                return "需量清零"

            return f"未知控制码(0x{self.ctrl_code:02X})"

        except Exception as e:
            return f"解析描述失败: {str(e)}"