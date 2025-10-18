#include "dlt645/model/data_item.h"
#include "dlt645/model/model.h"
#include "dlt645/service/server_service.h"
#include <chrono>
#include <iostream>
#include <thread>

using namespace dlt645;

int main()
{
    try {
        std::cout << "Starting DLT645 RTU Server Example..." << std::endl;

        // 创建RTU服务端
        auto server = service::createRtuServer("/dev/ttyV0", 9600, 8, 1, "none");
        if (!server) {
            std::cerr << "Failed to create RTU server" << std::endl;
            return 1;
        }

        server->setAddress({ 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 });
        server->set00(0x00000000, 1234.56f);    // 电能
        server->set01(0x01010000, model::Demand(75.0f, std::chrono::system_clock::now()));
        server->set02(0x02010100, 100.5f); 
        // 启动服务
        if (!server->start()) {
            std::cerr << "Failed to start server" << std::endl;
            return 1;
        }

        std::cout << "RTU server started successfully on port /dev/ttyUSB0" << std::endl;
        std::cout << "Waiting for RTU client requests..." << std::endl;
        std::cout << "Press Enter to stop server..." << std::endl;

        // 等待用户输入停止服务
        std::cin.get();

        // 停止服务
        server->stop();
        std::cout << "Server stopped" << std::endl;

        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Exception: " << e.what() << std::endl;
        return 1;
    }
}