#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DLT645协议库报文捕获功能测试

这个脚本提供了报文捕获功能的单元测试
"""

import unittest
import sys
import os
import time
import threading

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from src.common.message_types import MessageRecord, MessagePair
    from src.common.message_capture import MessageQueue, MessageCapture
except ImportError as e:
    print(f"导入模块失败: {e}")
    print("请确保在dlt645/python目录中运行此脚本")
    sys.exit(1)


class TestMessageTypes(unittest.TestCase):
    """报文数据类型测试"""

    def test_message_record_creation(self):
        """测试MessageRecord创建"""
        print("测试MessageRecord创建...")
        record = MessageRecord(direction="TX", data=b"\x68\x00\x00\x00\x00\x00\x00\x68")
        self.assertEqual(record.direction, "TX")
        self.assertEqual(record.data, b"\x68\x00\x00\x00\x00\x00\x00\x68")
        self.assertIsNotNone(record.id)
        self.assertIsNotNone(record.timestamp)
        self.assertIn("68", record.hex_string)
        print("✓ MessageRecord创建成功")

    def test_message_record_to_dict(self):
        """测试MessageRecord转换为字典"""
        print("测试MessageRecord转换为字典...")
        record = MessageRecord(direction="RX", data=b"\x68\x01\x02\x03\x04\x05\x06\x68")
        record_dict = record.to_dict()
        self.assertIn("id", record_dict)
        self.assertEqual(record_dict["direction"], "RX")
        self.assertIn("timestamp", record_dict)
        print("✓ MessageRecord转换为字典成功")

    def test_message_pair_creation(self):
        """测试MessagePair创建"""
        print("测试MessagePair创建...")
        pair = MessagePair()
        self.assertIsNotNone(pair.id)
        self.assertIsNone(pair.tx)
        self.assertIsNone(pair.rx)
        self.assertFalse(pair.is_complete())
        print("✓ MessagePair创建成功")

    def test_message_pair_with_tx_rx(self):
        """测试MessagePair配对TX和RX"""
        print("测试MessagePair配对TX和RX...")
        pair = MessagePair()
        
        tx_record = MessageRecord(direction="TX", data=b"\x68\x00")
        time.sleep(0.01)  # 小延迟确保时间差
        rx_record = MessageRecord(direction="RX", data=b"\x68\x01")
        
        pair.set_tx(tx_record)
        pair.set_rx(rx_record)
        
        self.assertTrue(pair.is_complete())
        self.assertIsNotNone(pair.round_trip_time)
        self.assertGreater(pair.round_trip_time, 0)
        self.assertEqual(tx_record.pair_id, pair.id)
        self.assertEqual(rx_record.pair_id, pair.id)
        print("✓ MessagePair配对TX和RX成功")


class TestMessageQueue(unittest.TestCase):
    """报文队列测试"""

    def test_queue_basic_operations(self):
        """测试队列基本操作"""
        print("测试队列基本操作...")
        queue = MessageQueue(maxlen=10)
        
        # 添加记录
        record = MessageRecord(direction="TX", data=b"\x68")
        queue.append(record)
        
        self.assertEqual(len(queue), 1)
        records = queue.get_all()
        self.assertEqual(len(records), 1)
        print("✓ 队列基本操作成功")

    def test_queue_maxlen(self):
        """测试队列最大长度限制"""
        print("测试队列最大长度限制...")
        queue = MessageQueue(maxlen=5)
        
        # 添加超过最大长度的记录
        for i in range(10):
            record = MessageRecord(direction="TX", data=bytes([i]))
            queue.append(record)
        
        self.assertEqual(len(queue), 5)
        # 应该保留最后5条记录
        records = queue.get_all()
        self.assertEqual(records[-1].data, bytes([9]))
        print("✓ 队列最大长度限制成功")

    def test_queue_get_recent(self):
        """测试获取最近记录"""
        print("测试获取最近记录...")
        queue = MessageQueue(maxlen=20)
        
        for i in range(10):
            record = MessageRecord(direction="TX", data=bytes([i]))
            queue.append(record)
        
        recent = queue.get_recent(3)
        self.assertEqual(len(recent), 3)
        self.assertEqual(recent[-1].data, bytes([9]))
        print("✓ 获取最近记录成功")

    def test_queue_clear(self):
        """测试清空队列"""
        print("测试清空队列...")
        queue = MessageQueue(maxlen=10)
        
        for i in range(5):
            queue.append(MessageRecord(direction="TX", data=bytes([i])))
        
        queue.clear()
        self.assertEqual(len(queue), 0)
        print("✓ 清空队列成功")

    def test_queue_resize(self):
        """测试调整队列大小"""
        print("测试调整队列大小...")
        queue = MessageQueue(maxlen=10)
        
        for i in range(8):
            queue.append(MessageRecord(direction="TX", data=bytes([i])))
        
        # 缩小队列
        queue.resize(5)
        self.assertEqual(len(queue), 5)
        self.assertEqual(queue.maxlen, 5)
        
        # 确保保留的是最新的记录
        records = queue.get_all()
        self.assertEqual(records[-1].data, bytes([7]))
        print("✓ 调整队列大小成功")

    def test_queue_thread_safety(self):
        """测试队列线程安全性"""
        print("测试队列线程安全性...")
        queue = MessageQueue(maxlen=1000)
        
        def add_records(start, count):
            for i in range(start, start + count):
                queue.append(MessageRecord(direction="TX", data=bytes([i % 256])))
        
        # 创建多个线程同时添加记录
        threads = []
        for i in range(10):
            t = threading.Thread(target=add_records, args=(i * 50, 50))
            threads.append(t)
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # 应该有500条记录
        self.assertEqual(len(queue), 500)
        print("✓ 队列线程安全性测试成功")


class TestMessageCapture(unittest.TestCase):
    """报文捕获管理器测试"""

    def test_capture_disabled_by_default(self):
        """测试默认禁用捕获"""
        print("测试默认禁用捕获...")
        capture = MessageCapture()
        
        tx_id = capture.capture_tx(b"\x68\x00")
        self.assertIsNone(tx_id)
        
        stats = capture.get_stats()
        self.assertFalse(stats["enabled"])
        print("✓ 默认禁用捕获测试成功")

    def test_capture_enable_disable(self):
        """测试启用和禁用捕获"""
        print("测试启用和禁用捕获...")
        capture = MessageCapture()
        
        capture.enable()
        self.assertTrue(capture.enabled)
        
        capture.disable()
        self.assertFalse(capture.enabled)
        print("✓ 启用/禁用捕获测试成功")

    def test_capture_tx_and_rx(self):
        """测试捕获TX和RX"""
        print("测试捕获TX和RX...")
        capture = MessageCapture(enabled=True, queue_size=50)
        
        # 捕获TX
        tx_id = capture.capture_tx(b"\x68\x00\x00\x00\x00\x00\x00\x68")
        self.assertIsNotNone(tx_id)
        
        # 捕获RX并配对
        capture.capture_rx(b"\x68\x01\x02\x03\x04\x05\x06\x68", tx_id=tx_id)
        
        # 验证捕获结果
        tx_messages = capture.get_tx_messages()
        self.assertEqual(len(tx_messages), 1)
        
        rx_messages = capture.get_rx_messages()
        self.assertEqual(len(rx_messages), 1)
        
        pairs = capture.get_pairs()
        self.assertEqual(len(pairs), 1)
        self.assertTrue(pairs[0].is_complete())
        print("✓ 捕获TX和RX测试成功")

    def test_capture_server_mode(self):
        """测试服务器模式捕获（RX先于TX）"""
        print("测试服务器模式捕获...")
        capture = MessageCapture(enabled=True, queue_size=50)
        
        # 服务器先收到RX（请求）
        rx_id = capture.capture_rx_for_server(b"\x68\x00\x00\x00\x00\x00\x00\x68")
        self.assertIsNotNone(rx_id)
        
        # 然后发送TX（响应）
        capture.capture_tx_for_server(b"\x68\x01\x02\x03\x04\x05\x06\x68", rx_id=rx_id)
        
        # 验证配对
        pairs = capture.get_pairs()
        self.assertEqual(len(pairs), 1)
        self.assertTrue(pairs[0].is_complete())
        print("✓ 服务器模式捕获测试成功")

    def test_capture_queue_size(self):
        """测试队列大小设置"""
        print("测试队列大小设置...")
        capture = MessageCapture(enabled=True, queue_size=5)
        
        # 发送超过队列大小的报文
        for i in range(10):
            capture.capture_tx(bytes([0x68, i]))
        
        tx_messages = capture.get_tx_messages()
        self.assertEqual(len(tx_messages), 5)
        print("✓ 队列大小设置测试成功")

    def test_capture_clear(self):
        """测试清空捕获"""
        print("测试清空捕获...")
        capture = MessageCapture(enabled=True, queue_size=50)
        
        for i in range(5):
            capture.capture_tx(bytes([0x68, i]))
            capture.capture_rx(bytes([0x68, i + 10]))
        
        capture.clear()
        
        self.assertEqual(len(capture.get_tx_messages()), 0)
        self.assertEqual(len(capture.get_rx_messages()), 0)
        print("✓ 清空捕获测试成功")

    def test_capture_stats(self):
        """测试捕获统计"""
        print("测试捕获统计...")
        capture = MessageCapture(enabled=True, queue_size=100)
        
        for i in range(3):
            tx_id = capture.capture_tx(bytes([0x68, i]))
            capture.capture_rx(bytes([0x68, i + 10]), tx_id=tx_id)
        
        stats = capture.get_stats()
        self.assertTrue(stats["enabled"])
        self.assertEqual(stats["queue_size"], 100)
        self.assertEqual(stats["tx_count"], 3)
        self.assertEqual(stats["rx_count"], 3)
        self.assertEqual(stats["pair_count"], 3)
        print("✓ 捕获统计测试成功")


def run_tests():
    """运行测试"""
    print("DLT645协议库报文捕获功能测试")
    print("=" * 50)

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestMessageTypes))
    suite.addTests(loader.loadTestsFromTestCase(TestMessageQueue))
    suite.addTests(loader.loadTestsFromTestCase(TestMessageCapture))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✓ 所有测试通过！")
        print("报文捕获功能正常工作。")
    else:
        print("✗ 部分测试失败！")
        print("请检查错误信息并修复问题。")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
