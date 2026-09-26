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
| **冻结命令、通信速率变更** 🐾 | ✅ |
| **电能量** 🐾  | ✅  |
| **最大需量及发生时间** 🐾         | ✅ |
| **变量** 🐾                | ✅ |
| **参变量（04 类）** 🐾            | ✅ |
| **事件记录（03 类）** 🐾                 | ✅* |
| **冻结量** 🐾               | ❌ |
| **负荷纪录** 🐾           | ❌ |

通信速率变更目前完成协议应答与模拟表状态更新；实际 RTU 串口的波特率需要调用方重新配置。
*单帧数据域上限为 255 字节；超长事件记录尚需分帧读取。*


## 选择语言版本

请选择您感兴趣的语言版本查看详细文档：

- C++版本（支持 Linux、Windows 和 macOS）
- [Python版本](../python/README.md)
- [Go版本](../go/README.md)

## DL/T645-2007协议C++实现库

该 C++ 实现支持 TCP 和 RTU 客户端及服务端，覆盖 00–04 类数据和部分管理命令。

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

- 实现DLT645-2007协议的帧格式、校验和及已支持数据类的编解码
- 支持TCP和RTU两种通信方式
- 提供客户端和服务端实现
- 传输层支持异步通信
- 完善的日志系统
- 模拟设备数据（服务端）
- 简单易用的API接口

## 依赖项

- C++17 标准
- CMake 3.20+
- Boost >=1.83（用于Asio网络编程）
- spdlog 日志库（已包含在third目录）
- 数据项定义编译在 C++ 静态表中；维护时从 Python 版定义重新生成（见下文）
- 默认构建动态库；安装包包含库文件、头文件和 CMake 包配置

## 数据定义维护

C++ 已实现的 00–04 类数据以 Python 版的 `python/src/config/` 定义为维护源。在仓库根目录运行以下命令，更新 C++ 头文件，并将生成结果与 Python 定义一起提交：

```bash
python cpp/tools/generate_type_definitions.py
```

生成结果位于 `cpp/include/dlt645/model/type_definitions.h`。C++ 编译及运行时无需 Python 或额外的数据配置文件。

03/04 类使用 `read03`、`read04`、`write04` 和服务端的 `set03`、`set04`。`DataItem::fields` 按 Python 定义顺序保存字段，值为定长十进制数字字符串；成对事件字段以 `first,second` 表示。04 类写入使用客户端 `setPassword` 设置的四字节密码，并自动附加全零操作者代码。

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
   cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
   cmake --build build --config Release
   ctest --test-dir build -C Release --output-on-failure
   ```

3. 安装（可选）：
   ```bash
   cmake --install build --config Release --prefix ./build/stage
   ```

## 在其他 C++ 项目中使用动态库

先构建并安装本库，或从 GitHub Actions 的 `C++ shared library` 运行记录下载与目标系统、架构匹配的安装包。安装目录包含 `include/` 头文件、`lib/` 链接库与 CMake 包配置；Windows DLL 位于 `bin/`。调用方还需要 Boost 1.83 或更新版本的头文件。

在调用方项目中新建 `main.cpp`：

```cpp
#include "dlt645/common/transform.h"
#include <cstdint>
#include <iostream>
#include <vector>

int main()
{
    const std::vector<uint8_t> bytes{0x01, 0x23, 0x45};
    std::cout << dlt645::common::bytesToHexString(bytes) << '\n';
}
```

对应的 `CMakeLists.txt`：

```cmake
cmake_minimum_required(VERSION 3.20)
project(meter_demo LANGUAGES CXX)

find_package(dlt645 1 CONFIG REQUIRED)
add_executable(meter_demo main.cpp)
target_link_libraries(meter_demo PRIVATE dlt645::dlt645)
```

在调用方项目目录中配置并编译，其中 `<安装目录>` 可填本地的 `cpp/build/stage` 或下载后解压的目录：

```bash
cmake -S . -B build -DCMAKE_PREFIX_PATH="<安装目录>"
cmake --build build --config Release
```

如果 Boost 不在系统默认位置，再向配置命令添加 `-DBoost_ROOT=<Boost目录>`。Linux 和 macOS 可直接运行构建目录中的 `./build/meter_demo`；CMake 会为构建目录配置动态库搜索路径。

运行时系统必须能找到动态库：

| 平台 | 动态库及使用方式 |
| --- | --- |
| Windows MSVC | 将安装包 `bin/dlt645.dll` 放在 `meter_demo.exe` 同目录，或将安装包 `bin` 加入 `PATH`；CMake 自动链接 `lib/dlt645.lib`。 |
| Windows MinGW | 将 `bin/libdlt645.dll` 放在程序同目录或加入 `PATH`；CMake 链接 `lib/libdlt645.dll.a`。调用方需使用兼容的 MinGW 工具链。 |
| Linux | 动态库为 `lib/libdlt645.so`（以及版本号文件）；部署时将 `lib` 加入系统库搜索路径，或给可执行文件设置相对 RPATH。 |
| macOS | 动态库为 `lib/libdlt645.dylib`（以及版本号文件）；部署时给可执行文件设置相对 RPATH。 |

Linux 和 macOS 安装包内的示例程序已配置相对于 `bin/` 的库搜索路径。将自己的程序与库一同打包时，Linux 可使用 `$ORIGIN/../lib`，macOS 可使用 `@loader_path/../lib`；Windows 则将 DLL 放在程序旁边。MSVC 与 MinGW 的导入库不能混用。

例如在 Windows 的 Visual Studio Release 构建中，可使用 PowerShell 将 DLL 复制到程序旁边后运行：

```powershell
Copy-Item "<安装目录>\bin\dlt645.dll" .\build\Release\
.\build\Release\meter_demo.exe
```

GitHub Actions 的 `C++ shared library` 工作流在 Linux x64、Windows x64、macOS x64 和 macOS arm64 上构建、测试并上传独立安装包。产物可在对应的 Actions 运行记录中下载。

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
