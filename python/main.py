from src.service.serversvc.server_service import new_tcp_server, new_rtu_server

if __name__ == '__main__':
    server_svc = new_tcp_server("127.0.0.1", 8021, 3000)
    # server_svc = new_rtu_server("COM4", 8, 1, 9600, "N", 1000)
    server_svc.set_00(0x00000000, 100.0)
    server_svc.set_02(0x02010100, 86.0)
    server_svc.server.start()
