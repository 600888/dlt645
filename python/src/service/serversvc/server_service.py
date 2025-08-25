import struct
from typing import Union
import time

from src.common.transform import bytes_to_spaced_hex, float_to_bcd, time_to_bcd
from src.model.data.data_handler import set_data_item, get_data_item
from src.model.types.dlt645_type import CtrlCode, Demand
from src.protocol.protocol import DLT645Protocol
from src.protocol.log import log
from src.model.data import data_handler as data
from src.transport.server.rtu_server import RtuServer
from src.transport.server.tcp_server import TcpServer


class MeterServerService:
    def __init__(self, server: Union[TcpServer, RtuServer], address: bytearray = None, password=None):
        self.server = server
        if address is None:
            self.address = bytearray([0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        else:
            self.address = address
        if password is None:
            self.password = bytearray([0x00, 0x00, 0x00, 0x00])
        else:
            self.password = bytearray(password)

    def register_device(self, addr: bytearray):
        """
        设备注册
        :param addr:
        :return:
        """
        self.address = addr

    def validate_device(self, address: bytearray) -> bool:
        """
        验证设备地址
        :param address:
        :return:
        """
        if address == [0xAA] * 6:  # 读通讯地址命令
            return True
        if address == [0x99] * 6:  # 广播时间同步命令
            return True
        # 验证设备地址是否匹配
        log.info(f"address:{self.address}, received_address:{address}")
        return address == self.address

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

    def set_password(self, password: bytearray) -> None:
        """
        写密码
        :param password:
        :return:
        """
        if len(password) != 4:
            raise ValueError("invalid password length")
        self.password = password
        log.info(f"设置密码: {self.password}")

    def handle_request(self, frame):
        """
        处理读数据请求
        :param frame:
        :return:
        """
        # 1. 验证设备
        if not self.validate_device(frame.addr):
            log.info(f"验证设备地址: {bytes_to_spaced_hex(frame.addr)} 失败")
            raise Exception("unauthorized device")

        # 2. 根据控制码判断请求类型
        if frame.ctrl_code == CtrlCode.BroadcastTimeSync:  # 广播校时
            log.info(f"广播校时: {frame.Data.hex(' ')}")
            self.set_time(frame.Data)
            return DLT645Protocol.build_frame(frame.addr, frame.ctrl_code | 0x80, frame.data)
        elif frame.ctrl_code == CtrlCode.ReadData:
            # 解析数据标识
            di = frame.data
            di3 = di[3]
            if di3 == 0x00:  # 读取电能
                # 构建响应帧
                res_data = bytearray(8)
                # 解析数据标识为 32 位无符号整数
                data_id = struct.unpack("<I", frame.data[:4])[0]
                data_item = data.get_data_item(data_id)
                if data_item is None:
                    raise Exception("data item not found")
                res_data[:4] = frame.data[:4]  # 仅复制前 4 字节数据标识
                value = data_item.value
                # 转换为 BCD 码
                bcd_value = float_to_bcd(value, data_item.data_format, 'little')
                res_data[4:] = bcd_value
                return DLT645Protocol.build_frame(frame.addr, frame.ctrl_code | 0x80, bytes(res_data))
            elif di3 == 0x01:  # 读取最大需量及发生时间
                res_data = bytearray(12)
                data_id = struct.unpack("<I", frame.data[:4])[0]
                data_item = data.get_data_item(data_id)
                if data_item is None:
                    raise Exception("data item not found")
                res_data[:4] = frame.data[:4]  # 返回数据标识
                value = data_item.value
                # 转换为 BCD 码
                bcd_value = float_to_bcd(value, data_item.data_format, 'little')
                res_data[4:7] = bcd_value[:3]
                # 需量发生时间
                res_data[7:12] = time_to_bcd(time.time())
                log.info(f"读取最大需量及发生时间: {res_data}")
                return DLT645Protocol.build_frame(frame.addr, frame.ctrl_code | 0x80, bytes(res_data))
            elif di3 == 0x02:  # 读变量
                data_id = struct.unpack("<I", frame.data[:4])[0]
                data_item = data.get_data_item(data_id)
                if data_item is None:
                    raise Exception("data item not found")
                # 变量数据长度
                data_len = 4
                data_len += (len(data_item.data_format) - 1) // 2  # (数据格式长度 - 1 位小数点)/2
                # 构建响应帧
                res_data = bytearray(data_len)
                res_data[:4] = frame.data[:4]  # 仅复制前 4 字节
                value = data_item.value
                # 转换为 BCD 码（小端序）
                bcd_value = float_to_bcd(value, data_item.data_format, 'little')
                res_data[4:data_len] = bcd_value
                return DLT645Protocol.build_frame(frame.addr, frame.ctrl_code | 0x80, bytes(res_data))
            else:
                log.info(f"unknown: {hex(di3)}")
                return Exception("unknown di3")
        elif frame.ctrl_code == CtrlCode.ReadAddress:
            # 构建响应帧
            res_data = self.address[:6]
            return DLT645Protocol.build_frame(self.address, frame.ctrl_code | 0x80, res_data)
        elif frame.ctrl_code == CtrlCode.WriteAddress:
            res_data = b''  # 写通讯地址不需要返回数据
            # 解析数据
            addr = frame.data[:6]
            self.set_address(addr)  # 设置通讯地址
            return DLT645Protocol.build_frame(self.address, frame.ctrl_code | 0x80, res_data)
        else:
            log.info(f"unknown control code: {hex(frame.ctrl_code)}")
            raise Exception("unknown control code")


def new_tcp_server(ip: str, port: int, timeout: int) -> MeterServerService:
    """
    创建 TCP 服务器
    :param ip: IP 地址
    :param port: 端口
    :param timeout: 超时时间
    :return:
    """
    # 1. 先创建 TcpServer（不依赖 Service）
    tcp_server = TcpServer(ip, port, timeout, None)

    # 2. 创建 MeterServerService，注入 TcpServer（作为 Server 接口）
    meter_service = MeterServerService(tcp_server)

    # 3. 将 MeterServerService 注入回 TcpServer
    tcp_server.service = meter_service
    return meter_service


def new_rtu_server(port: str, dataBits: int, stopBits: int, baudRate: int, parity: str,
                   timeout: float) -> MeterServerService:
    """
    创建 RTU 服务器
    :param port: 端口
    :param dataBits: 数据位
    :param stopBits: 停止位
    :param baudRate: 波特率
    :param parity: 校验位
    :param timeout: 超时时间
    :return:
    """
    # 1. 先创建 RtuServer（不依赖 Service）
    rtu_server = RtuServer(port, dataBits, stopBits, baudRate, parity, timeout)
    # 2. 创建 MeterServerService，注入 RtuServer（作为 Server 接口）
    meter_service = MeterServerService(rtu_server)
    # 3. 将 MeterServerService 注入回 RtuServer
    rtu_server.service = meter_service
    return meter_service
