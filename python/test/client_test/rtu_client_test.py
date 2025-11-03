import sys
import time

sys.path.append("../..")
from src.service.clientsvc.client_service import MeterClientService

if __name__ == "__main__":
    client_svc = MeterClientService.new_rtu_client("COM10", 9600, 8, 1, "N", 0.5)
    if not client_svc:
        print("创建客户端失败")
        sys.exit(1)
    
    # 读取通讯地址
    print("读取通讯地址...")
    address_data = client_svc.read_address()
    if address_data and hasattr(address_data, 'value'):
        print(f"通讯地址: {address_data.value}")
    else:
        print("读取通讯地址失败")
    
    # 设置设备地址
    client_svc.set_address(address_data.value)
    
    # 读取电能数据
    data_item = client_svc.read_00(0x00000000)
    print(f"电能数据: {data_item}")
    
    # 读取最大需量及发生时间
    data_item2 = client_svc.read_01(0x01010000)
    print(f"最大需量及发生时间: {data_item2}")
    
    # 读取变量数据
    data_item3 = client_svc.read_02(0x02010100)
    print(f"变量数据: {data_item3}")
    
    # 读取参变量
    print("读取参变量...")
    data_item4 = client_svc.read_04(0x04000101)
    print(f"日期及星期: {data_item4}")
    
    data_item5 = client_svc.read_04(0x04000204)
    print(f"费率数: {data_item5}")

