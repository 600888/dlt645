import sys
import time
from datetime import datetime

sys.path.append("../..")
from src.service.serversvc.server_service import MeterServerService
from src.model.types.dlt645_type import Demand

if __name__ == "__main__":
    dlt645_svc = MeterServerService.new_rtu_server(port="COM11",data_bits=8,stop_bits=1,baud_rate=9600,parity="N",timeout=1.0)
    # 写电能
    dlt645_svc.set_00(0x00000000, 50.5)
    
    # 写最大需量
    dlt645_svc.set_01(0x01010000, Demand(78.0, datetime.strptime("2023-01-01 12:00:00", "%Y-%m-%d %H:%M:%S")))
        
    # 写参变量
    dlt645_svc.set_04(0x04000101, "25110201") # 2025年11月2日星期一
    dlt645_svc.set_04(0x04000204, "10") # 设置费率数为10
    
    schedule_list = []
    schedule_list.append("120901")
    schedule_list.append("120902")
    schedule_list.append("120903")
    schedule_list.append("120904")
    schedule_list.append("120905")
    schedule_list.append("120906")
    schedule_list.append("120907")
    schedule_list.append("120908")
    schedule_list.append("120909")
    schedule_list.append("120910")
    schedule_list.append("120911")
    schedule_list.append("120912")
    schedule_list.append("120913")
    schedule_list.append("120914")
    dlt645_svc.set_04(0x04010000, schedule_list)    # 第一套时区表数据
    
    dlt645_svc.server.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        dlt645_svc.server.stop()
        print("服务端已停止")