#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DLT645协议使用示例

这个脚本演示了如何使用dlt645协议库创建服务器和客户端
"""

import time
import threading
from dlt645 import new_tcp_server, MeterClientService


def server_example():
    """服务器示例"""
    print("=== DLT645 TCP服务器示例 ===")
    
    # 创建TCP服务器
    print("创建TCP服务器...")
    server_service = new_tcp_server("127.0.0.1", 8021, 30)
    
    # 设置设备地址
    device_addr = bytearray([0x01, 0x02, 0x03, 0x04, 0x05, 0x06])
    server_service.register_device(device_addr)
    print(f"设备地址: {device_addr.hex()}")
    
    # 设置电能量数据
    print("设置电能量数据...")
    server_service.set_00(0x00000000, 12345.67)  # 总有功电能
    server_service.set_00(0x00010000, 10000.50)  # 正向有功电能
    server_service.set_00(0x00020000, 2345.17)   # 反向有功电能
    
    # 设置变量数据
    print("设置变量数据...")
    server_service.set_02(0x02010100, 220.5)     # A相电压
    server_service.set_02(0x02010200, 219.8)     # B相电压
    server_service.set_02(0x02010300, 221.2)     # C相电压
    server_service.set_02(0x02020100, 15.6)      # A相电流
    server_service.set_02(0x02020200, 14.8)      # B相电流
    server_service.set_02(0x02020300, 16.2)      # C相电流
    
    # 启动服务器
    print("启动服务器...")
    server_service.server.start()
    print("服务器已启动，监听 127.0.0.1:8021")
    
    return server_service


def client_example():
    """客户端示例"""
    print("\n=== DLT645 TCP客户端示例 ===")
    
    # 等待服务器启动
    time.sleep(2)
    
    # 创建TCP客户端
    print("创建TCP客户端...")
    client = MeterClientService.new_tcp_client("127.0.0.1", 8021, 10.0)
    
    if client is None:
        print("创建客户端失败")
        return
    
    # 设置设备地址（需要与服务器一致）
    device_addr = bytes([0x01, 0x02, 0x03, 0x04, 0x05, 0x06])
    client.set_address(device_addr)
    print(f"设置设备地址: {device_addr.hex()}")
    
    print("\n开始读取数据...")
    
    # 读取电能量数据
    print("\n--- 读取电能量数据 ---")
    energy_dis = [
        (0x00000000, "总有功电能"),
        (0x00010000, "正向有功电能"),
        (0x00020000, "反向有功电能"),
    ]
    
    for di, desc in energy_dis:
        try:
            data = client.read_01(di)
            if data:
                print(f"{desc}: {data.value} kWh")
            else:
                print(f"{desc}: 读取失败")
        except Exception as e:
            print(f"{desc}: 读取异常 - {e}")
    
    # 读取变量数据
    print("\n--- 读取变量数据 ---")
    variable_dis = [
        (0x02010100, "A相电压"),
        (0x02010200, "B相电压"), 
        (0x02010300, "C相电压"),
        (0x02020100, "A相电流"),
        (0x02020200, "B相电流"),
        (0x02020300, "C相电流"),
    ]
    
    for di, desc in variable_dis:
        try:
            data = client.read_03(di)
            if data:
                unit = "V" if "电压" in desc else "A"
                print(f"{desc}: {data.value} {unit}")
            else:
                print(f"{desc}: 读取失败")
        except Exception as e:
            print(f"{desc}: 读取异常 - {e}")
    
    # 读取设备地址
    print("\n--- 读取设备地址 ---")
    try:
        addr_data = client.read_address()
        if addr_data:
            print(f"设备地址: {addr_data.value}")
        else:
            print("读取设备地址失败")
    except Exception as e:
        print(f"读取设备地址异常: {e}")


def rtu_example():
    """RTU示例（仅演示代码，需要真实串口）"""
    print("\n=== DLT645 RTU示例 ===")
    print("注意：此示例需要真实的串口设备，这里仅演示代码")
    
    # RTU服务器示例
    print("\nRTU服务器代码示例：")
    print("""
from dlt645 import new_rtu_server

# 创建RTU服务器
server_service = new_rtu_server(
    port="COM1",        # Windows: "COM1", Linux: "/dev/ttyUSB0"
    dataBits=8,
    stopBits=1, 
    baudRate=9600,
    parity="E",         # E=偶校验, O=奇校验, N=无校验
    timeout=1000
)

# 设置数据
server_service.set_00(0x00000000, 100.0)
server_service.set_02(0x02010100, 220.0)

# 启动服务器
server_service.server.start()
    """)
    
    # RTU客户端示例
    print("\nRTU客户端代码示例：")
    print("""
from dlt645 import MeterClientService

# 创建RTU客户端
client = MeterClientService.new_rtu_client(
    port="COM1",
    baudrate=9600,
    databits=8,
    stopbits=1,
    parity="E",
    timeout=30.0
)

# 设置设备地址
client.set_address(b'\\x01\\x02\\x03\\x04\\x05\\x06')

# 读取数据
data = client.read_01(0x00000000)
if data:
    print(f"电能量: {data.value}")
    """)


def main():
    """主函数"""
    print("DLT645协议库使用示例")
    print("=" * 50)
    
    try:
        # 在单独线程中启动服务器
        server_thread = threading.Thread(target=server_example, daemon=True)
        server_thread.start()
        
        # 运行客户端示例
        client_example()
        
        # 显示RTU示例
        rtu_example()
        
        print("\n示例运行完成!")
        print("注意：服务器仍在后台运行，可以使用其他DLT645客户端工具连接测试")
        
        # 保持程序运行一段时间
        print("\n按Ctrl+C退出...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n程序已退出")
            
    except Exception as e:
        print(f"运行示例时发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()