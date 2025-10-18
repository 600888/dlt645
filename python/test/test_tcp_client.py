import sys

sys.path.append("..")
from src.service.clientsvc.client_service import MeterClientService

if __name__ == "__main__":
    client_svc = MeterClientService.new_tcp_client("127.0.0.1", 10521, 3000)
    client_svc.set_address(bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))
    data_item = client_svc.read_01(0x00000000)
    print(data_item)
