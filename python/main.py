import time

from src.service.serversvc.server_service import MeterServerService

if __name__ == '__main__':
    server_svc = MeterServerService.new_tcp_server("127.0.0.1", 10521, 3000)
    # server_svc = MeterServerService.new_rtu_server("COM11", 8, 1, 2400, "E", 1000)
    server_svc.set_00(0x00000000, 100.0)
    server_svc.set_02(0x02010100, 86.0)
    server_svc.enable_message_capture(queue_size=50)
    server_svc.server.start()
    while True:
        messages = server_svc.get_captured_pairs()
        for message in messages:
            print(message)
        time.sleep(1)