#ifndef DLT645_CLIENT_SERVICE_H
#define DLT645_CLIENT_SERVICE_H
#include "dlt645/model/data_item.h"
#include "dlt645/protocol/protocol.h"
#include "dlt645/transport/client/client_api.h"
#include <array>
#include <chrono>
#include <cstdint>
#include <future>
#include <memory>
#include <thread>
#include <vector>

namespace dlt645 {
    namespace service {

        class ClientService {
        public:
            // 构造函数
            ClientService(std::shared_ptr<transport::client::Connection> conn);
            ~ClientService();

            // 创建TCP客户端服务
            static std::shared_ptr<ClientService> createTcpClient(const std::string& ip,
                                                                  uint16_t port,
                                                                  std::chrono::milliseconds timeout
                                                                  = std::chrono::milliseconds(5000));

            // 创建RTU客户端服务
            static std::shared_ptr<ClientService> createRtuClient(const std::string& port,
                                                                  int baudrate,
                                                                  int databits = 8,
                                                                  int stopbits = 1,
                                                                  const std::string& parity = "none",
                                                                  std::chrono::milliseconds timeout
                                                                  = std::chrono::milliseconds(5000));

            // 设置设备地址
            bool setAddress(const std::array<uint8_t, 6>& address);

            // 设置设备密码
            void setPassword(const std::array<uint8_t, 4>& password);

            // 读取电能（00类）
            std::shared_ptr<model::DataItem> read00(uint32_t di);

            // 读取最大需量及发生时间（01类）
            std::shared_ptr<model::DataItem> read01(uint32_t di);

            // 读取变量（02类）
            std::shared_ptr<model::DataItem> read02(uint32_t di);

            // 读取通讯地址
            std::shared_ptr<model::DataItem> readAddress();

            // 写入通讯地址
            std::shared_ptr<model::DataItem> writeAddress(const std::array<uint8_t, 6>& newAddress);

            // 更改密码
            bool changePassword(const std::array<uint8_t, 4>& oldPassword, const std::array<uint8_t, 4>& newPassword);

            // 广播校时
            bool broadcastTimeSync();

            // 连接设备
            bool connect() { return connection_->connect(); }

            // 断开连接
            void disconnect() { connection_->disconnect(); }

        private:
            std::array<uint8_t, 6> address_ = { 0 };
            std::array<uint8_t, 4> password_ = { 0 };
            std::shared_ptr<transport::client::Connection> connection_;
            std::unique_ptr<std::thread> executor_;
            std::mutex mutex_;

            // 验证设备
            bool validateDevice(const std::array<uint8_t, 6>& addr) const;

            // 发送请求并处理响应（带超时控制）
            std::shared_ptr<model::DataItem> sendAndHandleRequest(const std::vector<uint8_t>& frame,
                                                                  std::chrono::milliseconds timeout = std::chrono::seconds(5));

            // 处理响应
            std::shared_ptr<model::DataItem> handleResponse(const std::shared_ptr<protocol::Frame>& frame);

            // 从字节数据获取时间
            std::chrono::system_clock::time_point getTime(const std::vector<uint8_t>& t) const;
        };

    } // namespace service
} // namespace dlt645

#endif // DLT645_CLIENT_SERVICE_H