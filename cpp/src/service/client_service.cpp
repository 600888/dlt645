#include "dlt645/service/client_service.h"
#include <ctime>
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <sys/types.h>
#include <vector>
#include "dlt645/common/log.h"
#include "dlt645/common/transform.h"
#include "dlt645/model/data_item.h"
#include "dlt645/model/model.h"
#include "dlt645/transport/client/client_api.h"
#include "log/default_logger.hpp"
#include "field_codec.h"

namespace dlt645 {
    namespace service {

        ClientService::ClientService(std::shared_ptr<transport::client::Connection> conn)
            : connection_(std::move(conn))
        {
            // 初始化地址和密码为全0
            address_.fill(0);
            password_.fill(0);
        }

        ClientService::~ClientService()
        {
            // 确保断开连接
            if (connection_ && connection_->isConnected()) {
                connection_->disconnect();
            }
        }

        std::shared_ptr<ClientService>
        ClientService::createTcpClient(const std::string& ip, uint16_t port, std::chrono::milliseconds timeout)
        {
            // 创建TCP客户端
            auto tcpClient = std::make_shared<transport::client::TcpClient>();
            transport::client::TcpClientConfig config;
            config.ip = ip;
            config.port = port;
            config.timeout = timeout;
            LOG_INFO("Creating TCP client with IP: {}, port: {}, timeout: {} ms", ip, port, timeout.count());

            if (!tcpClient->configure(config)) {
                LOG_ERROR("Failed to configure TCP client");
                return nullptr;
            }

            return std::make_shared<ClientService>(tcpClient);
        }

        std::shared_ptr<ClientService> ClientService::createRtuClient(const std::string& port,
                                                                      int baudrate,
                                                                      int databits,
                                                                      int stopbits,
                                                                      const std::string& parity,
                                                                      std::chrono::milliseconds timeout)
        {
            // 创建RTU客户端
            auto rtuClient = std::make_shared<transport::client::RtuClient>();
            transport::client::RtuClientConfig config;
            config.port = port;
            config.baudRate = baudrate;
            config.dataBits = databits;
            config.stopBits = stopbits;
            config.parity = parity;
            config.timeout = timeout;

            if (!rtuClient->configure(config)) {
                LOG_ERROR("Failed to configure RTU client");
                return nullptr;
            }

            return std::make_shared<ClientService>(rtuClient);
        }

        bool ClientService::setAddress(const std::array<uint8_t, 6>& address)
        {
            if (address == address_) {
                LOG_ERROR("New address is the same as current address");
                return false;
            }

            address_ = address;
            LOG_INFO("Client address set to: %02X %02X %02X %02X %02X %02X",
                     address_[0],
                     address_[1],
                     address_[2],
                     address_[3],
                     address_[4],
                     address_[5]);
            return true;
        }

        void ClientService::setPassword(const std::array<uint8_t, 4>& password)
        {
            if (password != password_) {
                password_ = password;
                LOG_INFO("Client password set");
            }
        }

        std::shared_ptr<model::DataItem> ClientService::read00(uint32_t di)
        {
            return readData(di);
        }

        std::shared_ptr<model::DataItem> ClientService::read01(uint32_t di)
        {
            return readData(di);
        }

        std::shared_ptr<model::DataItem> ClientService::read02(uint32_t di)
        {
            return readData(di);
        }

        std::shared_ptr<model::DataItem> ClientService::read03(uint32_t di)
        {
            return (di >> 24) == 0x03 ? readData(di) : nullptr;
        }

        std::shared_ptr<model::DataItem> ClientService::read04(uint32_t di)
        {
            return (di >> 24) == 0x04 ? readData(di) : nullptr;
        }

        bool ClientService::write04(uint32_t di, const std::vector<std::string>& values)
        {
            if ((di >> 24) != 0x04) return false;
            const auto item = DIManager::inst()->getDataItem(di);
            if (!item || item->fields.size() != values.size()) return false;
            auto fields = item->fields;
            for (size_t i = 0; i < values.size(); ++i) fields[i].value = values[i];
            std::vector<uint8_t> data;
            for (int shift = 0; shift < 32; shift += 8) data.push_back(static_cast<uint8_t>(di >> shift));
            data.insert(data.end(), password_.begin(), password_.end());
            data.insert(data.end(), 4, 0); // Operator code.
            if (!detail::encodeFields(fields, data) || data.size() > 255) return false;
            return static_cast<bool>(sendAndHandleRequest(
                protocol::Frame::buildFrame(address_, model::CTRL_WRITE_DATA, data)));
        }

        std::shared_ptr<model::DataItem> ClientService::readData(uint32_t di)
        {
            std::vector<uint8_t> data(4);
            data[0] = static_cast<uint8_t>(di & 0xFF);
            data[1] = static_cast<uint8_t>((di >> 8) & 0xFF);
            data[2] = static_cast<uint8_t>((di >> 16) & 0xFF);
            data[3] = static_cast<uint8_t>((di >> 24) & 0xFF);

            auto frame = protocol::Frame::buildFrame(address_, model::CTRL_READ_DATA, data);
            return sendAndHandleRequest(frame);
        }

        std::shared_ptr<model::DataItem> ClientService::readAddress()
        {
            // 构建请求帧，读地址命令不需要数据部分
            const std::array<uint8_t, 6> broadcastAddress = {0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA};
            auto frame = protocol::Frame::buildFrame(broadcastAddress, model::READ_ADDRESS, {});

            // 发送请求并处理响应
            return sendAndHandleRequest(frame);
        }

        std::shared_ptr<model::DataItem> ClientService::writeAddress(const std::array<uint8_t, 6>& newAddress)
        {
            if (newAddress == address_) {
                LOG_ERROR("New address is the same as current address");
                return nullptr;
            }

            std::vector<uint8_t> data(newAddress.begin(), newAddress.end());

            // 构建请求帧
            auto frame = protocol::Frame::buildFrame(address_, model::WRITE_ADDRESS, data);

            // 发送请求并处理响应
            auto response = sendAndHandleRequest(frame);

            // 如果成功，更新本地地址
            if (response) {
                address_ = newAddress;
            }

            return response;
        }

        bool ClientService::changePassword(const std::array<uint8_t, 4>& oldPassword, const std::array<uint8_t, 4>& newPassword)
        {
            const uint32_t di = 0x40000C00u | newPassword[0];
            std::vector<uint8_t> data;
            data.reserve(12);
            for (int shift = 0; shift < 32; shift += 8) {
                data.push_back(static_cast<uint8_t>(di >> shift));
            }
            data.insert(data.end(), oldPassword.begin(), oldPassword.end());
            data.insert(data.end(), newPassword.begin(), newPassword.end());

            // 构建请求帧
            auto frame = protocol::Frame::buildFrame(address_, model::CHANGE_PASSWORD, data);

            // 发送请求并处理响应
            auto response = sendAndHandleRequest(frame);

            // 如果成功，更新本地密码
            if (response) {
                password_ = newPassword;
                return true;
            }

            return false;
        }

        bool ClientService::broadcastTimeSync(std::chrono::system_clock::time_point time)
        {
            const auto timestamp = std::chrono::system_clock::to_time_t(time);
            std::tm localTime{};
#ifdef _WIN32
            if (localtime_s(&localTime, &timestamp) != 0) return false;
#else
            if (localtime_r(&timestamp, &localTime) == nullptr) return false;
#endif
            const std::array<int, 6> fields = {
                localTime.tm_year % 100, localTime.tm_mon + 1, localTime.tm_mday,
                localTime.tm_hour, localTime.tm_min, localTime.tm_sec};
            std::vector<uint8_t> data;
            for (int value : fields) {
                data.push_back(static_cast<uint8_t>(((value / 10) << 4) | (value % 10)));
            }
            const std::array<uint8_t, 6> broadcastAddr = {0x99, 0x99, 0x99, 0x99, 0x99, 0x99};

            // 构建请求帧
            auto frame = protocol::Frame::buildFrame(broadcastAddr, model::BROADCAST_TIME_SYNC, data);

            try {
                std::lock_guard<std::mutex> lock(mutex_);
                // 发送请求（广播消息不需要等待响应）
                if (!connection_->isConnected() && !connection_->connect()) {
                    LOG_ERROR("Failed to connect");
                    return false;
                }

                return connection_->sendOnly(frame);
            } catch (const std::exception& e) {
                LOG_ERROR("Exception during broadcast time sync: {}", e.what());
                return false;
            }
        }

        std::shared_ptr<model::DataItem> ClientService::freeze(
            const std::array<uint8_t, 4>& freezeTime, bool broadcast)
        {
            const std::vector<uint8_t> data(freezeTime.begin(), freezeTime.end());
            const std::array<uint8_t, 6> broadcastAddress = {0x99, 0x99, 0x99, 0x99, 0x99, 0x99};
            auto frame = protocol::Frame::buildFrame(
                broadcast ? broadcastAddress : address_, model::CTRL_FREEZE_CMD, data);
            if (!broadcast) return sendAndHandleRequest(frame);
            std::lock_guard<std::mutex> lock(mutex_);
            try {
                if (!connection_->isConnected() && !connection_->connect()) return nullptr;
                if (!connection_->sendOnly(frame)) return nullptr;
                auto result = std::make_shared<model::DataItem>();
                result->name = "广播冻结";
                result->value = common::bytesToHexString(data);
                return result;
            } catch (const std::exception& e) {
                LOG_ERROR("Broadcast freeze failed: {}", e.what());
                return nullptr;
            }
        }

        std::shared_ptr<model::DataItem> ClientService::changeBaudRate(int baud)
        {
            uint8_t feature = 0;
            switch (baud) {
            case 1200: feature = 0x04; break;
            case 2400: feature = 0x08; break;
            case 4800: feature = 0x16; break;
            case 9600: feature = 0x32; break;
            case 19200: feature = 0x64; break;
            default: return nullptr;
            }
            auto frame = protocol::Frame::buildFrame(address_, model::CHANGE_BAUD_RATE, {feature});
            auto result = sendAndHandleRequest(frame);
            if (!result || !std::holds_alternative<int32_t>(result->value)
                || std::get<int32_t>(result->value) != baud) return nullptr;
            return result;
        }

        bool ClientService::validateDevice(const std::array<uint8_t, 6>& addr) const
        {
            // 检查是否为请求的设备地址或广播地址（99类型）
            std::array<uint8_t, 6> broadcastAddr99 = { 0x99, 0x99, 0x99, 0x99, 0x99, 0x99 };

            // 接受设备自身地址或广播地址作为有效响应
            if (addr == address_ || addr == broadcastAddr99) {
                return true;
            } else {
                return false;
            }
        }

        std::shared_ptr<model::DataItem> ClientService::sendAndHandleRequest(const std::vector<uint8_t>& frame)
        {
            try {
                std::lock_guard<std::mutex> lock(mutex_);

                if (!connection_) {
                    LOG_ERROR("Connection is null");
                    return nullptr;
                }

                // 确保连接已建立
                if (!connection_->isConnected() && !connection_->connect()) {
                    LOG_ERROR("Failed to connect");
                    return nullptr;
                }

                // 发送请求并获取响应
                auto response = connection_->sendRequest(frame);
                if (response.empty()) {
                    LOG_ERROR("Empty response");
                    return nullptr;
                }
                LOG_INFO("Received response: {}", dlt645::common::bytesToHexString(response));

                // 反序列化响应帧
                auto responseFrame = protocol::Frame::deserialize(response);
                if (!responseFrame) {
                    LOG_ERROR("Failed to deserialize response frame");
                    return nullptr;
                }

                auto requestFrame = protocol::Frame::deserialize(frame);
                if (!requestFrame || (responseFrame->ctrlCode != (requestFrame->ctrlCode | 0x80)
                    && responseFrame->ctrlCode != (requestFrame->ctrlCode | 0xC0))) {
                    LOG_ERROR("Response control code does not match request");
                    return nullptr;
                }
                if (requestFrame->ctrlCode == model::CTRL_READ_DATA
                    && responseFrame->ctrlCode == (model::CTRL_READ_DATA | 0x80)
                    && (responseFrame->data.size() < 4 || requestFrame->data.size() < 4
                        || !std::equal(requestFrame->data.begin(), requestFrame->data.begin() + 4,
                                       responseFrame->data.begin()))) {
                    LOG_ERROR("Response data identifier does not match request");
                    return nullptr;
                }

                // 验证设备地址
                const bool addressReply = responseFrame->ctrlCode == (model::READ_ADDRESS | 0x80)
                    || responseFrame->ctrlCode == (model::WRITE_ADDRESS | 0x80);
                if (!addressReply && !validateDevice(responseFrame->addr)) {
                    LOG_ERROR("Device address validation failed");
                    return nullptr;
                }

                // 处理响应
                return handleResponse(responseFrame);
            } catch (const std::exception& e) {
                LOG_ERROR("Exception during sendAndHandleRequest: {}", e.what());
                return nullptr;
            }
        }

        std::shared_ptr<model::DataItem> ClientService::handleResponse(const std::shared_ptr<protocol::Frame>& frame)
        {
            if (!frame) {
                return nullptr;
            }
            if (frame->ctrlCode & 0x40) {
                LOG_ERROR("Meter returned error code {}", frame->data.empty() ? 0 : frame->data[0]);
                return nullptr;
            }

            // 使用switch-case结构处理不同的控制码
            switch (frame->ctrlCode) {
            case model::BROADCAST_TIME_SYNC | 0x80: {
                // 广播校时响应
                LOG_INFO("Broadcast time sync response received");
                // if (decodedData.size() >= 4) {
                //   // 提取时间戳
                //   auto timestamp = getTime(std::vector<uint8_t>(decodedData.begin(), decodedData.begin() + 4));
                // }
                break;
            }

            case model::CTRL_READ_DATA | 0x80: {
                // 读数据响应
                if (frame->data.size() >= 4) {
                    // 提取数据项标识符（小端序）
                    uint32_t di = dlt645::common::bytesToIntLittleEndian<uint32_t>(
                        std::vector<uint8_t>(frame->data.begin(), frame->data.begin() + 4));

                    // 获取数据类型（DI的第3个字节）
                    uint8_t diType = (di >> 24) & 0xFF;

                    // 从DataItemManager获取数据项定义
                    const auto dataItem = DIManager::inst()->getDataItem(di);
                    if (!dataItem) {
                        LOG_ERROR("Data item not found for ID: {}", di);
                        return nullptr;
                    }

                    // 根据数据类型处理值
                    switch (diType) {
                    case 0x00: {
                        // 00类：电能数据
                        LOG_INFO("Reading energy data response");
                        if (frame->data.size() >= 8) {
                            // 解析电能值（4-7字节）
                            std::vector<uint8_t> valueBytes(frame->data.begin() + 4, frame->data.begin() + 8);
                            float value = 0.0f;
                            if (!dataItem->dataFormat.empty()) {
                                // 使用dataFormat进行解析
                                value = common::bcdToFloat(valueBytes, dataItem->dataFormat, true);
                            }
                            dataItem->value = value;
                            return dataItem;
                        }
                        break;
                    }
                    case 0x01: {
                        // 01类：最大需量数据
                        LOG_INFO("Reading demand data response");
                        if (frame->data.size() >= 12) {
                            // 解析需量值（4-6字节）
                            std::vector<uint8_t> valueBytes(frame->data.begin() + 4, frame->data.begin() + 7);
                            float demandValue = 0.0f;

                            if (dataItem && !dataItem->dataFormat.empty()) {
                                // 使用dataFormat进行解析
                                demandValue = common::bcdToFloat(valueBytes, dataItem->dataFormat, true);
                            }

                            // 解析发生时间（7-11字节）
                            std::vector<uint8_t> timeBytes(frame->data.begin() + 7, frame->data.begin() + 12);
                            auto occurTime = common::bcdToTime(timeBytes);

                            // 创建需量对象
                            model::Demand demand(demandValue, occurTime);
                            dataItem->value = demand;
                            return dataItem;
                        }
                        break;
                    }
                    case 0x02: {
                        // 02类：变量数据
                        LOG_INFO("Reading variable data response");
                        const size_t digits = std::count(dataItem->dataFormat.begin(), dataItem->dataFormat.end(), 'X');
                        const size_t valueLength = (digits + 1) / 2;
                        if (valueLength > 0 && frame->data.size() >= 4 + valueLength) {
                            std::vector<uint8_t> valueBytes(frame->data.begin() + 4, frame->data.begin() + 4 + valueLength);
                            float value = 0.0f;
                            if (dataItem && !dataItem->dataFormat.empty()) {
                                // 使用dataFormat进行解析
                                value = common::bcdToFloat(valueBytes, dataItem->dataFormat, true);
                            }
                            dataItem->value = value;
                            return dataItem;
                        }
                        break;
                    }

                    case 0x03:
                    case 0x04: {
                        if (!detail::decodeFields(dataItem->fields, frame->data, 4)) return nullptr;
                        if (dataItem->fields.size() == 1) dataItem->value = dataItem->fields[0].value;
                        dataItem->timestamp = std::chrono::system_clock::now();
                        return dataItem;
                    }

                    default: {
                        LOG_WARN("Unknown data type: {}", diType);
                        break;
                    }
                    }
                }
                break;
            }

            case model::READ_ADDRESS | 0x80: {
                // 读地址响应
                LOG_INFO("Read address response received");
                if (frame->data.size() >= 6) {
                    // 更新本地地址
                    for (int i = 0; i < 6; i++) {
                        address_[i] = frame->data[i];
                    }
                    std::vector<uint8_t> di(frame->data.begin(), frame->data.begin() + 6);
                    std::vector<uint8_t> addressBytes(address_.begin(), address_.end());
                    LOG_INFO("Client address: {}", common::bytesToHexString(addressBytes));

                    // 创建数据项
                    auto dataItem = std::make_shared<model::DataItem>();
                    dataItem->di = common::bytesToIntLittleEndian<uint32_t>(di);
                    dataItem->name = "通讯地址";
                    dataItem->dataFormat = model::DataFormat::XXXXXXXXXXXX;
                    dataItem->value = common::bytesToHexString(addressBytes);
                    dataItem->unit = "";
                    dataItem->timestamp = std::chrono::system_clock::now();

                    return dataItem;
                }
                break;
            }

            case model::WRITE_ADDRESS | 0x80: {
                // 写地址响应
                LOG_INFO("Write address response received");
                auto dataItem = std::make_shared<model::DataItem>();
                dataItem->name = "通讯地址";
                dataItem->value = common::bytesToHexString(
                    std::vector<uint8_t>(frame->addr.begin(), frame->addr.end()));
                return dataItem;
            }

            case model::CHANGE_PASSWORD | 0x80: {
                if (frame->data.size() != 4) return nullptr;
                auto dataItem = std::make_shared<model::DataItem>();
                dataItem->name = "密码修改";
                dataItem->value = common::bytesToHexString(frame->data);
                return dataItem;
            }

            case model::CTRL_WRITE_DATA | 0x80: {
                if (!frame->data.empty()) return nullptr;
                auto dataItem = std::make_shared<model::DataItem>();
                dataItem->name = "Parameter write";
                return dataItem;
            }

            case model::CTRL_FREEZE_CMD | 0x80: {
                auto dataItem = std::make_shared<model::DataItem>();
                dataItem->name = "冻结命令";
                dataItem->value = std::string("已执行");
                return dataItem;
            }

            case model::CHANGE_BAUD_RATE | 0x80: {
                if (frame->data.size() != 1) return nullptr;
                int baud = 0;
                switch (frame->data[0]) {
                case 0x04: baud = 1200; break;
                case 0x08: baud = 2400; break;
                case 0x16: baud = 4800; break;
                case 0x32: baud = 9600; break;
                case 0x64: baud = 19200; break;
                default: return nullptr;
                }
                auto dataItem = std::make_shared<model::DataItem>();
                dataItem->name = "通信速率";
                dataItem->value = static_cast<int32_t>(baud);
                dataItem->unit = "bps";
                return dataItem;
            }

            default: {
                LOG_WARN("Unknown control code: {}", frame->ctrlCode);
                break;
            }
            }

            return nullptr;
        }

        std::chrono::system_clock::time_point ClientService::getTime(const std::vector<uint8_t>& t) const
        {
            if (t.size() < 4) {
                throw std::invalid_argument("Timestamp requires four bytes");
            }
            // 从字节数据获取时间戳
            uint32_t timestamp = dlt645::common::bytesToIntLittleEndian<uint32_t>(std::vector<uint8_t>(t.begin(), t.begin() + 4));
            LOG_INFO("Timestamp: {}", timestamp);

            // 转换为time_point
            return std::chrono::system_clock::from_time_t(static_cast<time_t>(timestamp));
        }

    } // namespace service
} // namespace dlt645
