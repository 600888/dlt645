"""异步客户端和服务端测试。"""

import asyncio
import importlib.util
import unittest
from datetime import datetime

from src.aio import (
    AsyncMeterClientService,
    AsyncMeterServerService,
    AsyncRtuClient,
    AsyncTcpClient,
)
from src.common.transform import string_to_bcd
from src.model.types.dlt645_type import Demand
from src.protocol.protocol import DLT645Protocol
from src.model.types.dlt645_type import CtrlCode


class TestAsyncTcpIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.server = AsyncMeterServerService.new_tcp_server(
            "127.0.0.1", 0, timeout=0.5
        )
        self.server.set_address("123456781012")
        self.server.set_password("04000000")
        self.server.set_password("02000000")
        self.server.set_00(0x00000000, 12.34)
        self.server.set_01(0x01010000, Demand(5.67, datetime(2026, 8, 1, 12, 0, 0)))
        self.server.set_02(0x02010100, 220.5)
        self.assertTrue(await self.server.start())

        self.client = AsyncMeterClientService.new_tcp_client(
            "127.0.0.1", self.server.server.port, timeout=0.5
        )
        self.client.set_address("123456781012")

    async def asyncTearDown(self):
        await self.client.disconnect()
        await self.server.stop()

    async def test_read_and_concurrent_requests_on_one_connection(self):
        energy, voltage = await asyncio.gather(
            self.client.read_00(0x00000000),
            self.client.read_02(0x02010100),
        )
        self.assertIsNotNone(energy)
        self.assertIsNotNone(voltage)
        self.assertAlmostEqual(energy.value, 12.34, places=2)
        self.assertAlmostEqual(voltage.value, 220.5, places=1)

    async def test_read_address_and_commands(self):
        address = await self.client.read_address()
        self.assertIsNotNone(address)
        self.assertEqual(address.value, "123456781012")

        freeze = await self.client.freeze(month=8, day=1, hour=10, minute=30)
        self.assertIsNotNone(freeze)
        self.assertEqual(freeze.name, "冻结命令")

        self.assertTrue(
            await self.client.broadcast_time_sync(datetime(2026, 8, 1, 10, 30, 45))
        )
        await asyncio.sleep(0.05)
        self.assertEqual(self.server.time, datetime(2026, 8, 1, 10, 30, 45))

        broadcast_freeze = await self.client.freeze(
            month=12, day=25, hour=8, minute=0, broadcast=True
        )
        self.assertIsNotNone(broadcast_freeze)
        await asyncio.sleep(0.05)
        self.assertEqual(
            bytes(self.server.last_freeze_time), bytes([0x12, 0x25, 0x08, 0x00])
        )

    async def test_data_write_password_and_clear_commands(self):
        self.server.set_03(
            0x03010000,
            [("000015", "000012"), ("000025", "000024"), ("000034", "000030")],
        )
        self.server.set_04(0x04000101, "26080106")

        demand = await self.client.read_01(0x01010000)
        events = await self.client.read_03(0x03010000)
        parameter = await self.client.read_04(0x04000101)
        self.assertIsNotNone(demand)
        self.assertIsNotNone(events)
        self.assertIsNotNone(parameter)

        written = await self.client.write_04(
            0x04000101, "26080207", password="02000000"
        )
        # 同步 API 对成功的写参变量响应也返回 None；异步版保持兼容。
        self.assertIsNone(written)
        self.assertEqual(self.server.get_data_item(0x04000101).value, "26080207")

        self.client.set_password("04000000")
        changed = await self.client.change_password("04000000", "04123456")
        self.assertIsNone(changed)
        self.assertTrue(
            self.server.password_manager.check_password(string_to_bcd("04123456"))
        )

        cleared_event = await self.client.clear_event("02000000")
        self.assertIsNotNone(cleared_event)
        cleared_meter = await self.client.clear_meter("02000000")
        self.assertIsNotNone(cleared_meter)

        new_address = string_to_bcd("123456781013")
        address_result = await self.client.write_address(new_address)
        self.assertIsNotNone(address_result)
        self.assertEqual(bytes(self.server.address), bytes(new_address))

    async def test_clear_demand_and_validation_failure_are_awaitable(self):
        self.assertIsNone(await self.client.change_baud_rate(1111))
        self.assertIsNone(await self.client.clear_demand(0x01010000, "05000000"))
        result = await self.client.clear_demand(0x01010000, "04000000")
        self.assertIsNotNone(result)
        self.assertEqual(self.server.get_data_item(0x01010000).value.value, 0.0)

    async def test_multiple_clients(self):
        clients = [
            AsyncMeterClientService.new_tcp_client(
                "127.0.0.1", self.server.server.port, timeout=0.5
            )
            for _ in range(3)
        ]
        for client in clients:
            client.set_address("123456781012")
        try:
            results = await asyncio.gather(
                *(client.read_00(0x00000000) for client in clients)
            )
            self.assertEqual([item.value for item in results], [12.34] * 3)
        finally:
            await asyncio.gather(*(client.disconnect() for client in clients))


class TestAsyncTcpTransport(unittest.IsolatedAsyncioTestCase):
    async def test_fragmented_response(self):
        address = bytes.fromhex("121078563412")
        response = bytes(
            DLT645Protocol.build_frame(address, CtrlCode.ReadAddress | 0x80, address)
        )

        async def responder(reader, writer):
            await reader.read(1024)
            midpoint = len(response) // 2
            writer.write(response[:midpoint])
            await writer.drain()
            await asyncio.sleep(0.02)
            writer.write(response[midpoint:])
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        server = await asyncio.start_server(responder, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        client = AsyncTcpClient("127.0.0.1", port, timeout=0.5)
        request = bytes(
            DLT645Protocol.build_frame(
                bytes.fromhex("AAAAAAAAAAAA"), CtrlCode.ReadAddress, None
            )
        )
        try:
            received = await client.send_request(
                request, read_timeout=0.5, total_timeout=1.0, retries=0
            )
            self.assertEqual(received, response)
        finally:
            await client.disconnect()
            server.close()
            await server.wait_closed()


class _MemoryWriter:
    def __init__(self):
        self.data = bytearray()
        self.closed = False

    def write(self, data):
        self.data.extend(data)

    async def drain(self):
        return None

    def close(self):
        self.closed = True

    async def wait_closed(self):
        return None

    def is_closing(self):
        return self.closed


class TestAsyncRtuTransport(unittest.IsolatedAsyncioTestCase):
    async def test_server_handles_fragmented_serial_frame(self):
        service = AsyncMeterServerService.new_rtu_server("unused", timeout=0.5)
        service.set_address("123456781012")
        service.set_00(0x00000000, 88.66)
        reader = asyncio.StreamReader()
        writer = _MemoryWriter()
        service.server.reader = reader
        service.server.writer = writer
        service.server._running = True

        request = bytes(
            DLT645Protocol.build_frame(
                bytes.fromhex("123456781012"),
                CtrlCode.ReadData,
                bytes.fromhex("00000000"),
            )
        )
        task = asyncio.create_task(service.server._run())
        midpoint = len(request) // 2
        reader.feed_data(request[:midpoint])
        await asyncio.sleep(0)
        reader.feed_data(request[midpoint:])
        reader.feed_eof()
        await task

        _, response_frame = DLT645Protocol.deserialize_with_remaining(
            bytes(writer.data)
        )
        self.assertIsNotNone(response_frame)
        self.assertEqual(response_frame.ctrl_code, CtrlCode.ReadData | 0x80)

    @unittest.skipUnless(
        importlib.util.find_spec("serial_asyncio") is not None,
        "未安装 pyserial-asyncio 可选依赖",
    )
    async def test_client_loopback(self):
        client = AsyncRtuClient("loop://", timeout=1.0)
        self.assertTrue(await client.connect())
        # pyserial-asyncio 强制非阻塞写；loop:// 需要测试专用正超时。
        client.writer.transport.serial.write_timeout = 1.0
        frame = bytes(
            DLT645Protocol.build_frame(
                bytes.fromhex("121078563412"), CtrlCode.ReadAddress, None
            )
        )
        try:
            self.assertEqual(await client.send_request(frame, retries=0), frame)
        finally:
            await client.disconnect()


if __name__ == "__main__":
    unittest.main(verbosity=2)
