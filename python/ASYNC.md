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

## TCP 连接生命周期回调

`AsyncMeterServerService.new_tcp_server` 和 `AsyncTcpServer` 接受三个可选的
关键字参数：`on_connect`、`on_activity`、`on_disconnect`。回调可以是普通函数
或 `async def`；未传入时行为与旧版本完全一致。

```python
from dlt645.aio import AsyncMeterServerService


def on_connect(connection):
    print(connection.connection_id, connection.peer_host, connection.peer_port)


async def on_activity(connection, activity):
    print(activity.direction, len(activity.data), connection.last_activity_at)


def on_disconnect(connection):
    print(connection.disconnect_reason, connection.duration)
    print(connection.bytes_received, connection.bytes_sent)


server = AsyncMeterServerService.new_tcp_server(
    "127.0.0.1",
    10521,
    on_connect=on_connect,
    on_activity=on_activity,
    on_disconnect=on_disconnect,
)
```

三个回调共享同一个 `TcpConnectionContext`。其中包含连接 ID、`peername`、
本地地址、连接/最近活动/断开时间、实时连接时长、连接状态、收发字节数、
收发完整报文数、断开原因和异常。时间字段均为 Unix 时间戳（秒）。

`on_activity(connection, activity)` 在每次成功接收或发送一条完整的 DL/T 645
报文时触发；`activity.direction` 为 `"RX"` 或 `"TX"`，`activity.data` 是完整
原始报文。生命周期回调抛出的普通异常会被记录，但不会中断设备连接。

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
