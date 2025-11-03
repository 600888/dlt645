import struct
from typing import Optional, Union
from datetime import datetime
import struct

from ...common.transform import bytes_to_spaced_hex, float_to_bcd, datetime_to_bcd, string_to_bcd
from ...model.data.data_handler import set_data_item, get_data_item
from ...model.types.data_type import DataItem
from ...model.types.dlt645_type import DI_LEN, PASSWORD_LEN, ADDRESS_LEN, CtrlCode, Demand
from ...protocol.protocol import DLT645Protocol
from ...model.data import data_handler as data
from ...service.serversvc.log import log
from ...transport.server.rtu_server import RtuServer
from ...transport.server.tcp_server import TcpServer


class MeterServerService:
    def __init__(
        self,
        server: Union[TcpServer, RtuServer],
        address: Optional[bytearray] = bytearray([0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
        password: Optional[bytearray] = bytearray([0x00, 0x00, 0x00, 0x00]),
    ):
        self.server = server
        self.address = address
        self.password = password
            
    @classmethod
    def new_tcp_server(cls, ip: str, port: int, timeout: int = 300) -> "MeterServerService":
        """
        创建 TCP 服务器
        :param ip: IP 地址
        :param port: 端口
        :param timeout: 超时时间
        :return:
        """
        # 1. 先创建 TcpServer
        tcp_server = TcpServer(ip, port, timeout, None)
        # 2. 创建 MeterServerService，注入 TcpServer（作为 Server 接口）
        return cls.new_meter_server_service(tcp_server)

    @classmethod
    def new_rtu_server(
        cls, port: str, data_bits: int, stop_bits: int, baud_rate: int, parity: str, timeout: float
    ) -> "MeterServerService":
        """
        创建 RTU 服务器
        :param port: 端口
        :param data_bits: 数据位
        :param stop_bits: 停止位
        :param baud_rate: 波特率
        :param parity: 校验位
        :param timeout: 超时时间
        :return:
        """
        # 1. 先创建 RtuServer
        rtu_server = RtuServer(port, data_bits, stop_bits, baud_rate, parity, timeout)
        # 2. 创建 MeterServerService，注入 RtuServer（作为 Server 接口）
        return cls.new_meter_server_service(rtu_server)
    
    @classmethod
    def new_meter_server_service(cls, server: Union[TcpServer, RtuServer]) -> "MeterServerService":
        """
        创建新的MeterServerService实例
        :param server: 服务器实例（TCP或RTU）
        :return: MeterServerService实例
        """
        # 创建业务服务实例
        meter_service = cls(server)
        # 将服务实例注入回服务器
        server.service = meter_service
        return meter_service

    def register_device(self, addr: bytearray):
        """
        设备注册
        :param addr:
        :return:
        """
        self.address = addr

    def validate_device(self, ctrl_code: CtrlCode, addr: bytes) -> bool:
        """验证设备地址"""
        if ctrl_code == CtrlCode.ReadAddress | 0x80 or ctrl_code == CtrlCode.WriteAddress | 0x80:  # 读通讯地址命令
            return True
        # 广播地址和广播时间同步地址
        if addr == bytearray([0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA]) or addr == bytearray([0x99, 0x99, 0x99, 0x99, 0x99, 0x99]):
            return True
        return bytes(self.address) == addr

    # 设置时间，需根据实际情况实现
    def set_time(self, data_bytes):
        pass

    def set_address(self, address: bytearray):
        """
        写通讯地址
        :param address:
        :return:
        """
        if len(address) != 6:
            raise ValueError("invalid address length")
        self.address = address

    def set_00(self, di: int, value: float) -> bool:
        """
        写电能量
        :param di: 数据项
        :param value: 值
        :return:
        """
        ok = set_data_item(di, value)
        if not ok:
            log.error(f"写电能量失败")
        return ok

    def set_01(self, di: int, demand: Demand) -> bool:
        """
        写最大需量及发生时间
        :param di: 数据项
        :param demand: 值
        :return:
        """
        ok = set_data_item(di, demand)
        if not ok:
            log.error(f"写最大需量及发生时间失败")
        return ok

    def set_02(self, di: int, value: float) -> bool:
        """
        写变量
        :param di: 数据项
        :param value: 值
        :return:
        """
        dataItem = get_data_item(di)
        if dataItem is None:
            log.error(f"获取数据项失败")
            return False

        ok = set_data_item(di, value)
        if not ok:
            log.error(f"写变量失败")
            return False
        return ok
    
    def set_04(self, di: int, value: str) -> bool:
        """
        写参变量
        :param di: 数据项
        :param value: 值
        :return:
        """
        dataItem = get_data_item(di)
        if dataItem is None:
            log.error(f"获取数据项失败")
            return False
        
        ok = set_data_item(di, value)
        if not ok:
            log.error(f"写参变量失败")
        return ok

    def set_password(self, password: bytearray) -> None:
        """
        写密码
        :param password:
        :return:
        """
        if len(password) != PASSWORD_LEN:
            raise ValueError("invalid password length")
        self.password = password
        log.info(f"设置密码: {self.password}")
        
    def get_data_item(self, di: int) -> Optional[DataItem]:
        """
        获取数据项
        :param di: 数据项
        :return:
        """
        return get_data_item(di)

    def handle_request(self, frame):
        """
        处理读数据请求
        :param frame:
        :return:
        """
        # 1. 验证设备
        if not self.validate_device(frame.ctrl_code, frame.addr):
            log.info(f"验证设备地址: {bytes_to_spaced_hex(frame.addr)} 失败")
            raise Exception("unauthorized device")

        # 2. 根据控制码判断请求类型
        if frame.ctrl_code == CtrlCode.BroadcastTimeSync:  # 广播校时
            log.info(f"广播校时: {frame.Data.hex(' ')}")
            self.set_time(frame.Data)
            return DLT645Protocol.build_frame(
                frame.addr, frame.ctrl_code | 0x80, frame.data
            )
        elif frame.ctrl_code == CtrlCode.ReadData:
            # 解析数据标识
            di = frame.data
            di3 = di[3]
            if di3 == 0x00:  # 读取电能
                # 构建响应帧
                res_data = bytearray(8)
                # 解析数据标识为 32 位无符号整数
                data_id = struct.unpack("<I", frame.data[:DI_LEN])[0]
                data_item = data.get_data_item(data_id)
                if data_item is None:
                    raise Exception("data item not found")
                res_data[:DI_LEN] = frame.data[:DI_LEN]  # 仅复制前 4 字节数据标识
                value = data_item.value
                # 转换为 BCD 码
                bcd_value = float_to_bcd(value, data_item.data_format, "little")
                res_data[DI_LEN:] = bcd_value
                return DLT645Protocol.build_frame(
                    frame.addr, frame.ctrl_code | 0x80, bytes(res_data)
                )
            elif di3 == 0x01:  # 读取最大需量及发生时间
                res_data = bytearray(12)
                data_id = struct.unpack("<I", frame.data[:DI_LEN])[0]
                data_item = data.get_data_item(data_id)
                if data_item is None:
                    raise Exception("data item not found")
                res_data[:DI_LEN] = frame.data[:DI_LEN]  # 返回数据标识
                demand:Demand = data_item.value
                # 转换为 BCD 码
                bcd_value = float_to_bcd(demand.value, data_item.data_format, "little")
                res_data[DI_LEN:DI_LEN+3] = bcd_value[:3]
                # 需量发生时间
                res_data[DI_LEN+3:12] = datetime_to_bcd(demand.time)
                return DLT645Protocol.build_frame(
                    frame.addr, frame.ctrl_code | 0x80, bytes(res_data)
                )
            elif di3 == 0x02:  # 读变量
                data_id = struct.unpack("<I", frame.data[:DI_LEN])[0]
                data_item = data.get_data_item(data_id)
                if data_item is None:
                    raise Exception("data item not found")
                # 变量数据长度
                data_len = DI_LEN
                data_len += (
                    len(data_item.data_format) - 1
                ) // 2  # (数据格式长度 - 1 位小数点)/2
                # 构建响应帧
                res_data = bytearray(data_len)
                res_data[:DI_LEN] = frame.data[:DI_LEN]  # 仅复制前 DI_LEN 字节
                value = data_item.value
                # 转换为 BCD 码（小端序）
                bcd_value = float_to_bcd(value, data_item.data_format, "little")
                res_data[DI_LEN:data_len] = bcd_value
                return DLT645Protocol.build_frame(
                    frame.addr, frame.ctrl_code | 0x80, bytes(res_data)
                )
            elif di3 == 0x04:  # 读参变量
                data_id = struct.unpack("<I", frame.data[:DI_LEN])[0]
                data_item = data.get_data_item(data_id)
                if data_item is None:
                    raise Exception("data item not found")
                
                # 变量数据长度
                data_len = DI_LEN
                # 时段表数据
                if 0x04010000 <= int.from_bytes(di, byteorder='little') <=0x04020008:
                    res_data = bytearray(DI_LEN+14*2)
                    step = len(data_item.data_format) // 2
                    for i in range(0, 14):
                        data_len += step
                        res_data[:DI_LEN] = frame.data[:DI_LEN]  # 复制数据标识
                        value = data_item.value[i]
                        bcd_value = string_to_bcd(value, "little")
                        
                        # 扩展res_data以容纳BCD数据
                        res_data[DI_LEN+step*i:DI_LEN+step*(i+1)] = bcd_value
                    return DLT645Protocol.build_frame(
                        frame.addr, frame.ctrl_code | 0x80, bytes(res_data)
                    )
                else: 
                    # 根据数据格式确定数据长度
                    data_format = data_item.data_format
                    data_len += len(data_format) // 2
                    
                    # 构建响应帧
                    res_data = bytearray(data_len)
                    res_data[:DI_LEN] = frame.data[:DI_LEN]  # 复制数据标识
                    value = data_item.value
                    
                    bcd_value = string_to_bcd(value, "little")
                    
                    # 扩展res_data以容纳BCD数据
                    res_data[DI_LEN:DI_LEN+data_len] = bcd_value
                    
                    return DLT645Protocol.build_frame(
                        frame.addr, frame.ctrl_code | 0x80, bytes(res_data)
                    )
            else:
                log.info(f"unknown: {hex(di3)}")
                return Exception("unknown di3")
        elif frame.ctrl_code == CtrlCode.ReadAddress:
            # 构建响应帧
            res_data = self.address[:ADDRESS_LEN]
            return DLT645Protocol.build_frame(
                bytes(self.address), frame.ctrl_code | 0x80, bytes(res_data)
            )
        elif frame.ctrl_code == CtrlCode.WriteAddress:
            res_data = b""  # 写通讯地址不需要返回数据
            # 解析数据
            addr = frame.data[:ADDRESS_LEN]
            self.set_address(addr)  # 设置通讯地址
            return DLT645Protocol.build_frame(
                bytes(self.address), frame.ctrl_code | 0x80, res_data
            )
        else:
            log.info(f"unknown control code: {hex(frame.ctrl_code)}")
            raise Exception("unknown control code")
