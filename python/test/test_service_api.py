import unittest

from dlt645.common.transform import string_to_bcd
from dlt645.service.clientsvc.client_service import MeterClientService
from dlt645.service.serversvc.server_service import MeterServerService


class TestServiceApi(unittest.TestCase):
    def test_sync_context_managers_and_write_address(self):
        server = MeterServerService.new_tcp_server("127.0.0.1", 0, timeout=1.0)
        self.assertTrue(server.set_address("123456781012"))

        with server:
            client = MeterClientService.new_tcp_client(
                "127.0.0.1", server.server.port, timeout=1.0
            )
            self.assertTrue(client.set_address("123456781012"))
            with client:
                result = client.write_address("123456781013")

            self.assertIsNotNone(result)
            self.assertEqual(client.address, string_to_bcd("123456781013"))
            self.assertEqual(server.address, string_to_bcd("123456781013"))

        self.assertFalse(server.server.is_running())


if __name__ == "__main__":
    unittest.main()
