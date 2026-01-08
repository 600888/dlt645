#include <atomic>
#include <chrono>
#include <future>
#include <memory>
#include <thread>
#include <boost/asio.hpp>
#include <boost/system/error_code.hpp>
#include "dlt645/common/log.h"
#include "dlt645/transport/client/client_api.h"
#include "dlt645/common/transform.h"

namespace dlt645
{
    namespace transport
    {
        namespace client
        {

            RtuClient::RtuClient()
                : io_context_(nullptr), isConnected_(false)
            {
            }

            RtuClient::~RtuClient()
            {
                // 只在连接时才尝试断开连接
                if (isConnected_)
                {
                    disconnect();
                }
                if (io_thread_.joinable())
                {
                    if (io_context_)
                    {
                        io_context_->stop();
                    }
                    io_thread_.join();
                }
            }

            bool RtuClient::configure(const RtuClientConfig &config)
            {
                config_ = config;
                return true;
            }

            void RtuClient::ensureIoContextRunning()
            {
                if (!io_context_)
                {
                    io_context_ = std::make_shared<boost::asio::io_context>();
                    io_thread_ = std::thread([this]()
                                             {
                        try {
                            boost::asio::executor_work_guard<boost::asio::io_context::executor_type> work_guard(
                                io_context_->get_executor());
                            io_context_->run();
                        } catch (const std::exception& e) {
                            LOG_ERROR("IO Context thread exception: {}", e.what());
                        } });
                }
            }

            bool RtuClient::configureSerialPort(boost::asio::serial_port &port, const RtuClientConfig &config)
            {
                try
                {
                    // 设置波特率
                    port.set_option(boost::asio::serial_port_base::baud_rate(config.baudRate));

                    // 设置数据位
                    port.set_option(boost::asio::serial_port_base::character_size(config.dataBits));

                    // 设置停止位
                    if (config.stopBits == 1)
                    {
                        port.set_option(boost::asio::serial_port_base::stop_bits(boost::asio::serial_port_base::stop_bits::one));
                    }
                    else if (config.stopBits == 2)
                    {
                        port.set_option(boost::asio::serial_port_base::stop_bits(boost::asio::serial_port_base::stop_bits::two));
                    }
                    else
                    {
                        port.set_option(boost::asio::serial_port_base::stop_bits(boost::asio::serial_port_base::stop_bits::one));
                        LOG_WARN("Invalid stop bits value, using 1 stop bit");
                    }

                    // 设置校验位
                    if (config.parity == "even")
                    {
                        port.set_option(boost::asio::serial_port_base::parity(boost::asio::serial_port_base::parity::even));
                    }
                    else if (config.parity == "odd")
                    {
                        port.set_option(boost::asio::serial_port_base::parity(boost::asio::serial_port_base::parity::odd));
                    }
                    else
                    {
                        port.set_option(boost::asio::serial_port_base::parity(boost::asio::serial_port_base::parity::none));
                    }

                    // 设置流控制
                    if (config.flowControl == 1)
                    {
                        port.set_option(
                            boost::asio::serial_port_base::flow_control(boost::asio::serial_port_base::flow_control::software));
                    }
                    else if (config.flowControl == 2)
                    {
                        port.set_option(
                            boost::asio::serial_port_base::flow_control(boost::asio::serial_port_base::flow_control::hardware));
                    }
                    else
                    {
                        port.set_option(
                            boost::asio::serial_port_base::flow_control(boost::asio::serial_port_base::flow_control::none));
                    }

                    return true;
                }
                catch (const std::exception &e)
                {
                    LOG_ERROR("Failed to configure serial port: {}", e.what());
                    return false;
                }
            }

            std::future<bool> RtuClient::connectAsync()
            {
                auto promise = std::make_shared<std::promise<bool>>();
                auto future = promise->get_future();

                try
                {
                    ensureIoContextRunning();

                    serial_port_ = std::make_unique<boost::asio::serial_port>(*io_context_);

                    // 异步打开串口
                    boost::asio::post(*io_context_, [this, promise]()
                                      {
                        try {
                            serial_port_->open(config_.port);

                            // 配置串口参数
                            if (configureSerialPort(*serial_port_, config_)) {
                                isConnected_ = true;
                                LOG_INFO("RTU client connected to port {}", config_.port);
                                promise->set_value(true);
                            } else {
                                LOG_ERROR("Failed to configure serial port: {}", config_.port);
                                serial_port_->close();
                                isConnected_ = false;
                                promise->set_value(false);
                            }
                        } catch (const std::exception& e) {
                            LOG_ERROR("Failed to open serial port {}: {}", config_.port, e.what());
                            isConnected_ = false;
                            promise->set_value(false);
                        } });
                }
                catch (const std::exception &e)
                {
                    LOG_ERROR("Exception in RTU connectAsync: {}", e.what());
                    promise->set_value(false);
                }

                return future;
            }

            std::future<void> RtuClient::disconnectAsync()
            {
                auto promise = std::make_shared<std::promise<void>>();
                auto future = promise->get_future();

                try
                {
                    boost::asio::post(*io_context_, [this, promise]()
                                      {
                        try {
                            if (serial_port_ && serial_port_->is_open()) {
                                boost::system::error_code ec;
                                serial_port_->close(ec);
                                if (ec) {
                                    LOG_WARN("Error closing serial port: {}", ec.message());
                                }
                            }
                            isConnected_ = false;
                            LOG_INFO("RTU client disconnected from port {}", config_.port);
                            promise->set_value();
                        } catch (const std::exception& e) {
                            LOG_ERROR("Exception in RTU disconnectAsync: {}", e.what());
                            promise->set_exception(std::current_exception());
                        } });
                }
                catch (const std::exception &e)
                {
                    LOG_ERROR("Exception in RTU disconnectAsync wrapper: {}", e.what());
                    promise->set_exception(std::current_exception());
                }

                return future;
            }

            std::future<std::vector<uint8_t>> RtuClient::sendRequestAsync(const std::vector<uint8_t> &frame)
            {
                LOG_INFO("TX: {}({})", dlt645::common::bytesToHexString(frame), frame.size());
                auto promise = std::make_shared<std::promise<std::vector<uint8_t>>>();
                auto future = promise->get_future();

                try
                {
                    if (!isConnected_ || !serial_port_ || !serial_port_->is_open())
                    {
                        LOG_ERROR("RTU client not connected");
                        promise->set_value({});
                        return future;
                    }

                    auto buffer = std::make_shared<std::vector<uint8_t>>(frame);

                    // 发送数据
                    boost::asio::async_write(
                        *serial_port_,
                        boost::asio::buffer(*buffer),
                        [this, promise](const boost::system::error_code &error, std::size_t /*bytes_transferred*/)
                        {
                            if (error)
                            {
                                LOG_ERROR("RTU send failed: {}", error.message());
                                isConnected_ = false;
                                promise->set_value({});
                                return;
                            }

                            // 发送成功后接收响应
                            auto response_buffer = std::make_shared<std::vector<uint8_t>>();
                            response_buffer->resize(1024); // 预分配空间

                            // 创建一个定时器用于超时控制
                            auto timer = std::make_shared<boost::asio::steady_timer>(*io_context_, config_.timeout);

                            // 异步读取数据的标志
                            auto read_in_progress = std::make_shared<bool>(true);

                            // 设置超时处理
                            timer->async_wait(
                                [promise, response_buffer, read_in_progress](const boost::system::error_code &error)
                                {
                                    if (error == boost::asio::error::operation_aborted)
                                    {
                                        // 定时器被取消，说明读取已完成
                                        return;
                                    }

                                    if (*read_in_progress)
                                    {
                                        *read_in_progress = false;
                                        LOG_WARN("RTU receive timeout");
                                        promise->set_value({});
                                    }
                                });

                            // 异步读取串口数据
                            auto read_handler = [this, promise, response_buffer, timer, read_in_progress](
                                                    const boost::system::error_code &error, std::size_t bytes_read)
                            {
                                if (!*read_in_progress)
                                {
                                    // 超时已处理
                                    return;
                                }

                                *read_in_progress = false;
                                timer->cancel(); // 取消定时器

                                if (error)
                                {
                                    LOG_ERROR("RTU receive failed: {}", error.message());
                                    isConnected_ = false;
                                    promise->set_value({});
                                    return;
                                }

                                response_buffer->resize(bytes_read);
                                promise->set_value(*response_buffer);
                            };

                            serial_port_->async_read_some(boost::asio::buffer(*response_buffer), read_handler);
                        });
                }
                catch (const std::exception &e)
                {
                    LOG_ERROR("Exception in RTU sendRequestAsync: {}", e.what());
                    promise->set_value({});
                }

                return future;
            }

            bool RtuClient::isConnected() const { return isConnected_; }

            void RtuClient::setTimeout(std::chrono::milliseconds timeout) { config_.timeout = timeout; }

        } // namespace client
    } // namespace transport
} // namespace dlt645