# 异步客户端与服务端

异步 API 位于 `dlt645.aio`，不会替换或修改现有同步 API。异步 TCP 只依赖
Python 标准库；异步 RTU 需要安装串口可选依赖：

```bash
pip install "dlt645[async]"
```

## TCP 示例

```python
import asyncio

from dlt645.aio import AsyncMeterClientService, AsyncMeterServerService


async def main():
    server = AsyncMeterServerService.new_tcp_server("127.0.0.1", 10521)
    server.set_address("123456781012")
    server.set_00(0x00000000, 50.5)
    await server.start()

    try:
        async with AsyncMeterClientService.new_tcp_client(
            "127.0.0.1", 10521, timeout=5
        ) as client:
            client.set_address("123456781012")
            data = await client.read_00(0x00000000)
            print(data)
    finally:
        await server.stop()


asyncio.run(main())
```

## RTU 示例

```python
import asyncio

from dlt645.aio import AsyncMeterClientService


async def main():
    async with AsyncMeterClientService.new_rtu_client(
        port="COM10",
        baudrate=9600,
        databits=8,
        stopbits=1,
        parity="N",
        timeout=1.0,
    ) as client:
        client.set_address("123456781012")
        data = await client.read_00(0x00000000)
        print(data)


asyncio.run(main())
```

同一个客户端实例上的请求会自动串行执行。多个 TCP 客户端可以并发访问服务端。
广播校时和广播冻结只发送数据，不等待响应。

