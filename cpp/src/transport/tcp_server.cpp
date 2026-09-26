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
                    // 创建工作保护，防止io_context在没有异步操作时退出
                    work_guard_.emplace(boost::asio::make_work_guard(*io_context_));

                    // 开始接受连接（先创建异步操作）
                    acceptConnection();

                    // 然后启动io_context线程
                    io_thread_ = std::thread([this]() {
                        try {
                            io_context_->run();
                        } catch (const std::exception& e) {
                            LOG_ERROR("TCP server IO context exception: {}", e.what());
                        }
                    });

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

                    // 关闭acceptor，停止接受新连接
                    if (acceptor_) {
                        boost::system::error_code ec;
                        acceptor_->close(ec);
                        if (ec) {
                            LOG_WARN("Failed to close acceptor: {}", ec.message());
                        }
                    }

                    // 移除工作保护，允许io_context退出
                    if (work_guard_) {
                        work_guard_->reset();
                        work_guard_.reset(); // 释放optional
                    }

                    // 停止io_context
                    io_context_->stop();

                    // 等待io_thread_退出
                    if (io_thread_.joinable()) {
                        io_thread_.join();
                    }

                    LOG_INFO("TCP server stopped");
                } catch (const std::exception& e) {
                    LOG_ERROR("Failed to stop TCP server: {}", e.what());
                    // 确保在异常情况下也能正确清理
                    isRunning_ = false;
                    if (io_thread_.joinable()) {
                        try {
                            io_thread_.join();
                        } catch (...) {
                            // 忽略join异常
                        }
                    }
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
                    try {
                        if (!error) {
                            LOG_INFO("New TCP connection from {}", socket->remote_endpoint().address().to_string());

                            // 处理客户端连接
                            handleClient(socket, std::make_shared<protocol::FrameStreamDecoder>());
                        } else {
                            if (isRunning_) {
                                LOG_ERROR("Failed to accept TCP connection: {}", error.message());
                            }
                        }

                        // 继续接受下一个连接
                        if (isRunning_) {
                            acceptConnection();
                        }
                    } catch (const std::exception& e) {
                        if (isRunning_) {
                            LOG_ERROR("Exception in accept callback: {}", e.what());
                            // 继续接受下一个连接
                            if (isRunning_) {
                                acceptConnection();
                            }
                        }
                    } catch (...) {
                        if (isRunning_) {
                            LOG_ERROR("Unknown exception in accept callback");
                            // 继续接受下一个连接
                            if (isRunning_) {
                                acceptConnection();
                            }
                        }
                    }
                });
            }

            void TcpServer::handleClient(std::shared_ptr<boost::asio::ip::tcp::socket> socket,
                                         std::shared_ptr<protocol::FrameStreamDecoder> decoder)
            {
                auto buffer = std::make_shared<std::vector<uint8_t>>(1024);
                socket->async_read_some(
                    boost::asio::buffer(*buffer),
                    [this, socket, decoder, buffer](const boost::system::error_code& error, size_t bytesRead) {
                        if (error) {
                            LOG_INFO("TCP client disconnected: {}", error.message());
                            if (connectionHandler_)
                                connectionHandler_->onConnectionClosed();
                            return;
                        }
                        try {
                            decoder->append(buffer->data(), bytesRead);
                            std::vector<uint8_t> responses;
                            while (auto frame = decoder->nextFrame()) {
                                if (!connectionHandler_)
                                    continue;
                                try {
                                    auto response = connectionHandler_->handleRequest(*frame);
                                    responses.insert(responses.end(), response.begin(), response.end());
                                } catch (const std::exception& e) {
                                    LOG_ERROR("Failed to handle TCP frame: {}", e.what());
                                }
                            }
                            if (responses.empty()) {
                                if (isRunning_)
                                    handleClient(socket, decoder);
                                return;
                            }
                            auto output = std::make_shared<std::vector<uint8_t>>(std::move(responses));
                            boost::asio::async_write(
                                *socket,
                                boost::asio::buffer(*output),
                                [this, socket, decoder, output](const boost::system::error_code& writeError, size_t) {
                                    if (writeError) {
                                        LOG_ERROR("Failed to send TCP response: {}", writeError.message());
                                        if (connectionHandler_)
                                            connectionHandler_->onConnectionClosed();
                                    } else if (isRunning_) {
                                        handleClient(socket, decoder);
                                    }
                                });
                        } catch (const std::exception& e) {
                            LOG_ERROR("Failed to process TCP input: {}", e.what());
                            if (isRunning_)
                                handleClient(socket, decoder);
                        }
                    });
            }

        } // namespace server
    } // namespace transport
} // namespace dlt645
