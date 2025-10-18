import sys

sys.path.append("..")
from src.service.clientsvc.client_service import MeterClientService

if __name__ == "__main__":
    client_svc = MeterClientService.new_rtu_client("COM10", 9600, 8, 1, "N", 0.5)
    client_svc.set_address(bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))
    data_item = client_svc.read_01(0x00000000)
    print(data_item)
