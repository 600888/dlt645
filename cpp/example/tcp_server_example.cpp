#include "dlt645/model/model.h"
#include "dlt645/model/data_item.h"
#include "dlt645/service/server_service.h"
#include <chrono>
#include <iostream>
#include <thread>
#include <map>

using namespace dlt645;

int main()
{
    try
    {
        std::cout << "Starting DLT645 TCP Server Example..." << std::endl;

        // 创建TCP服务端
        auto server = service::createTcpServer("0.0.0.0", 10521);
        if (!server)
        {
            std::cerr << "Failed to create TCP server" << std::endl;
            return 1;
        }

        server->setAddress({0x00, 0x00, 0x00, 0x00, 0x00, 0x00});
        server->set00(0x00000000, 1234.56f);
        server->set00(0x00000100, 220.50f);
        server->set00(0x00000200, 5.25f);
        server->set01(0x01010000, model::Demand(75.0f, std::chrono::system_clock::now()));
        server->set02(0x02010100, 100.5f);

        // 验证值是否成功写入
        auto dataItem = server->getDataItem(0x00000000);
        if (dataItem)
        {
            std::cout << "0x00000000: " << std::get<float>(dataItem->value) << std::endl;
        }
        else
        {
            std::cerr << "Failed to get data item 0x00000000" << std::endl;
        }

        // 启动服务
        if (!server->start())
        {
            std::cerr << "Failed to start server" << std::endl;
            return 1;
        }

        std::cout << "TCP server started successfully on port 10521" << std::endl;
        std::cout << "Waiting for client connections..." << std::endl;
        std::cout << "Press Enter to stop server..." << std::endl;

        // 然后等待用户输入停止服务
        std::cin.get();

        // 停止服务
        server->stop();
        std::cout << "Server stopped" << std::endl;

        return 0;
    }
    catch (const std::exception &e)
    {
        std::cerr << "Exception: " << e.what() << std::endl;
        return 1;
    }
}