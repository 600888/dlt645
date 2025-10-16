#ifndef DLT645_CLIENT_API_H
#define DLT645_CLIENT_API_H

#include <vector>
#include <cstdint>
#include <memory>
#include <chrono>
#include <string>
#include <future>
#include <boost/asio.hpp>

namespace dlt645 {
    namespace transport {
        namespace client {

            // 前向声明
            class TcpClient;
            class RtuClient;

            // 连接接口定义
            class Connection {
            public:
                virtual ~Connection() = default;

                // 连接设备（异步）
                virtual std::future<bool> connectAsync() = 0;

                // 断开连接（异步）
                virtual std::future<void> disconnectAsync() = 0;

                // 发送请求并等待响应（异步）
                virtual std::future<std::vector<uint8_t>> sendRequestAsync(const std::vector<uint8_t>& frame) = 0;

                // 检查连接状态
                virtual bool isConnected() const = 0;

                // 设置超时时间
                virtual void setTimeout(std::chrono::milliseconds timeout) = 0;

                // 同步连接（使用connectAsync内部的超时机制）
                bool connect(std::chrono::milliseconds timeout = std::chrono::seconds(5))
                {
                    // 设置超时时间
                    setTimeout(timeout);
                    auto future = connectAsync();
                    return future.get();
                }

                // 同步断开连接
                void disconnect() { disconnectAsync().get(); }

                // 同步发送请求
                std::vector<uint8_t> sendRequest(const std::vector<uint8_t>& frame) { return sendRequestAsync(frame).get(); }
            };

            // 客户端配置基类
            struct ClientConfig {
                std::chrono::milliseconds timeout = std::chrono::seconds(5); // 默认超时时间5秒
            };

            // TCP客户端配置
            struct TcpClientConfig : public ClientConfig {
                std::string ip = "127.0.0.1";
                uint16_t port = 10521;
            };

            // RTU客户端配置
            struct RtuClientConfig : public ClientConfig {
                std::string port = "/dev/ttyS0";
                int baudRate = 9600;
                int dataBits = 8;
                int stopBits = 1;
                std::string parity = "none"; // "none", "even", "odd"
                int flowControl = 0;         // 0: none, 1: software, 2: hardware
            };

            // TCP客户端实现
            class TcpClient : public Connection {
            public:
                TcpClient();
                ~TcpClient();

                // 配置TCP客户端
                bool configure(const TcpClientConfig& config);

                // 实现Connection接口
                std::future<bool> connectAsync() override;
                std::future<void> disconnectAsync() override;
                std::future<std::vector<uint8_t>> sendRequestAsync(const std::vector<uint8_t>& frame) override;
                bool isConnected() const override;
                void setTimeout(std::chrono::milliseconds timeout) override;

            private:
                TcpClientConfig config_;
                std::shared_ptr<boost::asio::io_context> io_context_;
                std::unique_ptr<boost::asio::ip::tcp::socket> socket_;
                std::atomic<bool> isConnected_;
                std::thread io_thread_;

                // 确保io_context运行
                void ensureIoContextRunning();
            };

            // RTU客户端实现
            class RtuClient : public Connection {
            public:
                RtuClient();
                ~RtuClient();

                // 配置RTU客户端
                bool configure(const RtuClientConfig& config);

                // 实现Connection接口
                std::future<bool> connectAsync() override;
                std::future<void> disconnectAsync() override;
                std::future<std::vector<uint8_t>> sendRequestAsync(const std::vector<uint8_t>& frame) override;
                bool isConnected() const override;
                void setTimeout(std::chrono::milliseconds timeout) override;

            private:
                RtuClientConfig config_;
                std::shared_ptr<boost::asio::io_context> io_context_;
                std::unique_ptr<boost::asio::serial_port> serial_port_;
                std::atomic<bool> isConnected_;
                std::thread io_thread_;

                // 确保io_context运行
                void ensureIoContextRunning();

                // 配置串口参数
                bool configureSerialPort(boost::asio::serial_port& port, const RtuClientConfig& config);
            };

        } // namespace client
    } // namespace transport
} // namespace dlt645

#endif // DLT645_CLIENT_API_H