#include <cstring>
#include <thread>
#include <vector>
#include "dlt645/common/log.h"
#include "dlt645/common/transform.h"
#include "dlt645/transport/server/server_api.h"

namespace dlt645 {
    namespace transport {
        namespace server {

            TcpServer::TcpServer()
                : io_context_(std::make_shared<boost::asio::io_context>())
                , isRunning_(false)
            {
            }

            TcpServer::~TcpServer()
            {
                stop();
                if (io_thread_.joinable()) {
                    io_thread_.join();
                }
            }

            bool TcpServer::configure(const TcpServerConfig& config)
            {
                config_ = config;
                return true;
            }

            bool TcpServer::start()
            {
                if (isRunning_) {
                    LOG_WARN("TCP server is already running");
                    return true;
                }

                try {
                    // 创建acceptor
                    boost::asio::ip::tcp::endpoint endpoint(boost::asio::ip::make_address(config_.ip), config_.port);

                    acceptor_ = std::make_unique<boost::asio::ip::tcp::acceptor>(*io_context_, endpoint);

                    // 启动io_context线程
                    isRunning_ = true;
                    io_thread_ = std::thread([this]() {
                        try {
                            io_context_->run();
                        } catch (const std::exception& e) {
                            LOG_ERROR("TCP server IO context exception: {}", e.what());
                        }
                    });

                    // 开始接受连接
                    acceptConnection();

                    LOG_INFO("TCP server started on {}:{}", config_.ip, config_.port);
                    return true;
                } catch (const std::exception& e) {
                    LOG_ERROR("Failed to start TCP server: {}", e.what());
                    isRunning_ = false;
                    return false;
                }
            }

            void TcpServer::stop()
            {
                if (!isRunning_) {
                    return;
                }

                try {
                    isRunning_ = false;

                    if (acceptor_) {
                        acceptor_->close();
                    }

                    io_context_->stop();

                    LOG_INFO("TCP server stopped");
                } catch (const std::exception& e) {
                    LOG_ERROR("Failed to stop TCP server: {}", e.what());
                }
            }

            bool TcpServer::isRunning() const { return isRunning_; }

            void TcpServer::setConnectionHandler(std::shared_ptr<ConnectionHandler> handler) { connectionHandler_ = handler; }

            void TcpServer::acceptConnection()
            {
                if (!isRunning_ || !acceptor_) {
                    return;
                }

                auto socket = std::make_shared<boost::asio::ip::tcp::socket>(*io_context_);

                acceptor_->async_accept(*socket, [this, socket](const boost::system::error_code& error) {
                    if (!error) {
                        LOG_INFO("New TCP connection from {}", socket->remote_endpoint().address().to_string());

                        // 处理客户端连接
                        handleClient(socket);
                    } else {
                        if (isRunning_) {
                            LOG_ERROR("Failed to accept TCP connection: {}", error.message());
                        }
                    }

                    // 继续接受下一个连接
                    if (isRunning_) {
                        acceptConnection();
                    }
                });
            }

            void TcpServer::handleClient(std::shared_ptr<boost::asio::ip::tcp::socket> socket)
            {
                auto buffer = std::make_shared<std::vector<uint8_t>>(1024);

                socket->async_read_some(
                    boost::asio::buffer(*buffer),
                    [this, socket, buffer](const boost::system::error_code& error, size_t bytes_transferred) {
                        if (!error) {
                            buffer->resize(bytes_transferred);

                            LOG_DEBUG(
                                "Received {} bytes from TCP client: {}", bytes_transferred, common::bytesToHexString(*buffer));

                            // 处理数据
                            if (connectionHandler_) {
                                try {
                                    // 解析帧
                                    auto frame = protocol::Frame::deserialize(*buffer);
                                    if (!frame) {
                                        LOG_WARN("Failed to parse frame");
                                        return;
                                    }

                                    LOG_DEBUG("Received frame: ctrlCode={}, data length={}", frame->ctrlCode, frame->dataLen);

                                    // 调用handleFrame来处理解析后的帧
                                    std::vector<uint8_t> response = connectionHandler_->handleRequest(*frame);

                                    // 发送响应
                                    if (!response.empty()) {
                                        boost::asio::async_write(
                                            *socket,
                                            boost::asio::buffer(response),
                                            [socket, response](const boost::system::error_code& error, size_t) {
                                                if (error) {
                                                    LOG_ERROR("Failed to send TCP response: {}", error.message());
                                                } else {
                                                    LOG_DEBUG("Sent response to TCP client: {}",
                                                              common::bytesToHexString(response));
                                                }
                                            });
                                    }
                                } catch (const std::exception& e) {
                                    LOG_ERROR("Exception in TCP connection handler: {}", e.what());
                                }
                            }

                            // 继续接收数据
                            handleClient(socket);
                        } else {
                            LOG_INFO("TCP client disconnected: {}", error.message());

                            // 通知连接关闭
                            if (connectionHandler_) {
                                try {
                                    connectionHandler_->onConnectionClosed();
                                } catch (const std::exception& e) {
                                    LOG_ERROR("Exception in onConnectionClosed: {}", e.what());
                                }
                            }
                        }
                    });
            }

        } // namespace server
    } // namespace transport
} // namespace dlt645