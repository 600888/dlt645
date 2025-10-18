#include "dlt645/common/transform.h"
#include "dlt645/model/data_item.h"
#include "dlt645/service/client_service.h"
#include <chrono>
#include <iostream>
#include <thread>

using namespace dlt645;

int main()
{
    try {
        std::cout << "Starting DLT645 RTU Client Example..." << std::endl;

        // 创建RTU客户端服务
        auto client = service::ClientService::createRtuClient("/dev/ttyV1", 9600, 8, 1, "none");
        if (!client) {
            std::cerr << "Failed to create RTU client" << std::endl;
            return 1;
        }

        // 设置设备地址
        client->setAddress({ 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 });

        // 设置默认密码
        std::array<uint8_t, 4> password = { 0x00, 0x00, 0x00, 0x00 };
        client->setPassword(password);

        // 连接到设备
        std::cout << "Connecting to device..." << std::endl;
        bool connected = client->connect();
        if (!connected) {
            std::cerr << "Failed to connect to device" << std::endl;
            return 1;
        }
        std::cout << "Connected successfully" << std::endl;

        // 读取设备地址
        std::cout << "Reading device address..." << std::endl;
        auto addressData = client->readAddress();
        if (addressData) {
            std::cout << "Device address: " << std::endl;
            if (std::holds_alternative<std::string>(addressData->value)) {
                std::cout << "  Address: " << std::get<std::string>(addressData->value) << std::endl;
            }
        } else {
            std::cout << "Failed to read device address" << std::endl;
        }

        // 读取电能数据
        std::cout << "Reading energy data..." << std::endl;
        auto energyData = client->read00(0x00000000);
        if (energyData) {
            std::cout << "Energy data: " << std::endl;
            std::cout << "  Name: " << energyData->name << std::endl;
            std::cout << "  Format: " << energyData->dataFormat << std::endl;
            std::cout << "  Unit: " << energyData->unit << std::endl;
            if (std::holds_alternative<float>(energyData->value)) {
                std::cout << "  Value: " << std::get<float>(energyData->value) << std::endl;
            }
        } else {
            std::cout << "Failed to read energy data" << std::endl;
        }

        // 读取需量数据
        std::cout << "Reading demand data..." << std::endl;
        auto demandData = client->read01(0x01010000);
        if (demandData) {
            std::cout << "Demand data: " << std::endl;
            std::cout << "  Name: " << demandData->name << std::endl;
            std::cout << "  Format: " << demandData->dataFormat << std::endl;
            std::cout << "  Unit: " << demandData->unit << std::endl;
            // 判断是否为需量
            if (std::holds_alternative<model::Demand>(demandData->value)) {
                auto demand = std::get<model::Demand>(demandData->value);
                std::cout << "  Value: " << demand.value << std::endl;
                std::cout << "  Timestamp: " << demand.occurTime.time_since_epoch().count() << std::endl;
            }
        } else {
            std::cout << "Failed to read demand data" << std::endl;
        }

        // 读取变量数据
        std::cout << "Reading variable data..." << std::endl;
        auto variableData = client->read02(0x02010100);
        if (variableData) {
            std::cout << "Variable data: " << std::endl;
            std::cout << "  Name: " << variableData->name << std::endl;
            std::cout << "  Format: " << variableData->dataFormat << std::endl;
            std::cout << "  Unit: " << variableData->unit << std::endl;
            if (std::holds_alternative<float>(variableData->value)) {
                std::cout << "  Value: " << std::get<float>(variableData->value) << std::endl;
            }
        } else {
            std::cout << "Failed to read variable data" << std::endl;
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