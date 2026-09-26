#include <boost/asio/steady_timer.hpp>
#include "dlt645/common/log.h"
#include "dlt645/common/transform.h"
#include "dlt645/transport/client/client_api.h"
#include "transport/read_frame.h"
#include "log/default_logger.hpp"

namespace dlt645 {
    namespace transport {
        namespace client {

            TcpClient::TcpClient()
                : io_context_(nullptr)
                , isConnected_(false)
            {
            }

            TcpClient::~TcpClient()
            {
                // 只在连接时才尝试断开连接
                if (isConnected_) {
                    disconnect();
                }
                if (io_thread_.joinable()) {
                    if (io_context_) {
                        io_context_->stop();
                    }
                    io_thread_.join();
                }
            }

            bool TcpClient::configure(const TcpClientConfig& config)
            {
                config_ = config;
                return true;
            }

            void TcpClient::ensureIoContextRunning()
            {
                if (!io_context_) {
                    io_context_ = std::make_shared<boost::asio::io_context>();
                    io_thread_ = std::thread([this]() {
                        try {
                            boost::asio::executor_work_guard<boost::asio::io_context::executor_type> work_guard(
                                io_context_->get_executor());
                            io_context_->run();
                        } catch (const std::exception& e) {
                            LOG_ERROR("IO Context thread exception: {}", e.what());
                        }
                    });
                }
            }

            std::future<bool> TcpClient::connectAsync()
            {
                auto promise = std::make_shared<std::promise<bool>>();
                auto future = promise->get_future();

                try {
                    ensureIoContextRunning();

                    socket_ = std::make_unique<boost::asio::ip::tcp::socket>(*io_context_);
                    boost::asio::ip::tcp::endpoint endpoint(boost::asio::ip::make_address(config_.ip), config_.port);

                    LOG_INFO(
                        "Attempting to connect to {}:{} with timeout {} ms", config_.ip, config_.port, config_.timeout.count());

                    // 使用steady_timer实现连接超时
                    auto timer = std::make_shared<boost::asio::steady_timer>(*io_context_);
                    timer->expires_after(config_.timeout);

                    // 创建一个标志来跟踪哪个操作先完成
                    auto completed = std::make_shared<std::atomic<bool>>(false);

                    // 设置定时器回调
                    timer->async_wait([this, promise, completed](const boost::system::error_code& ec) {
                        if (!completed->exchange(true)) { // 如果是第一个完成的操作
                            if (ec != boost::asio::error::operation_aborted) {
                                // 超时，取消连接操作
                                if (socket_) {
                                    boost::system::error_code ignore_ec;
                                    socket_->cancel(ignore_ec);
                                }
                                LOG_WARN("TCP connection timeout after {} ms", config_.timeout.count());
                                isConnected_ = false;
                                promise->set_value(false);
                            }
                        }
                    });

                    socket_->async_connect(endpoint, [this, promise, timer, completed](const boost::system::error_code& error) {
                        // 取消定时器
                        timer->cancel();

                        if (!completed->exchange(true)) { // 如果是第一个完成的操作
                            if (!error) {
                                isConnected_ = true;
                                LOG_INFO("TCP client connected to {}:{} successfully", config_.ip, config_.port);
                                promise->set_value(true);
                            } else {
                                LOG_ERROR("TCP connection to {}:{} failed: {}", config_.ip, config_.port, error.message());
                                LOG_DEBUG(
                                    "Possible reasons: server not running, firewall blocking, incorrect IP/port, network issues");
                                isConnected_ = false;
                                promise->set_value(false);
                            }
                        }
                    });
                } catch (const std::exception& e) {
                    LOG_ERROR("Exception in TCP connectAsync: {}", e.what());
                    promise->set_value(false);
                }

                return future;
            }

            std::future<void> TcpClient::disconnectAsync()
            {
                auto promise = std::make_shared<std::promise<void>>();
                auto future = promise->get_future();

                try {
                    boost::asio::post(*io_context_, [this, promise]() {
                        try {
                            if (socket_ && socket_->is_open()) {
                                boost::system::error_code ec;
                                socket_->close(ec);
                                if (ec) {
                                    LOG_WARN("Error closing TCP socket: {}", ec.message());
                                }
                            }
                            isConnected_ = false;
                            LOG_INFO("TCP client disconnected");
                            promise->set_value();
                        } catch (const std::exception& e) {
                            LOG_ERROR("Exception in TCP disconnectAsync: {}", e.what());
                            promise->set_exception(std::current_exception());
                        }
                    });
                } catch (const std::exception& e) {
                    LOG_ERROR("Exception in TCP disconnectAsync wrapper: {}", e.what());
                    promise->set_exception(std::current_exception());
                }

                return future;
            }

            std::future<std::vector<uint8_t>> TcpClient::sendRequestAsync(const std::vector<uint8_t>& frame)
            {
                LOG_INFO("TX: {}({})", dlt645::common::bytesToHexString(frame), frame.size());
                auto promise = std::make_shared<std::promise<std::vector<uint8_t>>>();
                auto future = promise->get_future();

                try {
                    if (!isConnected_ || !socket_ || !socket_->is_open()) {
                        LOG_ERROR("TCP client not connected");
                        promise->set_value({});
                        return future;
                    }

                    auto buffer = std::make_shared<std::vector<uint8_t>>(frame);
                    boost::asio::async_write(
                        *socket_,
                        boost::asio::buffer(*buffer),
                        [this, promise, buffer](const boost::system::error_code& error, std::size_t /*bytes_transferred*/) {
                            if (error) {
                                LOG_ERROR("TCP send failed: {}", error.message());
                                isConnected_ = false;
                                promise->set_value({});
                                return;
                            }

                            std::make_shared<transport::FrameReadOperation<boost::asio::ip::tcp::socket>>(
                                *socket_, decoder_, *io_context_, config_.timeout, promise)
                                ->start();
                        });
                } catch (const std::exception& e) {
                    LOG_ERROR("Exception in TCP sendRequestAsync: {}", e.what());
                    promise->set_value({});
                }

                return future;
            }

            std::future<bool> TcpClient::sendOnlyAsync(const std::vector<uint8_t>& frame)
            {
                auto promise = std::make_shared<std::promise<bool>>();
                auto future = promise->get_future();
                if (!isConnected_ || !socket_ || !socket_->is_open()) {
                    promise->set_value(false);
                    return future;
                }
                auto buffer = std::make_shared<std::vector<uint8_t>>(frame);
                boost::asio::async_write(*socket_,
                                         boost::asio::buffer(*buffer),
                                         [this, promise, buffer](const boost::system::error_code& error, size_t) {
                                             if (error)
                                                 isConnected_ = false;
                                             promise->set_value(!error);
                                         });
                return future;
            }

            bool TcpClient::isConnected() const { return isConnected_; }

            void TcpClient::setTimeout(std::chrono::milliseconds timeout) { config_.timeout = timeout; }

        } // namespace client
    } // namespace transport
} // namespace dlt645
