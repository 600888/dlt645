#include "dlt645/service/server_service.h"
#include <chrono>
#include <string>
#include <array>
#include <span>
#include <utility>
#include "dlt645/common/log.h"
#include "dlt645/common/transform.h"
#include "dlt645/model/data_item.h"

namespace dlt645 {
    namespace service {

        ServerService::ServerService(std::shared_ptr<transport::server::Server> server,
                                     std::optional<std::array<uint8_t, 6>> address,
                                     std::optional<std::array<uint8_t, 4>> password)
            : server_(std::move(server))
        {
            // 初始化地址和密码
            if (address.has_value()) {
                address_ = *address;
            } else {
                address_.fill(0x00);
            }

            if (password.has_value()) {
                password_ = *password;
            } else {
                password_.fill(0x00);
            }
        }

        // 初始化方法，用于在对象完全构造后设置连接处理器
        void ServerService::init()
        {
            if (server_) {
                server_->setConnectionHandler(shared_from_this());
            }
        }

        void ServerService::registerDevice(const std::array<uint8_t, 6>& addr)
        {
            address_ = addr;
            LOG_INFO("Device registered with address: {}",
                     common::bytesToHexString(std::vector<uint8_t>(addr.begin(), addr.end())));
        }

        bool ServerService::validateDevice(const std::array<uint8_t, 6>& address) const
        {
            // 处理特殊命令地址
            if (std::ranges::all_of(address, [](uint8_t b) { return b == 0xAA; })) {
                return true; // 读通讯地址命令
            }

            if (std::ranges::all_of(address, [](uint8_t b) { return b == 0x99; })) {
                return true; // 广播时间同步命令
            }

            // 验证设备地址是否匹配
            LOG_INFO("Validating address: {} vs received: {}",
                     common::bytesToHexString(std::vector<uint8_t>(address_.begin(), address_.end())),
                     common::bytesToHexString(std::vector<uint8_t>(address.begin(), address.end())));

            return address == address_;
        }

        void ServerService::setTime(const std::vector<uint8_t>& dataBytes)
        {
            // 时间设置实现，可以根据实际需求添加
            LOG_INFO("Setting time with data: {}", common::bytesToHexString(dataBytes));
        }

        void ServerService::setAddress(const std::array<uint8_t, 6>& address)
        {
            if (address.size() != 6) {
                throw std::invalid_argument("Invalid address length");
            }
            address_ = address;
            LOG_INFO("Device address set to: {}", common::bytesToHexString(std::vector<uint8_t>(address.begin(), address.end())));
        }

        bool ServerService::set00(uint32_t di, float value)
        {
            LOG_INFO("Setting energy value for DI={}: {}", di, value);

            // 获取数据项
            auto dataItem = DIManager::inst()->getDataItem(di);

            if (!dataItem) {
                LOG_ERROR("Failed to get data item");
                return false;
            }

            // 验证值是否符合数据项的格式
            if (!model::isValueValid(dataItem->dataFormat, value)) {
                LOG_ERROR("Value {} is out of range for data format {}", value, dataItem->dataFormat);
                return false;
            }

            // 更新数据项的值
            dataItem->value = value;
            dataItem->setTimestamp(std::chrono::system_clock::now());

            // 使用updateDataItem方法更新原始数据
            return DIManager::inst()->updateDataItem(di, *dataItem);
        }

        bool ServerService::set01(uint32_t di, const model::Demand& demand)
        {
            LOG_INFO("Setting demand value for DI={}: {}", di, demand.value);

            // 获取数据项
            auto dataItem = DIManager::inst()->getDataItem(di);

            if (!dataItem) {
                LOG_ERROR("Failed to get data item");
                return false;
            }

            // 验证值是否符合数据项的格式
            if (!model::isValueValid(dataItem->dataFormat, demand.value)) {
                LOG_ERROR("Demand value {} is out of range for data format {}", demand.value, dataItem->dataFormat);
                return false;
            }

            // 更新数据项的值
            dataItem->value = demand;
            dataItem->setTimestamp(std::chrono::system_clock::now());

            // 使用updateDataItem方法更新原始数据
            return DIManager::inst()->updateDataItem(di, *dataItem);
        }

        bool ServerService::set02(uint32_t di, float value)
        {
            LOG_INFO("Setting variable value for DI={}: {}", di, value);

            // 获取数据项
            auto dataItem = DIManager::inst()->getDataItem(di);

            if (!dataItem) {
                LOG_ERROR("Failed to get data item");
                return false;
            }

            // 验证值是否符合数据项的格式
            if (!model::isValueValid(dataItem->dataFormat, value)) {
                LOG_ERROR("Value {} is out of range for data format {}", value, dataItem->dataFormat);
                return false;
            }

            // 更新数据项的值
            dataItem->value = value;
            dataItem->setTimestamp(std::chrono::system_clock::now());

            // 使用updateDataItem方法更新原始数据
            return DIManager::inst()->updateDataItem(di, *dataItem);
        }

        void ServerService::setPassword(const std::array<uint8_t, 4>& password)
        {
            if (password.size() != 4) {
                throw std::invalid_argument("Invalid password length");
            }
            password_ = password;

            std::string passwordStr;
            for (const auto& byte : password) {
                passwordStr += fmt::format("{:02X}", byte);
            }
            LOG_INFO("Password set to: {}", passwordStr);
        }

        std::shared_ptr<model::DataItem> ServerService::getDataItem(uint32_t di) const
        {
            const auto dataItem = DIManager::inst()->getDataItem(di);
            if (!dataItem) {
                return nullptr;
            }
            return dataItem;
        }

        void ServerService::onConnectionClosed()
        {
            LOG_INFO("Connection closed");
            // 可以在这里添加连接关闭时的清理逻辑
        }

        std::vector<uint8_t> ServerService::handleRequest(const protocol::Frame& frame)
        {
            // 1. 验证设备
            if (!validateDevice(frame.addr)) {
                LOG_INFO("Device validation failed for address: {}",
                         common::bytesToHexString(std::vector<uint8_t>(frame.addr.begin(), frame.addr.end())));
                throw std::runtime_error("Unauthorized device");
            }

            // 2. 根据控制码判断请求类型
            switch (frame.ctrlCode) {
            case model::BROADCAST_TIME_SYNC: {
                LOG_INFO("Broadcast time sync: {}", common::bytesToHexString(frame.data));
                setTime(frame.data);
                return protocol::Frame::buildFrame(frame.addr, frame.ctrlCode | 0x80, frame.data);
            }

            case model::CTRL_READ_DATA: {
                // 解析数据标识
                if (frame.data.size() < 4) {
                    LOG_ERROR("Invalid read request data length");
                    return {};
                }

                uint32_t di = dlt645::common::bytesToIntLittleEndian<uint32_t>(frame.data);
                LOG_DEBUG("Read request for DI: {}", di);

                // 检查数据标识的第三个字节
                uint8_t di3 = frame.data[3];

                switch (di3) {
                case 0x00:
                    // 读取电能
                    return handleReadEnergy(frame);

                case 0x01:
                    // 读取最大需量及发生时间
                    return handleReadDemand(frame);

                case 0x02:
                    // 读取变量
                    return handleReadVariable(frame);

                default:
                    LOG_INFO("Unknown data type: {}", fmt::format("{:02X}", di3));
                    throw std::runtime_error("Unknown data type");
                }
            }

            case model::READ_ADDRESS: {
                // 读地址请求
                std::vector<uint8_t> resData(address_.begin(), address_.end());
                return protocol::Frame::buildFrame(address_, frame.ctrlCode | 0x80, resData);
            }

            case model::WRITE_ADDRESS: {
                // 写地址请求
                if (frame.data.size() >= 6) {
                    std::array<uint8_t, 6> newAddr;
                    std::ranges::copy(frame.data.begin(), frame.data.begin() + 6, newAddr.begin());
                    setAddress(newAddr);
                }
                return protocol::Frame::buildFrame(address_, frame.ctrlCode | 0x80, {});
            }

            default: {
                LOG_INFO("Unknown control code: {}", fmt::format("{:02X}", frame.ctrlCode));
                throw std::runtime_error("Unknown control code");
            }
            }
            return {};
        }

        std::vector<uint8_t> ServerService::handleReadEnergy(const protocol::Frame& frame)
        {
            // 解析数据标识为32位无符号整数
            uint32_t dataId = dlt645::common::bytesToIntLittleEndian<uint32_t>(frame.data);

            // 获取数据项
            const auto dataItem = DIManager::inst()->getDataItem(dataId);
            if (!dataItem) {
                LOG_ERROR("Data item not found for ID: {}", dataId);
                return {};
            }

            // 构建响应数据
            std::vector<uint8_t> resData(8);
            // 复制前4字节数据标识
            std::ranges::copy(frame.data.begin(), frame.data.begin() + 4, resData.begin());

            if (std::holds_alternative<float>(dataItem->value)) {
                float value = std::get<float>(dataItem->value);
                // 将浮点数转换为BCD码
                auto bcdValue = dlt645::common::floatToBcd(value, dataItem->dataFormat, true);
                // 复制BCD值到响应数据
                if (bcdValue.size() >= 4) {
                    std::ranges::copy(bcdValue.begin(), bcdValue.begin() + 4, resData.begin() + 4);
                }
            }

            // 构建响应帧
            return protocol::Frame::buildFrame(frame.addr, frame.ctrlCode | 0x80, resData);
        }

        std::vector<uint8_t> ServerService::handleReadDemand(const protocol::Frame& frame)
        {
            // 解析数据标识为32位无符号整数
            uint32_t dataId = common::bytesToIntLittleEndian<uint32_t>(frame.data);

            // 获取数据项
            const auto dataItem = DIManager::inst()->getDataItem(dataId);
            if (!dataItem) {
                LOG_ERROR("Data item not found for ID: {}", dataId);
                return {};
            }

            // 构建响应数据
            std::vector<uint8_t> resData(12);
            // 复制前4字节数据标识
            std::ranges::copy(frame.data.begin(), frame.data.begin() + 4, resData.begin());

            // 处理数据值
            if (std::holds_alternative<model::Demand>(dataItem->value)) {
                const model::Demand& demand = std::get<model::Demand>(dataItem->value);
                // 将需量值转换为BCD码
                auto bcdValue = dlt645::common::floatToBcd(demand.value, dataItem->dataFormat, true);
                // 确保BCD值至少有3个字节
                if (bcdValue.size() < 3) {
                    bcdValue.resize(3, 0);
                }
                // 复制BCD值到响应数据
                if (bcdValue.size() >= 3) {
                    std::ranges::copy(bcdValue.begin(), bcdValue.begin() + 3, resData.begin() + 4);
                }

                // 获取当前时间并转换为BCD码
                auto now = std::chrono::system_clock::now();
                auto timeBcd = dlt645::common::timeToBcd(now, true);
                // 复制时间BCD码到响应数据
                if (timeBcd.size() >= 5) {
                    std::ranges::copy(timeBcd.begin(), timeBcd.begin() + 5, resData.begin() + 7);
                }
            }

            LOG_INFO("Reading maximum demand and occurrence time: {}", common::bytesToHexString(resData));

            // 构建响应帧
            return protocol::Frame::buildFrame(frame.addr, frame.ctrlCode | 0x80, resData);
        }

        std::vector<uint8_t> ServerService::handleReadVariable(const protocol::Frame& frame)
        {
            // 解析数据标识为32位无符号整数
            uint32_t dataId = dlt645::common::bytesToIntLittleEndian<uint32_t>(frame.data);

            // 获取数据项
            const auto dataItem = DIManager::inst()->getDataItem(dataId);
            if (!dataItem) {
                LOG_ERROR("Data item not found for ID: {}", dataId);
                return {};
            }

            // 计算变量数据长度
            size_t dataLen = 4; // 数据标识长度
            // 根据数据格式计算额外长度
            if (!dataItem->dataFormat.empty()) {
                dataLen += (dataItem->dataFormat.length() - 1) / 2; // (数据格式长度 - 1位小数点)/2
            }

            // 构建响应数据
            std::vector<uint8_t> resData(dataLen);
            // 复制前4字节数据标识
            std::ranges::copy(frame.data.begin(), frame.data.begin() + 4, resData.begin());

            // 处理数据值
            if (std::holds_alternative<float>(dataItem->value)) {
                float value = std::get<float>(dataItem->value);
                // 将浮点数转换为BCD码（小端序）
                auto bcdValue = dlt645::common::floatToBcd(value, dataItem->dataFormat, true);
                // 复制BCD值到响应数据
                size_t bcdCopyLen = std::min(bcdValue.size(), dataLen - 4);
                std::ranges::copy(bcdValue.begin(), bcdValue.begin() + bcdCopyLen, resData.begin() + 4);
            }

            // 构建响应帧
            return protocol::Frame::buildFrame(frame.addr, frame.ctrlCode | 0x80, resData);
        }

        bool ServerService::start()
        {
            if (server_) {
                return server_->start();
            }
            return false;
        }

        void ServerService::stop()
        {
            if (server_) {
                server_->stop();
            }
        }

        std::shared_ptr<ServerService> createTcpServer(const std::string& ip, uint16_t port, std::chrono::milliseconds timeout)
        {
            DIManager::preInit();
            // 1. 先创建TcpServer
            auto tcpServer = std::make_shared<transport::server::TcpServer>();
            transport::server::TcpServerConfig config;
            config.ip = ip;
            config.port = port;
            config.timeout = timeout;

            if (!tcpServer->configure(config)) {
                LOG_ERROR("Failed to configure TCP server");
                return nullptr;
            }

            // 2. 创建ServerService，注入TcpServer
            auto serverService = std::make_shared<ServerService>(tcpServer);

            // 3. 在对象完全构造后调用init()方法设置连接处理器
            serverService->init();

            return serverService;
        }

        std::shared_ptr<ServerService> createRtuServer(const std::string& port,
                                                       int baudrate,
                                                       int databits,
                                                       int stopbits,
                                                       const std::string& parity,
                                                       std::chrono::milliseconds timeout)
        {
            DIManager::preInit();
            // 1. 先创建RtuServer
            auto rtuServer = std::make_shared<transport::server::RtuServer>();
            transport::server::RtuServerConfig config;
            config.port = port;
            config.baudRate = baudrate;
            config.dataBits = databits;
            config.stopBits = stopbits;
            config.parity = parity;
            config.timeout = timeout;

            if (!rtuServer->configure(config)) {
                LOG_ERROR("Failed to configure RTU server");
                return nullptr;
            }

            // 2. 创建ServerService，注入RtuServer
            auto serverService = std::make_shared<ServerService>(rtuServer);

            // 3. 在对象完全构造后调用init()方法设置连接处理器
            serverService->init();

            return serverService;
        }

    } // namespace service
} // namespace dlt645