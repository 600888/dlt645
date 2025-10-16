#include "dlt645/model/model.h"
#include "dlt645/common/log.h"
#include "dlt645/service/client_service.h"
#include <iostream>
#include <string>

using namespace dlt645;

int main()
{
    try {
        std::cout << "Starting DLT645 TCP Client Example..." << std::endl;

        // 创建TCP客户端服务
        auto client = service::ClientService::createTcpClient("127.0.0.1", 10521);
        if (!client) {
            std::cerr << "Failed to create TCP client" << std::endl;
            return 1;
        }

        // 连接到设备（带5秒超时）
        std::cout << "Connecting to device with 5 seconds timeout..." << std::endl;
        bool connected = client->connect();
        if (!connected) {
            std::cerr << "Failed to connect to device: connection timeout or error" << std::endl;
            return 1;
        }
        std::cout << "Connected successfully" << std::endl;

        // 读取设备地址
        std::cout << "Reading device address..." << std::endl;
        auto addressData = client->readAddress();
        if (addressData) {
            std::cout << "Device address: " << std::endl;
            if (std::holds_alternative<std::string>(addressData->value)) {
                std::cout << fmt::format("  Address: {}", std::get<std::string>(addressData->value)) << std::endl;
            }
        } else {
            std::cout << "Failed to read device address" << std::endl;
        }

        // 读取电能数据
        std::cout << "Reading energy data..." << std::endl;
        auto energyData = client->read00(0x00000000);
        if (energyData) {
            if (std::holds_alternative<float>(energyData->value)) {
                std::cout << fmt::format("  Value: {:.2f}", std::get<float>(energyData->value)) << std::endl;
            }
        } else {
            std::cout << "Failed to read energy data" << std::endl;
        }

        // 断开连接
        client->disconnect();
        std::cout << "Disconnected from device" << std::endl;

        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << std::endl;
        return 1;
    }
}