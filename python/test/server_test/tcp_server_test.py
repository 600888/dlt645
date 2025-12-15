import sys
import time
from datetime import datetime

sys.path.append("../..")
from src.service.serversvc.server_service import MeterServerService
from src.model.types.dlt645_type import Demand

if __name__ == "__main__":
    dlt645_svc = MeterServerService.new_tcp_server("0.0.0.0", 10521)
    dlt645_svc.server.start()

    # 设置设备地址
    dlt645_svc.set_address("123456781012")

    # 设置密码
    dlt645_svc.set_password("00123456")

    # 写电能
    dlt645_svc.set_00(0x00000000, 50.5)

    # 写最大需量
    dlt645_svc.set_01(
        0x01010000,
        Demand(78.0, datetime.strptime("2023-01-01 12:00:00", "%Y-%m-%d %H:%M:%S")),
    )

    # 写变量
    dlt645_svc.set_02(0x02010100, 66.6)

    # 设置事件记录
    dlt645_svc.set_03(
        0x03010000,
        [
            ("000015", "000012"),  # A相失压总次数、累计时间
            ("000025", "000024"),  # B相失压总次数、累计时间
            ("000034", "000030"),  # C相失压总次数、累计时间
        ],
    )

    # 写参变量
    dlt645_svc.set_04(0x04000101, "25110201")  # 2025年11月2日星期一
    dlt645_svc.set_04(0x04000204, "10")  # 设置费率数为10

    schedule_list = [
        "120901",
        "120902",
        "120903",
        "120904",
        "120905",
        "120906",
        "120907",
        "120908",
        "120909",
        "120910",
        "120911",
        "120912",
        "120913",
        "120914",
    ]
    dlt645_svc.set_04(0x04010000, schedule_list)  # 第一套时区表数据

    dlt645_svc.set_04(0x04030001, "25120901")  # 第一公共假日日期及时段表号

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        dlt645_svc.server.stop()
        print("服务端已停止")
