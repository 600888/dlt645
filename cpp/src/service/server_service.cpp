#include "dlt645/service/server_service.h"
#include <chrono>
#include <ctime>
#include <string>
#include <array>
#include <algorithm>
#include <utility>
#include <type_traits>
#include "dlt645/common/log.h"
#include "dlt645/common/transform.h"
#include "dlt645/model/data_item.h"
#include "field_codec.h"

namespace dlt645
{
    namespace service
    {

        ServerService::ServerService(std::shared_ptr<transport::server::Server> server,
                                     std::optional<std::array<uint8_t, 6>> address,
                                     std::optional<std::array<uint8_t, 4>> password)
            : server_(std::move(server))
        {
            // 初始化地址和密码
            if (address.has_value())
            {
                address_ = *address;
            }
            else
            {
                address_.fill(0x00);
            }

            if (password.has_value())
            {
                password_ = *password;
            }
            else
            {
                password_.fill(0x00);
            }
        }

        // 初始化方法，用于在对象完全构造后设置连接处理器
        void ServerService::init()
        {
            if (server_)
            {
                server_->setConnectionHandler(shared_from_this());
            }
        }

        void ServerService::registerDevice(const std::array<uint8_t, 6> &addr)
        {
            address_ = addr;
            LOG_INFO("Device registered with address: {}",
                     common::bytesToHexString(std::vector<uint8_t>(addr.begin(), addr.end())));
        }

        bool ServerService::validateDevice(const std::array<uint8_t, 6> &address) const
        {
            // 处理特殊命令地址
            if (std::all_of(address.begin(), address.end(), [](uint8_t b)
                                    { return b == 0xAA; }))
            {
                return true; // 读通讯地址命令
            }

            if (std::all_of(address.begin(), address.end(), [](uint8_t b)
                                    { return b == 0x99; }))
            {
                return true; // 广播时间同步命令
            }
            return address == address_;
        }

        void ServerService::setTime(const std::vector<uint8_t> &dataBytes)
        {
            if (dataBytes.size() != 6) return;
            std::array<int, 6> fields{};
            for (size_t i = 0; i < fields.size(); ++i) {
                const auto value = dataBytes[i];
                if ((value & 0x0F) > 9 || (value >> 4) > 9) return;
                fields[i] = (value >> 4) * 10 + (value & 0x0F);
            }
            std::tm localTime{};
            localTime.tm_year = 100 + fields[0];
            localTime.tm_mon = fields[1] - 1;
            localTime.tm_mday = fields[2];
            localTime.tm_hour = fields[3];
            localTime.tm_min = fields[4];
            localTime.tm_sec = fields[5];
            const auto timestamp = std::mktime(&localTime);
            if (timestamp == static_cast<std::time_t>(-1)
                || localTime.tm_year != 100 + fields[0] || localTime.tm_mon != fields[1] - 1
                || localTime.tm_mday != fields[2] || localTime.tm_hour != fields[3]
                || localTime.tm_min != fields[4] || localTime.tm_sec != fields[5]) return;
            time_ = std::chrono::system_clock::from_time_t(timestamp);
        }

        void ServerService::setAddress(const std::array<uint8_t, 6> &address)
        {
            if (address.size() != 6)
            {
                throw std::invalid_argument("Invalid address length");
            }
            address_ = address;
            LOG_INFO("Device address set to: {}", common::bytesToHexString(std::vector<uint8_t>(address.begin(), address.end())));
        }

        namespace {
        template <typename T>
        bool setDataItem(model::DataItemManager& manager, uint32_t di, const T& value, const char* category)
        {
            static_assert(std::is_same_v<T, float> || std::is_same_v<T, model::Demand>, "Unsupported data item value");
            const float numericValue = [&]() {
                if constexpr (std::is_same_v<T, model::Demand>) return value.value;
                else return value;
            }();
            LOG_INFO("Setting {} value for DI={}: {}", category, di, numericValue);
            auto item = manager.getDataItem(di);
            if (!item) {
                LOG_ERROR("Failed to get data item");
                return false;
            }
            if (!model::isValueValid(item->dataFormat, numericValue)) {
                LOG_ERROR("Value {} is out of range for data format {}", numericValue, item->dataFormat);
                return false;
            }
            item->value = value;
            item->setTimestamp(std::chrono::system_clock::now());
            return manager.updateDataItem(di, *item);
        }
        } // namespace

        bool ServerService::set00(uint32_t di, float value) { return setDataItem(dataItems_, di, value, "energy"); }
        bool ServerService::set01(uint32_t di, const model::Demand& demand) { return setDataItem(dataItems_, di, demand, "demand"); }
        bool ServerService::set02(uint32_t di, float value) { return setDataItem(dataItems_, di, value, "variable"); }

        namespace {
        bool setFields(model::DataItemManager& manager, uint32_t di, uint8_t category,
                       const std::vector<std::string>& values)
        {
            if ((di >> 24) != category) return false;
            auto item = manager.getDataItem(di);
            if (!item || item->fields.size() != values.size()) return false;
            for (size_t i = 0; i < values.size(); ++i) item->fields[i].value = values[i];
            std::vector<uint8_t> encoded;
            if (!detail::encodeFields(item->fields, encoded) || encoded.size() + 4 > 255) return false;
            if (values.size() == 1) item->value = values[0];
            item->setTimestamp(std::chrono::system_clock::now());
            return manager.updateDataItem(di, *item);
        }
        }

        bool ServerService::set03(uint32_t di, const std::vector<std::string>& values)
        { return setFields(dataItems_, di, 0x03, values); }
        bool ServerService::set04(uint32_t di, const std::vector<std::string>& values)
        { return setFields(dataItems_, di, 0x04, values); }

        void ServerService::setPassword(const std::array<uint8_t, 4> &password)
        {
            if (password.size() != 4)
            {
                throw std::invalid_argument("Invalid password length");
            }
            password_ = password;

            std::string passwordStr;
            for (const auto &byte : password)
            {
                passwordStr += fmt::format("{:02X}", byte);
            }
            LOG_INFO("Password set to: {}", passwordStr);
        }

        std::shared_ptr<model::DataItem> ServerService::getDataItem(uint32_t di) const
        {
            const auto dataItem = dataItems_.getDataItem(di);
            if (!dataItem)
            {
                return nullptr;
            }
            return dataItem;
        }

        void ServerService::onConnectionClosed()
        {
            LOG_INFO("Connection closed");
            // 可以在这里添加连接关闭时的清理逻辑
        }

        std::vector<uint8_t> ServerService::errorResponse(const protocol::Frame& frame, uint8_t errorCode) const
        {
            return protocol::Frame::buildFrame(frame.addr, frame.ctrlCode | 0xC0, {errorCode});
        }

        std::vector<uint8_t> ServerService::handleRequest(const protocol::Frame &frame)
        {
            // 1. 验证设备
            if (!validateDevice(frame.addr))
            {
                LOG_INFO("Device validation failed for address: {}",
                         common::bytesToHexString(std::vector<uint8_t>(frame.addr.begin(), frame.addr.end())));
                return errorResponse(frame, 0x01);
            }

            // 2. 根据控制码判断请求类型
            switch (frame.ctrlCode)
            {
            case model::BROADCAST_TIME_SYNC:
            {
                LOG_INFO("Broadcast time sync: {}", common::bytesToHexString(frame.data));
                setTime(frame.data);
                return {}; // Broadcast time sync has no response.
            }

            case model::CTRL_FREEZE_CMD:
            {
                if (frame.data.size() != 4) return errorResponse(frame, 0x02);
                std::array<uint8_t, 4> freezeTime{};
                std::copy(frame.data.begin(), frame.data.end(), freezeTime.begin());
                lastFreezeTime_ = freezeTime;
                const std::array<uint8_t, 6> broadcastAddress = {0x99, 0x99, 0x99, 0x99, 0x99, 0x99};
                if (frame.addr == broadcastAddress) return {};
                return protocol::Frame::buildFrame(frame.addr, frame.ctrlCode | 0x80, {});
            }

            case model::CHANGE_BAUD_RATE:
            {
                if (frame.data.size() != 1) return errorResponse(frame, 0x02);
                switch (frame.data[0]) {
                case 0x04: baudRate_ = 1200; break;
                case 0x08: baudRate_ = 2400; break;
                case 0x16: baudRate_ = 4800; break;
                case 0x32: baudRate_ = 9600; break;
                case 0x64: baudRate_ = 19200; break;
                default: return errorResponse(frame, 0x08);
                }
                return protocol::Frame::buildFrame(frame.addr, frame.ctrlCode | 0x80, frame.data);
            }

            case model::CTRL_READ_DATA:
            {
                // 解析数据标识
                if (frame.data.size() < 4)
                {
                    LOG_ERROR("Invalid read request data length");
                    return errorResponse(frame, 0x02);
                }

                uint32_t di = dlt645::common::bytesToIntLittleEndian<uint32_t>(frame.data);
                LOG_DEBUG("Read request for DI: {}", di);

                // 检查数据标识的第三个字节
                uint8_t di3 = frame.data[3];

                switch (di3)
                {
                case 0x00:
                    // 读取电能
                    return handleReadEnergy(frame);

                case 0x01:
                    // 读取最大需量及发生时间
                    return handleReadDemand(frame);

                case 0x02:
                    // 读取变量
                    return handleReadVariable(frame);

                case 0x03:
                case 0x04:
                    return handleReadFields(frame);

                default:
                    LOG_INFO("Unknown data type: {}", fmt::format("{:02X}", di3));
                    return errorResponse(frame, 0x01);
                }
            }

            case model::READ_ADDRESS:
            {
                // 读地址请求
                std::vector<uint8_t> resData(address_.begin(), address_.end());
                return protocol::Frame::buildFrame(address_, frame.ctrlCode | 0x80, resData);
            }

            case model::WRITE_ADDRESS:
            {
                // 写地址请求
                if (frame.data.size() != 6) return errorResponse(frame, 0x02);
                std::array<uint8_t, 6> newAddr;
                std::copy(frame.data.begin(), frame.data.end(), newAddr.begin());
                setAddress(newAddr);
                return protocol::Frame::buildFrame(address_, frame.ctrlCode | 0x80, {});
            }

            case model::CHANGE_PASSWORD:
            {
                if (frame.data.size() != 12) return errorResponse(frame, 0x02);
                std::array<uint8_t, 4> oldPassword;
                std::array<uint8_t, 4> newPassword;
                std::copy_n(frame.data.begin() + 4, 4, oldPassword.begin());
                std::copy_n(frame.data.begin() + 8, 4, newPassword.begin());
                if (oldPassword != password_) return errorResponse(frame, 0x04);
                password_ = newPassword;
                return protocol::Frame::buildFrame(address_, frame.ctrlCode | 0x80,
                    std::vector<uint8_t>(newPassword.begin(), newPassword.end()));
            }

            case model::CTRL_WRITE_DATA:
            {
                if (frame.data.size() < 12) return errorResponse(frame, 0x02);
                const uint32_t di = common::bytesToIntLittleEndian<uint32_t>(frame.data);
                if ((di >> 24) != 0x04) return errorResponse(frame, 0x01);
                auto item = dataItems_.getDataItem(di);
                if (!item || item->fields.empty()) return errorResponse(frame, 0x02);
                if (!std::equal(password_.begin(), password_.end(), frame.data.begin() + 4))
                    return errorResponse(frame, 0x04);
                auto fields = item->fields;
                if (!detail::decodeFields(fields, frame.data, 12)) return errorResponse(frame, 0x02);
                item->fields = std::move(fields);
                if (item->fields.size() == 1) item->value = item->fields[0].value;
                item->setTimestamp(std::chrono::system_clock::now());
                if (!dataItems_.updateDataItem(di, *item)) return errorResponse(frame, 0x02);
                return protocol::Frame::buildFrame(address_, frame.ctrlCode | 0x80, {});
            }

            default:
            {
                LOG_INFO("Unknown control code: {}", fmt::format("{:02X}", frame.ctrlCode));
                return errorResponse(frame, 0x01);
            }
            }
            return {};
        }

        std::vector<uint8_t> ServerService::handleReadEnergy(const protocol::Frame &frame)
        {
            if (frame.data.size() < 4) return errorResponse(frame, 0x02);
            // 解析数据标识为32位无符号整数
            uint32_t dataId = dlt645::common::bytesToIntLittleEndian<uint32_t>(frame.data);

            // 获取数据项
            const auto dataItem = dataItems_.getDataItem(dataId);
            if (!dataItem)
            {
                LOG_ERROR("Data item not found for ID: {}", dataId);
                return errorResponse(frame, 0x02);
            }

            // 构建响应数据
            std::vector<uint8_t> resData(8);
            // 复制前4字节数据标识
            std::copy(frame.data.begin(), frame.data.begin() + 4, resData.begin());

            if (std::holds_alternative<float>(dataItem->value))
            {
                float value = std::get<float>(dataItem->value);
                // 将浮点数转换为BCD码
                auto bcdValue = dlt645::common::floatToBcd(value, dataItem->dataFormat, true);
                // 复制BCD值到响应数据
                if (bcdValue.size() >= 4)
                {
                    std::copy(bcdValue.begin(), bcdValue.begin() + 4, resData.begin() + 4);
                }
            }

            // 构建响应帧
            return protocol::Frame::buildFrame(frame.addr, frame.ctrlCode | 0x80, resData);
        }

        std::vector<uint8_t> ServerService::handleReadDemand(const protocol::Frame &frame)
        {
            if (frame.data.size() < 4) return errorResponse(frame, 0x02);
            // 解析数据标识为32位无符号整数
            uint32_t dataId = common::bytesToIntLittleEndian<uint32_t>(frame.data);

            // 获取数据项
            const auto dataItem = dataItems_.getDataItem(dataId);
            if (!dataItem)
            {
                LOG_ERROR("Data item not found for ID: {}", dataId);
                return errorResponse(frame, 0x02);
            }

            // 构建响应数据
            std::vector<uint8_t> resData(12);
            // 复制前4字节数据标识
            std::copy(frame.data.begin(), frame.data.begin() + 4, resData.begin());

            // 处理数据值
            if (std::holds_alternative<model::Demand>(dataItem->value))
            {
                const model::Demand &demand = std::get<model::Demand>(dataItem->value);
                // 将需量值转换为BCD码
                auto bcdValue = dlt645::common::floatToBcd(demand.value, dataItem->dataFormat, true);
                // 确保BCD值至少有3个字节
                if (bcdValue.size() < 3)
                {
                    bcdValue.resize(3, 0);
                }
                // 复制BCD值到响应数据
                if (bcdValue.size() >= 3)
                {
                    std::copy(bcdValue.begin(), bcdValue.begin() + 3, resData.begin() + 4);
                }

                // 获取当前时间并转换为BCD码
                auto timeBcd = dlt645::common::timeToBcd(demand.occurTime, true);
                // 复制时间BCD码到响应数据
                if (timeBcd.size() >= 5)
                {
                    std::copy(timeBcd.begin(), timeBcd.begin() + 5, resData.begin() + 7);
                }
            }

            LOG_INFO("Reading maximum demand and occurrence time: {}", common::bytesToHexString(resData));

            // 构建响应帧
            return protocol::Frame::buildFrame(frame.addr, frame.ctrlCode | 0x80, resData);
        }

        std::vector<uint8_t> ServerService::handleReadVariable(const protocol::Frame &frame)
        {
            if (frame.data.size() < 4) return errorResponse(frame, 0x02);
            // 解析数据标识为32位无符号整数
            uint32_t dataId = dlt645::common::bytesToIntLittleEndian<uint32_t>(frame.data);

            // 获取数据项
            const auto dataItem = dataItems_.getDataItem(dataId);
            if (!dataItem)
            {
                LOG_ERROR("Data item not found for ID: {}", dataId);
                return errorResponse(frame, 0x02);
            }

            const size_t digits = std::count(dataItem->dataFormat.begin(), dataItem->dataFormat.end(), 'X');
            const size_t dataLen = 4 + (digits + 1) / 2;

            // 构建响应数据
            std::vector<uint8_t> resData(dataLen);
            // 复制前4字节数据标识
            std::copy(frame.data.begin(), frame.data.begin() + 4, resData.begin());

            // 处理数据值
            if (std::holds_alternative<float>(dataItem->value))
            {
                float value = std::get<float>(dataItem->value);
                // 将浮点数转换为BCD码（小端序）
                auto bcdValue = dlt645::common::floatToBcd(value, dataItem->dataFormat, true);
                // 复制BCD值到响应数据
                size_t bcdCopyLen = std::min(bcdValue.size(), dataLen - 4);
                std::copy(bcdValue.begin(), bcdValue.begin() + bcdCopyLen, resData.begin() + 4);
            }

            // 构建响应帧
            return protocol::Frame::buildFrame(frame.addr, frame.ctrlCode | 0x80, resData);
        }

        std::vector<uint8_t> ServerService::handleReadFields(const protocol::Frame& frame)
        {
            if (frame.data.size() != 4) return errorResponse(frame, 0x02);
            const uint32_t di = common::bytesToIntLittleEndian<uint32_t>(frame.data);
            const auto item = dataItems_.getDataItem(di);
            if (!item || item->fields.empty()) return errorResponse(frame, 0x02);
            std::vector<uint8_t> response(frame.data.begin(), frame.data.end());
            if (!detail::encodeFields(item->fields, response) || response.size() > 255)
                return errorResponse(frame, 0x02);
            return protocol::Frame::buildFrame(frame.addr, frame.ctrlCode | 0x80, response);
        }

        bool ServerService::start()
        {
            if (server_)
            {
                return server_->start();
            }
            return false;
        }

        void ServerService::stop()
        {
            if (server_)
            {
                server_->stop();
            }
        }

        std::shared_ptr<ServerService> createTcpServer(const std::string &ip, uint16_t port, std::chrono::milliseconds timeout)
        {
            DIManager::preInit();
            // 1. 先创建TcpServer
            auto tcpServer = std::make_shared<transport::server::TcpServer>();
            transport::server::TcpServerConfig config;
            config.ip = ip;
            config.port = port;
            config.timeout = timeout;

            if (!tcpServer->configure(config))
            {
                LOG_ERROR("Failed to configure TCP server");
                return nullptr;
            }

            // 2. 创建ServerService，注入TcpServer
            auto serverService = std::make_shared<ServerService>(tcpServer);

            // 3. 在对象完全构造后调用init()方法设置连接处理器
            serverService->init();

            return serverService;
        }

        std::shared_ptr<ServerService> createRtuServer(const std::string &port,
                                                       int baudrate,
                                                       int databits,
                                                       int stopbits,
                                                       const std::string &parity,
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

            if (!rtuServer->configure(config))
            {
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
