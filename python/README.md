# DL/T645-2007协议多语言实现库

一个功能完整的DL/T645-2007电能表通信协议的多语言实现项目，同时支持C++、Python和Go三种编程语言，提供了统一的接口和功能。

## 🌴通讯支持

| 功能                            | 状态 |
| ------------------------------- | ---- |
| **TCP客户端** 🐾 | ✅    |
| **TCP服务端** 🐾 | ✅    |
| **RTU主站** 🐾                   | ✅    |
| **RTU从站** 🐾                   | ✅    |

## 🌴 功能完成情况

| 功能                                           | 状态 |
| ---------------------------------------------- | -- |
| **读、写通讯地址** 🐾  | ✅  |
| **修改密码** 🐾  | ✅  |
| **广播校时** 🐾  | ✅  |
| **电能量** 🐾  | ✅  |
| **最大需量及发生时间** 🐾         | ✅ |
| **变量** 🐾                | ✅ |
| **读、写参变量** 🐾            | ✅ |
| **事件记录** 🐾                 | ✅ |
| **冻结量** 🐾               | ❌ |
| **负荷纪录** 🐾           | ❌ |


## 选择语言版本

请选择您感兴趣的语言版本查看详细文档：

- [C++版本](../cpp/README.md)
- Python版本
- [Go版本](../go/README.md)

## DL/T645-2007协议Python实现库

一个功能完整的DL/T645-2007电能表通信协议Python实现库，支持TCP和RTU两种通信方式，可用于电能表数据读写和通信测试。

## 功能特性

- 🌐 **多种通信方式**：支持TCP和RTU（串口）通信
- 📊 **完整协议支持**：实现DL/T645-2007协议的主要功能
- 🔌 **客户端/服务端**：同时提供客户端和服务端功能
- 📈 **多种数据类型**：支持电能量、最大需量、变量数据读写
- 🛡️ **设备认证**：支持设备地址验证和密码保护
- 📝 **完善日志**：内置日志系统，便于调试
- 🎯 **易于使用**：简洁的API设计，快速上手

## 支持的数据类型

- **电能量数据**（00类）：正向有功电能、反向有功电能等
- **最大需量数据**（01类）：最大需量及发生时间
- **变量数据**（02类）：实时电压、电流、功率等
- **参变量数据**（04类）：设备参数、配置信息等

## 安装

```bash
pip install dlt645
```

### 文档地址

**https://600888.github.io/dlt645**

![](../resource/python/6.png)

## 快速开始

### 创建TCP服务器

```python
from dlt645 import MeterServerService

# 创建TCP服务器
server_svc = MeterServerService.new_tcp_server("127.0.0.1", 8021, 3000)

# 设置设备地址
dlt645_svc.set_address("123456781012")

# 设置密码
dlt645_svc.set_password("00123456")

# 写电能
dlt645_svc.set_00(0x00000000, 50.5)

# 写最大需量
dlt645_svc.set_01(
    0x01010000,
    Demand(78.0, datetime.strptime("2023-01-01 12:00:00", "%Y-%m-%d %H:%M:%S")),
)

# 写变量
dlt645_svc.set_02(0x02010100, 66.6)

# 设置事件记录
dlt645_svc.set_03(
    0x03010000,
    [
        ("000015", "000012"),  # A相失压总次数、累计时间
        ("000025", "000024"),  # B相失压总次数、累计时间
        ("000034", "000030"),  # C相失压总次数、累计时间
    ],
)

# 写参变量
dlt645_svc.set_04(0x04000101, "25110201")  # 2025年11月2日星期一
dlt645_svc.set_04(0x04000204, "10")  # 设置费率数为10

schedule_list = []
schedule_list.append("120901")
schedule_list.append("120902")
schedule_list.append("120903")
schedule_list.append("120904")
schedule_list.append("120905")
schedule_list.append("120906")
schedule_list.append("120907")
schedule_list.append("120908")
schedule_list.append("120909")
schedule_list.append("120910")
schedule_list.append("120911")
schedule_list.append("120912")
schedule_list.append("120913")
schedule_list.append("120914")
dlt645_svc.set_04(0x04010000, schedule_list)  # 第一套时区表数据

# 启动服务器
server_svc.server.start()
```

![](../resource/python/1.png)

### 创建RTU服务器

```python
from dlt645 import MeterServerService

# 创建RTU服务器
server_svc = MeterServerService.new_rtu_server(port="COM11",data_bits=8,stop_bits=1,baud_rate=9600,parity="N",timeout=1.0)

# 设置设备地址
dlt645_svc.set_address("123456781012")

# 设置密码
dlt645_svc.set_password("00123456")

# 写电能
dlt645_svc.set_00(0x00000000, 50.5)

# 写最大需量
dlt645_svc.set_01(
    0x01010000,
    Demand(78.0, datetime.strptime("2023-01-01 12:00:00", "%Y-%m-%d %H:%M:%S")),
)

# 写变量
dlt645_svc.set_02(0x02010100, 66.6)

# 设置事件记录
dlt645_svc.set_03(
    0x03010000,
    [
        ("000015", "000012"),  # A相失压总次数、累计时间
        ("000025", "000024"),  # B相失压总次数、累计时间
        ("000034", "000030"),  # C相失压总次数、累计时间
    ],
)

# 写参变量
dlt645_svc.set_04(0x04000101, "25110201")  # 2025年11月2日星期一
dlt645_svc.set_04(0x04000204, "10")  # 设置费率数为10

schedule_list = []
schedule_list.append("120901")
schedule_list.append("120902")
schedule_list.append("120903")
schedule_list.append("120904")
schedule_list.append("120905")
schedule_list.append("120906")
schedule_list.append("120907")
schedule_list.append("120908")
schedule_list.append("120909")
schedule_list.append("120910")
schedule_list.append("120911")
schedule_list.append("120912")
schedule_list.append("120913")
schedule_list.append("120914")
dlt645_svc.set_04(0x04010000, schedule_list)  # 第一套时区表数据

# 启动服务器
server_svc.server.start()
```

![](../resource/python/2.png)

### 创建TCP客户端

```python
from dlt645 import MeterClientService

client_svc = MeterClientService.new_tcp_client("127.0.0.1", 10521, timeout=1)

# 设置设备密码(0级)
client_svc.set_password("00123456")

# 读取通讯地址
address_data = client_svc.read_address()
if address_data and hasattr(address_data, "value"):
    print(f"通讯地址: {address_data.value}")
else:
    print("读取通讯地址失败")

# 设置设备地址
client_svc.set_address(address_data.value)

# 读取电能数据
data_item = client_svc.read_00(0x00000000)
print(f"电能数据: {data_item}")

# 读取最大需量及发生时间
data_item2 = client_svc.read_01(0x01010000)
print(f"最大需量及发生时间: {data_item2}")

# 读取变量数据
data_item3 = client_svc.read_02(0x02010100)
print(f"变量数据: {data_item3}")

# 读取事件记录数据
data_item4 = client_svc.read_03(0x03010000)
print(f"事件记录数据: {data_item4}")

# 读取参变量
data_item5 = client_svc.read_04(0x04000101)
print(f"日期及星期: {data_item5}")

data_item6 = client_svc.read_04(0x04000204)
print(f"费率数: {data_item6}")

# 读取时区表数据
data_item7 = client_svc.read_04(0x04010000)
for item in data_item7:
    print(item)

# 读取公共假日日期及时段表号
data_item8 = client_svc.read_04(0x04030001)
print(f"公共假日日期及时段表号: {data_item8}")

# 修改密码
client_svc.change_password("00123456", "04123456")

# 写参变量
data_item9 = client_svc.write_04(
    0x04000101, "25120901", password="04123456"
)  # 写日期及星期

```

![](../resource/python/3.png)

### 创建RTU客户端

```python
from dlt645 import MeterClientService

# 创建RTU客户端
client = MeterClientService.new_rtu_client(
    port="COM10",
    baudrate=9600,
    databits=8,
    stopbits=1,
    parity="N",
    timeout=0.5
)

# 设置设备密码(0级)
client_svc.set_password("00123456")

# 读取通讯地址
address_data = client_svc.read_address()
if address_data and hasattr(address_data, "value"):
    print(f"通讯地址: {address_data.value}")
else:
    print("读取通讯地址失败")

# 设置设备地址
client_svc.set_address(address_data.value)

# 读取电能数据
data_item = client_svc.read_00(0x00000000)
print(f"电能数据: {data_item}")

# 读取最大需量及发生时间
data_item2 = client_svc.read_01(0x01010000)
print(f"最大需量及发生时间: {data_item2}")

# 读取变量数据
data_item3 = client_svc.read_02(0x02010100)
print(f"变量数据: {data_item3}")

# 读取事件记录数据
data_item4 = client_svc.read_03(0x03010000)
print(f"事件记录数据: {data_item4}")

# 读取参变量
data_item5 = client_svc.read_04(0x04000101)
print(f"日期及星期: {data_item5}")

data_item6 = client_svc.read_04(0x04000204)
print(f"费率数: {data_item6}")

# 读取时区表数据
data_item7 = client_svc.read_04(0x04010000)
for item in data_item7:
    print(item)

# 读取公共假日日期及时段表号
data_item8 = client_svc.read_04(0x04030001)
print(f"公共假日日期及时段表号: {data_item8}")

# 修改密码
client_svc.change_password("00123456", "04123456")

# 写参变量
data_item9 = client_svc.write_04(
    0x04000101, "25120901", password="04123456"
)  # 写日期及星期

```
![](../resource/python/4.png)

### 使用第三方工具测试

测试效果

![](../resource/python/5.gif)

## API参考

### 服务器端API

#### MeterServerService

主要的服务器服务类，提供以下方法：
- `new_tcp_server(ip: str, port: int, timeout: float)` - 创建TCP服务器（类方法）
- `new_rtu_server(port: str, data_bits: int, stop_bits: int, baud_rate: int, parity: str, timeout: float)` - 创建RTU服务器（类方法）
- `set_00(di: int, value: float)` - 设置电能量数据
- `set_01(di: int, demand: Demand)` - 设置最大需量数据
- `set_02(di: int, value: float)` - 设置变量数据
- `set_03(di: int, value: list)` - 设置事件记录数据
- `set_04(di: int, value: float)` - 设置参变量数据
- `set_address(address: str)` - 设置设备地址
- `set_password(password: str)` - 设置密码
- `change_password(old_password: str, new_password: str)` - 修改密码

### 客户端API

#### MeterClientService

主要的客户端服务类，提供以下方法：

- `new_tcp_client(ip: str, port: int, timeout: float)` - 创建TCP客户端（类方法）
- `new_rtu_client(port: str, baudrate: int, databits: int, stopbits: int, parity: str, timeout: float)` - 创建RTU客户端（类方法）
- `read_00(di: int)` - 读取电能量数据
- `read_01(di: int)` - 读取最大需量数据
- `read_02(di: int)` - 读取变量数据
- `read_04(di: int)` - 读取参变量数据
- `write_04(di: int, value: str, password: str)` - 写入参变量数据
- `read_address()` - 读取设备地址
- `write_address(new_address: str)` - 写入设备地址
- `set_address(address: str)` - 设置本地设备地址
- `set_password(password: str)` - 设置密码
- `change_password(old_password: str, new_password: str)` - 修改密码

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
- `0x02020300` - C相电流

### 参变量数据（04类）
- `0x04000101` - 日期及星期(0代表星期天)
- `0x04000102` - 时间

## 配置文件

库包含了丰富的配置文件，定义了各种数据类型：

- `config/energy_types.json` - 电能量数据类型配置
- `config/demand_types.json` - 最大需量数据类型配置  
- `config/variable_types.json` - 变量数据类型配置
- `config/event_record_types.json` - 事件记录数据类型配置
- `config/parameter_types.json` - 参变量数据类型配置

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