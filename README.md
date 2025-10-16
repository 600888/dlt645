# DLT645协议多语言实现库

一个功能完整的DLT645电能表通信协议的多语言实现项目，同时支持C++、Python和Go三种编程语言，提供了统一的接口和功能。

# 选择语言版本

请选择您感兴趣的语言版本查看详细文档：

- C++版本(目前只支持Linux平台)
- [Python版本](python/README.md)
- [Go版本](go/README.md)

# DLT645-2007 Protocol Implementation in C++

这是一个完整的DLT645-2007电能表通信协议的C++实现，支持TCP和RTU两种通信方式，提供了完整的客户端和服务端功能。

## 项目结构

```
├── cpp/
│   ├── include/         # 头文件
│   │   └── dlt645/      # DLT645协议相关头文件
│   │       ├── common/  # 通用工具（日志、转换等）
│   │       ├── model/   # 数据模型
│   │       ├── protocol/ # 协议实现
│   │       ├── service/  # 业务服务
│   │       └── transport/# 传输层实现
│   ├── src/             # 源代码实现
│   ├── example/         # 示例程序
│   ├── third/           # 第三方库
│   ├── build/           # 构建目录
│   └── CMakeLists.txt   # CMake构建配置
└── README_CPP.md        # C++版本项目说明文档
```

## 功能特性

- 完整实现DLT645-2007协议的帧格式、校验和、数据编解码
- 支持TCP和RTU两种通信方式
- 提供客户端和服务端完整实现
- 支持异步通信
- 完善的日志系统
- 模拟设备数据（服务端）
- 简单易用的API接口

## 依赖项

- C++20 标准
- CMake 3.16+ 
- Boost >=1.81（用于Asio网络编程）
- spdlog 日志库（已包含在third目录）
- rapidjson （已包含在third目录）

## 构建步骤

1. 确保已安装必要的依赖：
   ```bash
   # Ubuntu/Debian
   sudo apt-get install cmake libboost-all-dev
   
   # CentOS/RHEL
   sudo yum install cmake boost-devel
   
   # macOS
   brew install cmake boost
   ```

2. 创建构建目录并编译项目：
   ```bash
   cd cpp
   mkdir build
   cd build
   cmake ..
   make
   ```

3. 安装（可选）：
   ```bash
   sudo make install
   ```

## 使用示例

### TCP服务端示例

启动一个DLT645 TCP服务端，监听指定端口，并提供模拟的电能表数据。

```bash
./bin/tcp_server_example
```

服务端会在端口10521上监听连接，并响应客户端的读取请求。

### TCP客户端示例

连接到DLT645 TCP服务端，读取电能表数据。

```bash
./bin/tcp_client_example
```

客户端会连接到本地的10521端口，并尝试读取电能、电压、电流等数据。

### RTU服务端示例

启动一个DLT645 RTU服务端，通过串口与客户端通信。

```bash
./bin/rtu_server_example
```

注意：需要根据实际情况修改代码中的串口配置（端口名、波特率等）。

### RTU客户端示例

通过串口连接到DLT645 RTU服务端，读取电能表数据。

```bash
./bin/rtu_client_example
```

注意：需要根据实际情况修改代码中的串口配置（端口名、波特率等）。

## 代码示例

### 创建TCP客户端

```cpp
#include "dlt645/service/client_service.h"

// 创建TCP客户端
auto client = service::ClientService::createTcpClient("127.0.0.1", 10521);

// 设置设备地址
std::array<uint8_t, 6> deviceAddr = {0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC};
client->setAddress(deviceAddr);

// 设置密码
std::array<uint8_t, 4> password = {0x00, 0x00, 0x00, 0x00};
client->setPassword(password);

// 连接设备
bool connected = client->connect();

// 读取电能数据(00类)
auto energyData = client->read00(0x00000001);

// 读取最大需量数据(01类)
auto demandData = client->read01(0x01000100);

// 读取变量数据(02类)
auto variableData = client->read02(0x02010100);

// 读取通讯地址
auto addressData = client->readAddress();

// 广播校时
client->broadcastTimeSync();

// 断开连接
client->disconnect();
```

### 创建TCP服务端

```cpp
#include "dlt645/service/server_service.h"

// 创建TCP服务端
auto server = service::ServerService::createTcpServer("0.0.0.0", 10521);

// 注册设备
std::array<uint8_t, 6> deviceAddr = {0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC};
server->registerDevice(deviceAddr);
server->setAddress(deviceAddr);

// 设置密码
std::array<uint8_t, 4> password = {0x00, 0x00, 0x00, 0x00};
server->setPassword(password);

// 设置电能量数据(00类)
server->set00(0x00000001, 100.5);

// 设置变量数据(02类)
server->set02(0x02010100, 220.0);

// 启动服务
server->start();

// 当需要停止服务时
server->stop();
```

## 接口说明

### 客户端主要接口

- **createTcpClient**：创建TCP客户端连接
- **createRtuClient**：创建RTU客户端连接
- **setAddress**：设置设备地址
- **setPassword**：设置设备密码
- **connect**：连接到设备
- **read00**：读取电能量数据(00类)
- **read01**：读取最大需量数据(01类)
- **read02**：读取变量数据(02类)
- **readAddress**：读取通讯地址
- **writeAddress**：写入通讯地址
- **changePassword**：修改密码
- **broadcastTimeSync**：广播校时
- **disconnect**：断开连接

### 服务端主要接口

- **createTcpServer**：创建TCP服务端
- **createRtuServer**：创建RTU服务端
- **registerDevice**：注册设备
- **validateDevice**：验证设备地址
- **setAddress**：设置设备地址
- **setPassword**：设置设备密码
- **set00**：设置电能量数据
- **set01**：设置最大需量及发生时间
- **set02**：设置变量数据
- **start**：启动服务
- **stop**：停止服务

## 注意事项

1. RTU模式需要正确配置串口参数，包括端口名、波特率、数据位、停止位和校验位
2. 示例程序中的设备地址和密码使用了默认值，实际使用时需要根据设备情况修改
3. 服务端示例提供了简单的模拟数据，实际应用中可能需要连接到真实的设备或数据库
4. 在生产环境中，请确保正确处理异常和错误情况
5. 接口定义可能会随着版本更新而变化，请以最新的头文件为准