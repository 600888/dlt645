#include <cstring>
#include <thread>
#include <vector>
#include "dlt645/common/log.h"
#include "dlt645/common/transform.h"
#include "dlt645/transport/server/server_api.h"

namespace dlt645
{
    namespace transport
    {
        namespace server
        {

            RtuServer::RtuServer()
                : config_(), io_context_(std::make_shared<boost::asio::io_context>()), serial_port_(), isRunning_(false), connectionHandler_(), io_thread_(), receiveBuffer_()
            {
                receiveBuffer_.resize(1024);
            }

            RtuServer::~RtuServer()
            {
                stop();
                if (io_thread_.joinable())
                {
                    io_thread_.join();
                }
            }

            bool RtuServer::configure(const RtuServerConfig &config)
            {
                config_ = config;
                return true;
            }

            bool RtuServer::configureSerialPort(boost::asio::serial_port &port, const RtuServerConfig &config)
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
                        LOG_WARN("Invalid stop bits value: {}", config.stopBits);
                        return false;
                    }

                    // 设置校验位
                    if (config.parity == "none")
                    {
                        port.set_option(boost::asio::serial_port_base::parity(boost::asio::serial_port_base::parity::none));
                    }
                    else if (config.parity == "even")
                    {
                        port.set_option(boost::asio::serial_port_base::parity(boost::asio::serial_port_base::parity::even));
                    }
                    else if (config.parity == "odd")
                    {
                        port.set_option(boost::asio::serial_port_base::parity(boost::asio::serial_port_base::parity::odd));
                    }
                    else
                    {
                        LOG_WARN("Invalid parity value: {}", config.parity);
                        return false;
                    }

                    // 设置流控制
                    if (config.flowControl == 0)
                    {
                        port.set_option(
                            boost::asio::serial_port_base::flow_control(boost::asio::serial_port_base::flow_control::none));
                    }
                    else if (config.flowControl == 1)
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
                        LOG_WARN("Invalid flow control value: {}", config.flowControl);
                        return false;
                    }

                    return true;
                }
                catch (const std::exception &e)
                {
                    LOG_ERROR("Failed to configure serial port: {}", e.what());
                    return false;
                }
            }

            bool RtuServer::start()
            {
                if (isRunning_)
                {
                    LOG_WARN("RTU server is already running");
                    return true;
                }

                try
                {
                    // 创建串口
                    serial_port_ = std::make_unique<boost::asio::serial_port>(*io_context_, config_.port);

                    // 配置串口参数
                    if (!configureSerialPort(*serial_port_, config_))
                    {
                        LOG_ERROR("Failed to configure serial port: {}", config_.port);
                        serial_port_->close();
                        return false;
                    }

                    // 启动io_context线程
                    isRunning_ = true;
                    // 创建工作保护，防止io_context在没有异步操作时退出
                    work_guard_.emplace(boost::asio::make_work_guard(*io_context_));

                    // 开始接收数据（先创建异步操作）
                    startReceive();

                    // 然后启动io_context线程
                    io_thread_ = std::thread([this]()
                                             {
                                                try {
                                                    io_context_->run();
                                                } catch (const std::exception& e) {
                                                    LOG_ERROR("RTU server IO context exception: {}", e.what());
                                                } });

                    LOG_INFO("RTU server started on port {}", config_.port);
                    return true;
                }
                catch (const std::exception &e)
                {
                    LOG_ERROR("Failed to start RTU server: {}", e.what());
                    isRunning_ = false;
                    return false;
                }
            }

            void RtuServer::stop()
            {
                if (!isRunning_)
                {
                    return;
                }

                try
                {
                    isRunning_ = false;

                    if (serial_port_ && serial_port_->is_open())
                    {
                        boost::system::error_code ec;
                        serial_port_->close(ec);
                        if (ec)
                        {
                            LOG_WARN("Failed to close serial port: {}", ec.message());
                        }
                    }

                    // 移除工作保护，允许io_context退出
                    if (work_guard_)
                    {
                        work_guard_->reset();
                        work_guard_.reset(); // 释放optional
                    }

                    // 停止io_context
                    io_context_->stop();

                    // 等待io_thread_退出
                    if (io_thread_.joinable())
                    {
                        io_thread_.join();
                    }

                    LOG_INFO("RTU server stopped");
                }
                catch (const std::exception &e)
                {
                    LOG_ERROR("Failed to stop RTU server: {}", e.what());
                    // 确保在异常情况下也能正确清理
                    isRunning_ = false;
                    if (io_thread_.joinable())
                    {
                        try
                        {
                            io_thread_.join();
                        }
                        catch (...)
                        {
                            // 忽略join异常
                        }
                    }
                }
            }

            bool RtuServer::isRunning() const { return isRunning_; }

            void RtuServer::setConnectionHandler(std::shared_ptr<ConnectionHandler> handler) { connectionHandler_ = handler; }

            void RtuServer::startReceive()
            {
                if (!isRunning_ || !serial_port_ || !serial_port_->is_open())
                {
                    return;
                }

                serial_port_->async_read_some(boost::asio::buffer(receiveBuffer_),
                                              [this](const boost::system::error_code &error, size_t bytes_transferred)
                                              {
                                                  handleReceive(error, bytes_transferred);
                                              });
            }

            void RtuServer::handleReceive(const boost::system::error_code &error, size_t bytes_transferred)
            {
                if (!error)
                {
                    std::vector<uint8_t> data(receiveBuffer_.begin(), receiveBuffer_.begin() + bytes_transferred);

                    LOG_INFO("RX: {}({})", common::bytesToHexString(data), bytes_transferred);

                    // 处理数据
                    if (connectionHandler_)
                    {
                        try
                        {
                            // 解析帧
                            auto frame = protocol::Frame::deserialize(data);
                            if (!frame)
                            {
                                LOG_WARN("Failed to parse frame");
                                return;
                            }

                            LOG_DEBUG("Received frame: ctrlCode={}, data length={}", frame->ctrlCode, frame->dataLen);

                            // 调用handleFrame来处理解析后的帧
                            std::vector<uint8_t> response = connectionHandler_->handleRequest(*frame);

                            // 发送响应
                            if (!response.empty())
                            {
                                boost::asio::write(*serial_port_, boost::asio::buffer(response));
                                LOG_DEBUG("Sent response to RTU client: {}", common::bytesToHexString(response));
                            }
                        }
                        catch (const std::exception &e)
                        {
                            LOG_ERROR("Exception in RTU connection handler: {}", e.what());
                        }
                    }

                    // 继续接收数据
                    startReceive();
                }
                else
                {
                    if (isRunning_)
                    {
                        LOG_ERROR("RTU receive error: {}", error.message());
                        // 尝试重新开始接收
                        startReceive();
                    }

                    // 通知连接关闭
                    if (connectionHandler_)
                    {
                        try
                        {
                            connectionHandler_->onConnectionClosed();
                        }
                        catch (const std::exception &e)
                        {
                            LOG_ERROR("Exception in onConnectionClosed: {}", e.what());
                        }
                    }
                }
            }

        } // namespace server
    } // namespace transport
} // namespace dlt645