import socket
import threading
import unittest

from dlt645.model.types.dlt645_type import CtrlCode
from dlt645.protocol.protocol import DLT645Protocol
from dlt645.transport.client.tcp_client import TcpClient
from dlt645.transport.server.tcp_server import TcpServer


class _EchoService:
    def __init__(self) -> None:
        self.request_count = 0

    def handle_request(self, frame):
        self.request_count += 1
        return DLT645Protocol.build_frame(
            bytes(frame.addr), frame.ctrl_code | 0x80, bytes(frame.data)
        )


class TestSyncTcpTransport(unittest.TestCase):
    def test_server_processes_multiple_frames_from_one_read(self):
        service = _EchoService()
        server = TcpServer("127.0.0.1", 0, timeout=0.5, service=service)
        self.assertTrue(server.start())
        conn = socket.create_connection(("127.0.0.1", server.port), timeout=1.0)
        conn.settimeout(1.0)
        try:
            request = DLT645Protocol.build_frame(
                bytes(6), CtrlCode.ReadAddress, b""
            )
            conn.sendall(bytes(request + request))

            buffer = bytearray()
            frames = []
            while len(frames) < 2:
                buffer.extend(conn.recv(1024))
                while buffer:
                    remaining, frame = DLT645Protocol.deserialize_with_remaining(buffer)
                    buffer = bytearray(remaining)
                    if frame is None:
                        break
                    frames.append(frame)

            self.assertEqual(len(frames), 2)
            self.assertEqual(service.request_count, 2)
        finally:
            conn.close()
            self.assertTrue(server.stop())

    def test_client_reassembles_fragmented_response(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        response = bytes(
            DLT645Protocol.build_frame(
                bytes(6), CtrlCode.ReadAddress | 0x80, bytes(6)
            )
        )

        def serve_once() -> None:
            conn, _ = listener.accept()
            try:
                conn.recv(1024)
                midpoint = len(response) // 2
                conn.sendall(response[:midpoint])
                conn.sendall(response[midpoint:])
            finally:
                conn.close()
                listener.close()

        worker = threading.Thread(target=serve_once, daemon=True)
        worker.start()
        client = TcpClient("127.0.0.1", port, timeout=1.0)
        try:
            request = DLT645Protocol.build_frame(
                bytes(6), CtrlCode.ReadAddress, b""
            )
            received = client.send_request(
                request,
                write_timeout=1.0,
                read_timeout=1.0,
                total_timeout=2.0,
                retries=0,
            )
            self.assertEqual(received, response)
        finally:
            client.disconnect()
            worker.join(timeout=2.0)


if __name__ == "__main__":
    unittest.main()
