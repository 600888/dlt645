#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DLT645 新增功能回环测试（TCP）

覆盖按 DL/T645-2007 文档补充实现的命令：
- 广播校时（客户端发起，C=08H）
- 冻结命令（C=16H，含广播冻结）
- 更改通信速率（C=17H）
- 最大需量清零（C=19H）
- 电表清零（C=1AH）
- 事件清零（C=1BH）

通过本机 TCP server/client 回环验证请求-响应与数据清零效果。
"""

import os
import sys
import socket
import time
import unittest
from datetime import datetime

python_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, python_dir)

from dlt645.service.serversvc.server_service import MeterServerService
from dlt645.service.clientsvc.client_service import MeterClientService
from dlt645.model.types.dlt645_type import Demand


def get_free_port() -> int:
    """获取一个空闲 TCP 端口"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class TestNewCommands(unittest.TestCase):
    """新增命令回环测试"""

    @classmethod
    def setUpClass(cls):
        cls.port = get_free_port()
        cls.server = MeterServerService.new_tcp_server("127.0.0.1", cls.port, 5.0)
        # 服务端密码（04级用于最大需量清零，02级用于电表/事件清零）
        cls.server.set_password("04000000")
        cls.server.set_password("02000000")
        cls.server.server.start()

        cls.client = MeterClientService.new_tcp_client("127.0.0.1", cls.port, 5.0)
        cls.client.set_password("04000000")
        time.sleep(0.3)  # 等待连接建立

    @classmethod
    def tearDownClass(cls):
        try:
            cls.client.client.disconnect()
        except Exception:
            pass
        cls.server.server.stop()

    def test_broadcast_time_sync(self):
        """广播校时：发送后服务端时钟更新，且连接无残留影响后续通信"""
        dt = datetime(2026, 8, 1, 10, 30, 45)
        ok = self.client.broadcast_time_sync(dt)
        self.assertTrue(ok)
        time.sleep(0.3)
        self.assertEqual(self.server.time, dt)
        # 广播命令不应答，连接上不应有残留数据，后续读数据必须正常
        self.server.set_00(0x00000000, 999.99)
        item = self.client.read_00(0x00000000)
        self.assertIsNotNone(item)
        self.assertAlmostEqual(item.value, 999.99, places=2)

    def test_freeze(self):
        """普通冻结命令：收到 96H 应答，服务端记录冻结时间"""
        item = self.client.freeze(month=8, day=1, hour=10, minute=30)
        self.assertIsNotNone(item)
        self.assertEqual(item.name, "冻结命令")
        time.sleep(0.2)
        self.assertEqual(
            bytes(self.server.last_freeze_time), bytes([0x08, 0x01, 0x10, 0x30])
        )

    def test_broadcast_freeze(self):
        """广播冻结：使用广播地址，服务端不应答但记录冻结时间"""
        item = self.client.freeze(month=12, day=25, hour=8, minute=0, broadcast=True)
        self.assertIsNotNone(item)
        time.sleep(0.2)
        self.assertEqual(
            bytes(self.server.last_freeze_time), bytes([0x12, 0x25, 0x08, 0x00])
        )

    def test_change_baud_rate(self):
        """更改通信速率：应答特征字与请求一致，服务端速率更新"""
        item = self.client.change_baud_rate(9600)
        self.assertIsNotNone(item)
        self.assertEqual(item.value, 9600)
        time.sleep(0.2)
        self.assertEqual(self.server.baud_rate, 9600)
        # 不支持的速率，客户端应拒绝
        item = self.client.change_baud_rate(1111)
        self.assertIsNone(item)

    def test_clear_demand(self):
        """最大需量清零：需量值归零（04级密码）；权限不足被拒绝"""
        self.server.set_01(0x01010000, Demand(12.5, datetime(2026, 7, 31, 12, 0)))
        # 权限不足（05级密码，未设置但级别校验在客户端先行拦截）
        item = self.client.clear_demand(0x01010000, "05000000")
        self.assertIsNone(item)
        # 正确密码（04级）-> 清零成功
        item = self.client.clear_demand(0x01010000, "04000000")
        self.assertIsNotNone(item)
        self.assertEqual(item.name, "最大需量清零")
        time.sleep(0.2)
        demand = self.server.get_data_item(0x01010000)
        self.assertIsNotNone(demand)
        self.assertEqual(demand.value.value, 0.0)

    def test_clear_meter(self):
        """电表清零：电能/事件清零但变量保留（02级密码）；权限不足被拒绝"""
        self.server.set_00(0x00000000, 123.45)
        self.server.set_02(0x02010100, 220.5)  # 运行变量（瞬时值）
        self.server.set_03(
            0x03010000,
            [
                ("111111", "222222"),
                ("111111", "222222"),
                ("111111", "222222"),
            ],
        )
        # 权限不足（04级密码）-> 客户端直接拒绝，不发帧
        item = self.client.clear_meter("04000000")
        self.assertIsNone(item)
        time.sleep(0.2)
        self.assertNotEqual(self.server.get_data_item(0x00000000).value, 0.0)
        # 正确密码（02级）-> 清零成功
        item = self.client.clear_meter("02000000")
        self.assertIsNotNone(item)
        self.assertEqual(item.name, "电表清零")
        time.sleep(0.2)
        # 电能量归零
        self.assertEqual(self.server.get_data_item(0x00000000).value, 0.0)
        # 事件记录被清空
        events = self.server.get_data_item(0x03010000)
        self.assertEqual(events[0].value.event, ("000000", "000000"))
        # 运行变量保留（不在清零范围）
        self.assertEqual(self.server.get_data_item(0x02010100).value, 220.5)
        self.assertEqual(len(self.server.clear_meter_event_records), 1)

    def test_clear_event(self):
        """事件清零：事件记录被清空（02级密码），且可被客户端正常读回"""
        # 设置事件记录（A/B/C 相失压累计时间）
        self.server.set_03(
            0x03010000,
            [
                ("111111", "222222"),
                ("111111", "222222"),
                ("111111", "222222"),
            ],
        )
        # 权限不足（04级密码）-> 客户端直接拒绝，不发帧
        item = self.client.clear_event("04000000")
        self.assertIsNone(item)
        # 正确密码 -> 事件总清零
        item = self.client.clear_event("02000000")
        self.assertIsNotNone(item)
        self.assertEqual(item.name, "事件清零")
        time.sleep(0.2)
        events = self.server.get_data_item(0x03010000)
        self.assertIsNotNone(events)
        for ev in events:
            self.assertEqual(ev.value.event, ("000000", "000000"))
        # 客户端读回事件记录，应能正常解析（数据长度不变）
        read_back = self.client.read_03(0x03010000)
        self.assertIsNotNone(read_back)
        self.assertEqual(read_back[0].value.event, ("000000", "000000"))
        # 事件清零记录已生成（总次数累加）
        total = self.server.get_data_item(0x03300200)
        self.assertGreaterEqual(int(str(total[0].value.event)), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
