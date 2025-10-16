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
        auto client = service::ClientService::createRtuClient("/dev/ttyUSB0", 9600, 8, 1, "none");
        if (!client) {
            std::cerr << "Failed to create RTU client" << std::endl;
            return 1;
        }

        // 设置设备地址
        std::array<uint8_t, 6> deviceAddr = { 0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC };
        client->setAddress(deviceAddr);

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

        // 读取电能数据
        std::cout << "Reading energy data..." << std::endl;
        auto energyData = client->read00(0x00000001);
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

        // 读取电压数据
        std::cout << "Reading voltage data..." << std::endl;
        auto voltageData = client->read00(0x00000002);
        if (voltageData) {
            std::cout << "Voltage data: " << std::endl;
            std::cout << "  Name: " << voltageData->name << std::endl;
            std::cout << "  Format: " << voltageData->dataFormat << std::endl;
            std::cout << "  Unit: " << voltageData->unit << std::endl;
            if (std::holds_alternative<float>(voltageData->value)) {
                std::cout << "  Value: " << std::get<float>(voltageData->value) << std::endl;
            }
        } else {
            std::cout << "Failed to read voltage data" << std::endl;
        }

        // 读取电流数据
        std::cout << "Reading current data..." << std::endl;
        auto currentData = client->read00(0x00000003);
        if (currentData) {
            std::cout << "Current data: " << std::endl;
            std::cout << "  Name: " << currentData->name << std::endl;
            std::cout << "  Format: " << currentData->dataFormat << std::endl;
            std::cout << "  Unit: " << currentData->unit << std::endl;
            if (std::holds_alternative<float>(currentData->value)) {
                std::cout << "  Value: " << std::get<float>(currentData->value) << std::endl;
            }
        } else {
            std::cout << "Failed to read current data" << std::endl;
        }

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

        // 断开连接
        client->disconnect();
        std::cout << "Disconnected from device" << std::endl;

        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << std::endl;
        return 1;
    }
}