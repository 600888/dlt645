from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import time
import struct
from typing import Optional, Union

from src.common.transform import (
    bcd_to_float,
    bcd_to_time,
    bytes_to_int,
    bytes_to_spaced_hex,
)
from src.model.types.data_type import DataFormat, DataItem
from src.model.types.dlt645_type import CtrlCode, Demand
from src.protocol.protocol import DLT645Protocol, Frame
from src.protocol.log import log
from src.model.data import data_handler as data
from src.transport.client.rtu_client import RtuClient
from src.transport.client.tcp_client import TcpClient


class MeterClientService:
    def __init__(self, client: Union[TcpClient, RtuClient]):
        self.address = bytearray(6)  # 6字节地址
        self.password = bytearray(4)  # 4字节密码
        self.client = client
        self._executor = ThreadPoolExecutor(max_workers=1)  # 用于超时控制

    @classmethod
    def new_tcp_client(
        cls, ip: str, port: int, timeout: float
    ) -> Optional["MeterClientService"]:
        """创建TCP客户端"""
        tcp_client = TcpClient(ip=ip, port=port, timeout=timeout)

        # 创建业务服务实例
        return cls.new_meter_client_service(tcp_client)

    @classmethod
    def new_rtu_client(
        cls,
        port: str,
        baudrate: int,
        databits: int,
        stopbits: int,
        parity: str,
        timeout: float,
    ) -> Optional["MeterClientService"]:
        """创建RTU客户端"""
        rtu_client = RtuClient(
            port=port,
            baud_rate=baudrate,
            data_bits=databits,
            stop_bits=stopbits,
            parity=parity,
            timeout=timeout,
        )

        # 创建业务服务实例
        return cls.new_meter_client_service(rtu_client)

    @classmethod
    def new_meter_client_service(
        cls, client: Union[TcpClient, RtuClient]
    ) -> Optional["MeterClientService"]:
        """创建新的MeterService实例"""
        if client is None:
            log.error("连接不能为None")
            return None

        service = cls(client)
        return service

    def get_time(self, t: bytes) -> datetime:
        """从字节数据获取时间"""
        timestamp = bytes_to_int(t)
        log.info("timestamp: %v", timestamp)
        return datetime.fromtimestamp(timestamp)

    def validate_device(self, addr: bytes) -> bool:
        """验证设备地址"""
        if addr == bytes([0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA]):  # 读通讯地址命令
            return True
        if addr == bytes([0x99, 0x99, 0x99, 0x99, 0x99, 0x99]):  # 广播时间同步命令
            return True
        return bytes(self.address) == addr

    def set_address(self, address: bytes) -> bool:
        """设置设备地址"""
        if len(address) != 6:
            log.error("无效的地址长度")
            return False

        self.address = bytearray(address)
        log.info("设置客户端通讯地址: %x", self.address)
        return True

    def set_password(self, password: bytes) -> bool:
        """设置设备密码"""
        if len(password) != 4:
            log.error("无效的密码长度")
            return False

        self.password = bytearray(password)
        log.info("设置客户端密码: %v", self.password)
        return True

    def read_01(self, di: int) -> Optional[DataItem]:
        """读取电能"""
        data_bytes = struct.pack("<I", di)  # 小端序
        frame_bytes = DLT645Protocol.build_frame(
            self.address, CtrlCode.ReadData, data_bytes
        )
        return self.send_and_handle_request(frame_bytes)

    def read_02(self, di: int) -> Optional[DataItem]:
        """读取最大需量及发生时间"""
        data_bytes = struct.pack("<I", di)  # 小端序
        frame_bytes = DLT645Protocol.build_frame(
            self.address, CtrlCode.ReadData, data_bytes
        )
        return self.send_and_handle_request(frame_bytes)

    def read_03(self, di: int) -> Optional[DataItem]:
        """读取变量"""
        data_bytes = struct.pack("<I", di)  # 小端序
        frame_bytes = DLT645Protocol.build_frame(
            self.address, CtrlCode.ReadData, data_bytes
        )
        return self.send_and_handle_request(frame_bytes)

    def read_address(self) -> Optional[DataItem]:
        """读取通讯地址"""
        frame_bytes = DLT645Protocol.build_frame(
            self.address, CtrlCode.ReadAddress, None
        )
        return self.send_and_handle_request(frame_bytes)

    def write_address(self, new_address: bytes) -> Optional[DataItem]:
        """写通讯地址"""
        if len(new_address) != 6:
            log.error("无效的新地址长度")
            return None

        frame_bytes = DLT645Protocol.build_frame(
            self.address, CtrlCode.WriteAddress, new_address
        )
        return self.send_and_handle_request(frame_bytes)

    def send_and_handle_request(
        self,
        frame_bytes: bytes,
    ) -> Optional[DataItem]:
        """发送请求并处理响应（带超时控制）

        Args:
            frame_bytes: 要发送的帧数据

        Returns:
            DataItem: 成功时返回数据项
            None: 超时或失败时返回
        """
        try:
            if self.client is None:
                log.error("连接未初始化")
                return None

            if not self.client.connect():
                log.error("连接失败")
                return None

            # 请求阶段超时控制
            response = self.client.send_request(frame_bytes)

            if response is None:
                return None

            # 解析阶段
            frame = DLT645Protocol.deserialize(response)
            if frame is None:
                log.error("解析响应失败")
                return None

            # 处理响应
            data_item = self.handle_response(frame)
            return data_item
        except Exception as e:
            log.error(f"未知错误: {str(e)}", exc_info=True)
            return None

    def handle_response(self, frame: Frame) -> Optional[DataItem]:
        """处理响应帧"""
        # 验证设备地址
        if not self.validate_device(frame.addr):
            log.warning("验证设备地址: %x 失败", bytes_to_spaced_hex(frame.addr))
            return None

        # 根据控制码判断响应类型
        if frame.ctrl_code == (CtrlCode.BroadcastTimeSync | 0x80):  # 广播校时响应
            log.info("广播校时响应: % x", frame.data)
            time_value = self.get_time(frame.data[0:4])
            data_item = data.get_data_item(bytes_to_int(frame.data[0:4]))
            if not data_item:
                log.warning("获取数据项失败")
                return None
            data_item.value = time_value
            return data_item

        elif frame.ctrl_code == (CtrlCode.ReadData | 0x80):  # 读数据响应
            # 解析数据标识
            if len(frame.data) < 4:
                log.warning("读数据响应数据长度无效")
                return None

            di = frame.data[0:4]
            di3 = di[3]

            if di3 == 0x00:  # 读取电能响应
                log.info(f"读取电能响应")
                data_item = data.get_data_item(bytes_to_int(di))
                if not data_item:
                    log.warning("获取数据项失败")
                    return None
                data_item.value = bcd_to_float(
                    frame.data[4:8], data_item.data_format, "little"
                )
                return data_item

            elif di3 == 0x01:  # 读取最大需量及发生时间响应
                log.info("读取最大需量及发生时间响应: % x", frame.data)
                data_item = data.get_data_item(bytes_to_int(di))
                if not data_item:
                    log.warning("获取数据项失败")
                    return None

                # 转换时间
                occur_time = bcd_to_time(frame.data[7:12])

                # 转换需量值
                demand_value = bcd_to_float(
                    frame.data[4:7], data_item.data_format, "little"
                )

                data_item.value = Demand(value=demand_value, occur_time=occur_time)
                return data_item

            elif di3 == 0x02:
                data_item = data.get_data_item(bytes_to_int(di))
                if not data_item:
                    log.warning("获取数据项失败")
                    return None
                data_item.value = bcd_to_float(
                    frame.data[4:8], data_item.data_format, "little"
                )
                return data_item
            else:
                log.warning("<UNK> %x <UNK>", di3)
                return None

        elif frame.ctrl_code == (CtrlCode.ReadAddress | 0x80):  # 读通讯地址响应
            log.info("读通讯地址响应: %v", frame.data)
            if len(frame.data) == 6:
                self.address = frame.data[:6]
            return DataItem(
                di=bytes_to_int(frame.data[0:4]),
                name="通讯地址",
                data_format=DataFormat.XXXXXXXX.value,
                value=frame.data,
                unit="",
                timestamp=datetime.now().timestamp(),
            )

        elif frame.ctrl_code == (CtrlCode.WriteAddress | 0x80):  # 写通讯地址响应
            log.info("写通讯地址响应: %v", frame.data)
            return DataItem(
                di=bytes_to_int(frame.data[0:4]),
                name="通讯地址",
                data_format=DataFormat.XXXXXXXX.value,
                value=frame.data,
                unit="",
                timestamp=datetime.now().timestamp(),
            )

        else:
            log.warning("<UNK> %x <UNK>", frame.ctrl_code)
            return None
