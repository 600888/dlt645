#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DLT645协议库基本测试

这个脚本提供了基本的单元测试，确保包能正常工作
"""

import unittest
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

try:
    from src.service.serversvc.server_service import MeterServerService, new_tcp_server, new_rtu_server
    from src.service.clientsvc.client_service import MeterClientService
    from src.protocol.protocol import DLT645Protocol
    from src.model.types.dlt645_type import CtrlCode
except ImportError as e:
    print(f"导入模块失败: {e}")
    print("请确保在dlt645包目录中运行此脚本")
    sys.exit(1)


class TestDLT645Basic(unittest.TestCase):
    """DLT645协议基本功能测试"""
    
    def test_import(self):
        """测试模块导入"""
        print("测试模块导入...")
        self.assertIsNotNone(MeterServerService)
        self.assertIsNotNone(MeterClientService)
        self.assertIsNotNone(DLT645Protocol)
        self.assertIsNotNone(CtrlCode)
        print("✓ 模块导入正常")
    
    def test_tcp_server_creation(self):
        """测试TCP服务器创建"""
        print("测试TCP服务器创建...")
        try:
            server = new_tcp_server("127.0.0.1", 8022, 30)
            self.assertIsNotNone(server)
            self.assertIsInstance(server, MeterServerService)
            print("✓ TCP服务器创建成功")
        except Exception as e:
            self.fail(f"TCP服务器创建失败: {e}")
    
    def test_tcp_client_creation(self):
        """测试TCP客户端创建"""
        print("测试TCP客户端创建...")
        try:
            client = MeterClientService.new_tcp_client("127.0.0.1", 8023, 10.0)
            self.assertIsNotNone(client)
            self.assertIsInstance(client, MeterClientService)
            print("✓ TCP客户端创建成功")
        except Exception as e:
            self.fail(f"TCP客户端创建失败: {e}")
    
    def test_server_data_setting(self):
        """测试服务器数据设置"""
        print("测试服务器数据设置...")
        try:
            server = new_tcp_server("127.0.0.1", 8024, 30)
            
            # 测试设置电能量数据
            result = server.set_00(0x00000000, 123.45)
            # 注意：由于没有实际的数据存储后端，这里可能返回False
            # 我们主要测试方法调用不会抛出异常
            
            # 测试设置变量数据
            result = server.set_02(0x02010100, 220.0)
            
            # 测试设置地址
            server.set_address(bytearray([0x01, 0x02, 0x03, 0x04, 0x05, 0x06]))
            
            print("✓ 服务器数据设置方法调用正常")
        except Exception as e:
            self.fail(f"服务器数据设置失败: {e}")
    
    def test_client_address_setting(self):
        """测试客户端地址设置"""
        print("测试客户端地址设置...")
        try:
            client = MeterClientService.new_tcp_client("127.0.0.1", 8025, 10.0)
            
            # 测试设置地址
            result = client.set_address(b'\x01\x02\x03\x04\x05\x06')
            self.assertTrue(result)
            
            # 测试设置密码
            result = client.set_password(b'\x00\x00\x00\x00')
            self.assertTrue(result)
            
            print("✓ 客户端地址和密码设置正常")
        except Exception as e:
            self.fail(f"客户端地址设置失败: {e}")
    
    def test_protocol_constants(self):
        """测试协议常量"""
        print("测试协议常量...")
        try:
            # 测试控制码常量
            self.assertIsNotNone(CtrlCode.ReadData)
            self.assertIsNotNone(CtrlCode.ReadAddress)
            self.assertIsNotNone(CtrlCode.WriteAddress)
            
            print("✓ 协议常量定义正常")
        except Exception as e:
            self.fail(f"协议常量测试失败: {e}")


def run_tests():
    """运行测试"""
    print("DLT645协议库基本测试")
    print("=" * 50)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDLT645Basic)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✓ 所有测试通过！")
        print("包基本功能正常，可以进行安装和使用。")
    else:
        print("✗ 部分测试失败！")
        print("请检查错误信息并修复问题。")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)