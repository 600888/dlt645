import unittest

from dlt645.service.serversvc.server_service import MeterServerService


class TestServiceStateIsolation(unittest.TestCase):
    def test_server_instances_do_not_share_mutable_defaults(self):
        first = MeterServerService.new_tcp_server("127.0.0.1", 0)
        second = MeterServerService.new_tcp_server("127.0.0.1", 0)

        first.address[0] = 0x12

        self.assertEqual(second.address, bytearray(6))
        self.assertIsNot(first.password_manager, second.password_manager)
        self.assertIsNot(first.data_map, second.data_map)

    def test_server_data_values_are_isolated(self):
        first = MeterServerService.new_tcp_server("127.0.0.1", 0)
        second = MeterServerService.new_tcp_server("127.0.0.1", 0)
        di = 0x00000000

        self.assertTrue(first.set_00(di, 123.45))

        first_item = first.get_data_item(di)
        second_item = second.get_data_item(di)
        self.assertIsNot(first_item, second_item)
        self.assertEqual(first_item.value, 123.45)
        self.assertNotEqual(second_item.value, 123.45)


if __name__ == "__main__":
    unittest.main()
