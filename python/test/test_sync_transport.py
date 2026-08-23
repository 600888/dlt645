import socket
import threading
import unittest

from dlt645.model.types.dlt645_type import CtrlCode
from dlt645.protocol.protocol import DLT645Protocol
from dlt645.service.serversvc.server_service import MeterServerService
from dlt645.transport.client.tcp_client import TcpClient
from dlt645.transport.server.tcp_server import TcpServer
from dlt645.transport.server.tcp_lifecycle import TcpDisconnectReason


class _EchoService:
    def __init__(self) -> None:
        self.request_count = 0

    def handle_request(self, frame):
        self.request_count += 1
        return DLT645Protocol.build_frame(
            bytes(frame.addr), frame.ctrl_code | 0x80, bytes(frame.data)
        )


class TestSyncTcpTransport(unittest.TestCase):
    def test_server_lifecycle_callbacks(self):
        connected = []
        activities = []
        disconnected = []
        disconnect_event = threading.Event()

        def on_connect(connection):
            connected.append(connection)

        async def on_activity(connection, activity):
            activities.append((connection, activity))
            if activity.direction == "RX":
                raise RuntimeError("test callback failure")

        def on_disconnect(connection):
            disconnected.append(connection)
            disconnect_event.set()

        service = MeterServerService.new_tcp_server(
            "127.0.0.1",
            0,
            timeout=0.5,
            on_connect=on_connect,
            on_activity=on_activity,
            on_disconnect=on_disconnect,
        )
        service.set_address("123456781012")
        self.assertTrue(service.start())
        conn = socket.create_connection(("127.0.0.1", service.server.port), timeout=1.0)
        conn.settimeout(1.0)
        request = bytes(
            DLT645Protocol.build_frame(
                bytes.fromhex("AAAAAAAAAAAA"), CtrlCode.ReadAddress, None
            )
        )

        try:
            conn.sendall(request)
            response = conn.recv(1024)
            self.assertTrue(response)
            conn.close()
            self.assertTrue(disconnect_event.wait(timeout=1.0))

            self.assertEqual(len(connected), 1)
            self.assertEqual(len(disconnected), 1)
            connection = connected[0]
            self.assertIs(disconnected[0], connection)
            self.assertTrue(all(item[0] is connection for item in activities))
            self.assertEqual([item[1].direction for item in activities], ["RX", "TX"])
            self.assertEqual(activities[0][1].data, request)
            self.assertEqual(activities[1][1].data, response)
            self.assertEqual(connection.bytes_received, len(request))
            self.assertEqual(connection.bytes_sent, len(response))
            self.assertEqual(connection.messages_received, 1)
            self.assertEqual(connection.messages_sent, 1)
            self.assertEqual(connection.status, "disconnected")
            self.assertEqual(
                connection.disconnect_reason, TcpDisconnectReason.CLIENT_EOF
            )
            self.assertIsNone(connection.disconnect_error)
            self.assertGreaterEqual(connection.duration, 0.0)
            self.assertEqual(connection.peer_host, "127.0.0.1")
            self.assertIsInstance(connection.peer_port, int)
        finally:
            conn.close()
            self.assertTrue(service.stop())

    def test_server_stop_reports_disconnect_reason(self):
        connected_event = threading.Event()
        disconnected = []

        def on_connect(connection):
            connected_event.set()

        def on_disconnect(connection):
            disconnected.append(connection)

        server = TcpServer(
            "127.0.0.1",
            0,
            timeout=0.5,
            service=_EchoService(),
            on_connect=on_connect,
            on_disconnect=on_disconnect,
        )
        self.assertTrue(server.start())
        conn = socket.create_connection(("127.0.0.1", server.port), timeout=1.0)
        try:
            self.assertTrue(connected_event.wait(timeout=1.0))
            self.assertTrue(server.stop())
            self.assertEqual(conn.recv(1), b"")
            self.assertEqual(len(disconnected), 1)
            self.assertEqual(
                disconnected[0].disconnect_reason,
                TcpDisconnectReason.SERVER_STOPPED,
            )
        finally:
            conn.close()
            self.assertTrue(server.stop())

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
