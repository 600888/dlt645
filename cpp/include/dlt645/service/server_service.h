#ifndef DLT645_SERVER_SERVICE_H
#define DLT645_SERVER_SERVICE_H

#include "dlt645/model/data_item.h"
#include "dlt645/model/model.h"
#include "dlt645/protocol/protocol.h"
#include "dlt645/transport/server/server_api.h"
#include <array>
#include <cstdint>
#include <memory>
#include <vector>
#include <optional>
#include <string>

namespace dlt645 {
    namespace service {

        class ServerService : public transport::server::ConnectionHandler, public std::enable_shared_from_this<ServerService> {
        public:
            // 构造函数
            ServerService(std::shared_ptr<transport::server::Server> server,
                          std::optional<std::array<uint8_t, 6>> address = std::nullopt,
                          std::optional<std::array<uint8_t, 4>> password = std::nullopt);

            ~ServerService() = default;

            // 设备注册
            void registerDevice(const std::array<uint8_t, 6>& addr);

            // 验证设备地址
            bool validateDevice(const std::array<uint8_t, 6>& address) const;

            // 设置时间
            void setTime(const std::vector<uint8_t>& dataBytes);

            // 写通讯地址
            void setAddress(const std::array<uint8_t, 6>& address);

            // 写电能量
            bool set00(uint32_t di, float value);

            // 写最大需量及发生时间
            bool set01(uint32_t di, const model::Demand& value);

            // 写变量
            bool set02(uint32_t di, float value);

            // 设置密码
            void setPassword(const std::array<uint8_t, 4>& password);

            // 获取数据项
            std::shared_ptr<model::DataItem> getDataItem(uint32_t di) const;

            // 处理请求
            std::vector<uint8_t> handleRequest(const protocol::Frame& frame);

            // 处理电能读取请求
            std::vector<uint8_t> handleReadEnergy(const protocol::Frame& frame);

            // 处理最大需量读取请求
            std::vector<uint8_t> handleReadDemand(const protocol::Frame& frame);

            // 处理变量读取请求
            std::vector<uint8_t> handleReadVariable(const protocol::Frame& frame);

            // 连接关闭回调
            void onConnectionClosed();

            // 启动服务
            bool start();

            // 停止服务
            void stop();

            // 获取当前地址
            const std::array<uint8_t, 6>& getAddress() const { return address_; }

            // 获取当前密码
            const std::array<uint8_t, 4>& getPassword() const { return password_; }

            // 初始化方法，用于设置连接处理器
            void init();

        private:
            std::shared_ptr<transport::server::Server> server_; // 服务器实例
            std::array<uint8_t, 6> address_;                    // 设备地址
            std::array<uint8_t, 4> password_;                   // 设备密码
        };

        // 创建TCP服务端服务
        std::shared_ptr<ServerService>
        createTcpServer(const std::string& ip, uint16_t port, std::chrono::milliseconds timeout = std::chrono::seconds(5));

        // 创建RTU服务端服务
        std::shared_ptr<ServerService> createRtuServer(const std::string& port,
                                                       int baudrate,
                                                       int databits = 8,
                                                       int stopbits = 1,
                                                       const std::string& parity = "none",
                                                       std::chrono::milliseconds timeout = std::chrono::seconds(5));

    } // namespace service
} // namespace dlt645

#endif // DLT645_SERVER_SERVICE_H