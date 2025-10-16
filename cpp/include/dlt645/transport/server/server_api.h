#ifndef DLT645_SERVER_API_H
#define DLT645_SERVER_API_H

#include <boost/asio.hpp>
#include <chrono>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>
#include "dlt645/protocol/protocol.h" // 添加对protocol.h的引用

namespace dlt645 {
    namespace transport {
        namespace server {

            // 前向声明
            class TcpServer;
            class RtuServer;

            // 连接处理器接口定义
            class ConnectionHandler {
            public:
                virtual ~ConnectionHandler() = default;

                // 处理接收到的数据
                virtual std::vector<uint8_t> handleRequest(const protocol::Frame& frame) = 0;

                // 连接关闭时的回调
                virtual void onConnectionClosed() = 0;
            };

            // 服务器配置基类
            struct ServerConfig {
                std::chrono::milliseconds timeout = std::chrono::seconds(5); // 默认超时时间5秒
            };

            // TCP服务器配置
            struct TcpServerConfig : public ServerConfig {
                std::string ip = "0.0.0.0";
                uint16_t port = 10521;
                int maxConnections = 10; // 最大连接数
            };

            // RTU服务器配置
            struct RtuServerConfig : public ServerConfig {
                std::string port = "/dev/ttyS0";
                int baudRate = 9600;
                int dataBits = 8;
                int stopBits = 1;
                std::string parity = "none"; // "none", "even", "odd"
                int flowControl = 0;         // 0: none, 1: software, 2: hardware
            };

            // 服务器接口定义
            class Server {
            public:
                virtual ~Server() = default;

                // 启动服务器
                virtual bool start() = 0;

                // 停止服务器
                virtual void stop() = 0;

                // 检查服务器是否运行
                virtual bool isRunning() const = 0;

                // 设置连接处理器
                virtual void setConnectionHandler(std::shared_ptr<ConnectionHandler> handler) = 0;
            };

            // TCP服务器实现
            class TcpServer : public Server {
            public:
                TcpServer();
                ~TcpServer();

                // 配置TCP服务器
                bool configure(const TcpServerConfig& config);

                // 实现Server接口
                bool start() override;
                void stop() override;
                bool isRunning() const override;
                void setConnectionHandler(std::shared_ptr<ConnectionHandler> handler) override;

            private:
                TcpServerConfig config_;
                std::shared_ptr<boost::asio::io_context> io_context_;
                std::unique_ptr<boost::asio::ip::tcp::acceptor> acceptor_;
                std::atomic<bool> isRunning_;
                std::shared_ptr<ConnectionHandler> connectionHandler_;
                std::thread io_thread_;

                // 接受连接
                void acceptConnection();

                // 处理客户端连接
                void handleClient(std::shared_ptr<boost::asio::ip::tcp::socket> socket);
            };

            // RTU服务器实现
            class RtuServer : public Server {
            public:
                RtuServer();
                ~RtuServer();

                // 配置RTU服务器
                bool configure(const RtuServerConfig& config);

                // 实现Server接口
                bool start() override;
                void stop() override;
                bool isRunning() const override;
                void setConnectionHandler(std::shared_ptr<ConnectionHandler> handler) override;

            private:
                RtuServerConfig config_;
                std::shared_ptr<boost::asio::io_context> io_context_;
                std::unique_ptr<boost::asio::serial_port> serial_port_;
                std::atomic<bool> isRunning_;
                std::shared_ptr<ConnectionHandler> connectionHandler_;
                std::thread io_thread_;
                std::vector<uint8_t> receiveBuffer_;

                // 配置串口参数
                bool configureSerialPort(boost::asio::serial_port& port, const RtuServerConfig& config);

                // 开始接收数据
                void startReceive();

                // 处理接收到的数据
                void handleReceive(const boost::system::error_code& error, size_t bytes_transferred);
            };

        } // namespace server
    } // namespace transport
} // namespace dlt645

#endif // DLT645_SERVER_API_H