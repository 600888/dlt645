# DLT645协议多语言实现库

一个功能完整的DLT645电能表通信协议的多语言实现项目，同时支持C++、Python和Go三种编程语言，提供了统一的接口和功能。

# 选择语言版本

请选择您感兴趣的语言版本查看详细文档：

- [C++版本](../README.md)
- Python版本
- [Go版本](../go/README.md)

# DLT645协议Python实现库

一个功能完整的DLT645电能表通信协议Python实现库，支持TCP和RTU两种通信方式，可用于电能表数据读写和通信测试。

## 功能特性

- 🌐 **多种通信方式**：支持TCP和RTU（串口）通信
- 📊 **完整协议支持**：实现DLT645协议的主要功能
- 🔌 **客户端/服务端**：同时提供客户端和服务端功能
- 📈 **多种数据类型**：支持电能量、最大需量、变量数据读写
- 🛡️ **设备认证**：支持设备地址验证和密码保护
- 📝 **完善日志**：内置日志系统，便于调试
- 🎯 **易于使用**：简洁的API设计，快速上手

## 支持的数据类型

- **电能量数据**（00类）：正向有功电能、反向有功电能等
- **最大需量数据**（01类）：最大需量及发生时间
- **变量数据**（02类）：实时电压、电流、功率等

## 安装

```bash
pip install dlt645
```

## 快速开始

### 创建TCP服务器

```python
from dlt645 import new_tcp_server

# 创建TCP服务器
server_service = new_tcp_server("127.0.0.1", 8021, 3000)

# 设置电能量数据
server_service.set_00(0x00000000, 100.0)

# 设置变量数据
server_service.set_02(0x02010100, 86.0)

# 启动服务器
server_service.server.start()
```

### 创建RTU服务器

```python
from dlt645 import new_rtu_server

# 创建RTU服务器
server_service = new_rtu_server("COM4", 8, 1, 9600, "N", 1000)

# 设置数据
server_service.set_00(0x00000000, 100.0)
server_service.set_02(0x02010100, 86.0)

# 启动服务器
server_service.server.start()
```

### 创建TCP客户端

```python
from dlt645 import MeterClientService

# 创建TCP客户端
client = MeterClientService.new_tcp_client("127.0.0.1", 8021, 30.0)

# 设置设备地址
client.set_address(b'\x00\x00\x00\x00\x00\x00')

# 读取电能量数据
data = client.read_01(0x00000000)
if data:
    print(f"电能量: {data.value}")

# 读取变量数据
data = client.read_03(0x02010100)
if data:
    print(f"变量值: {data.value}")
```

### 创建RTU客户端

```python
from dlt645 import MeterClientService

# 创建RTU客户端
client = MeterClientService.new_rtu_client(
    port="COM4",
    baudrate=9600,
    databits=8,
    stopbits=1,
    parity="N",
    timeout=30.0
)

# 设置设备地址
client.set_address(b'\x01\x02\x03\x04\x05\x06')

# 读取数据
data = client.read_01(0x00000000)
```

## API参考

### 服务器端API

#### MeterServerService

主要的服务器服务类，提供以下方法：

- `set_00(di: int, value: float)` - 设置电能量数据
- `set_01(di: int, demand: Demand)` - 设置最大需量数据
- `set_02(di: int, value: float)` - 设置变量数据
- `set_address(address: bytearray)` - 设置设备地址
- `set_password(password: bytearray)` - 设置密码

#### 便捷函数

- `new_tcp_server(ip: str, port: int, timeout: int)` - 创建TCP服务器
- `new_rtu_server(port: str, dataBits: int, stopBits: int, baudRate: int, parity: str, timeout: float)` - 创建RTU服务器

### 客户端API

#### MeterClientService

主要的客户端服务类，提供以下方法：

- `new_tcp_client(ip: str, port: int, timeout: float)` - 创建TCP客户端（类方法）
- `new_rtu_client(port: str, baudrate: int, databits: int, stopbits: int, parity: str, timeout: float)` - 创建RTU客户端（类方法）
- `read_01(di: int)` - 读取电能量数据
- `read_02(di: int)` - 读取最大需量数据
- `read_03(di: int)` - 读取变量数据
- `read_address()` - 读取设备地址
- `write_address(new_address: bytes)` - 写入设备地址
- `set_address(address: bytes)` - 设置本地设备地址
- `set_password(password: bytes)` - 设置密码

## 数据标识说明

DLT645协议使用4字节的数据标识来标识不同的数据项：

### 电能量数据（00类）
- `0x00000000` - 总有功电能
- `0x00010000` - 正向有功电能
- `0x00020000` - 反向有功电能

### 最大需量数据（01类）  
- `0x01000000` - 总最大需量
- `0x01010000` - 正向最大需量

### 变量数据（02类）
- `0x02010100` - A相电压
- `0x02010200` - B相电压
- `0x02010300` - C相电压
- `0x02020100` - A相电流
- `0x02020200` - B相电流

## 配置文件

库包含了丰富的配置文件，定义了各种数据类型：

- `config/energy_types.json` - 电能量数据类型配置
- `config/demand_types.json` - 最大需量数据类型配置  
- `config/variable_types.json` - 变量数据类型配置

## 开发指南

### 环境要求

- Python >= 3.7
- loguru >= 0.5.0
- pyserial >= 3.4

### 运行测试

```bash
# 安装开发依赖
pip install -e .[dev]

# 运行测试
pytest
```

### 调试日志

库使用loguru进行日志记录，可以通过以下方式启用详细日志：

```python
from loguru import logger
logger.add("dlt645.log", level="DEBUG")
```

## 常见问题

### Q: 如何处理通信超时？
A: 可以在创建客户端时设置timeout参数，或者使用try-catch捕获超时异常。

### Q: 支持哪些串口参数？
A: 支持标准的串口参数：波特率（1200-115200）、数据位（7-8）、停止位（1-2）、校验位（N/E/O）。

### Q: 如何添加自定义数据类型？
A: 可以修改config目录下的JSON配置文件，添加新的数据标识和格式定义。

## 许可证

Apache License 2.0

## 贡献

欢迎提交Issue和Pull Request！

## 联系方式

- 作者：Chen Dongyu
- 邮箱：1755696012@qq.com
- 项目地址：https://gitee.com/chen-dongyu123/dlt645