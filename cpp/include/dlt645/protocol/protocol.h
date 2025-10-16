#ifndef DLT645_PROTOCOL_H
#define DLT645_PROTOCOL_H

#include <cstdint>
#include <memory>
#include <string>
#include <vector>
#include <array>
#include <span>

namespace dlt645 {
    namespace protocol {

        inline constexpr uint8_t FRAME_START_BYTE = 0x68;
        inline constexpr uint8_t FRAME_END_BYTE = 0x16;
        inline constexpr uint8_t BROADCAST_ADDR = 0xAA;

        // 帧结构体
        class Frame {
        public:
            std::vector<uint8_t> preamble; // 前导字节
            uint8_t startFlag = FRAME_START_BYTE;
            std::array<uint8_t, 6> addr = { 0 };
            uint8_t ctrlCode = 0;
            uint8_t dataLen = 0;
            std::vector<uint8_t> data;
            uint8_t checkSum = 0;
            uint8_t endFlag = FRAME_END_BYTE;

            // 默认构造函数
            Frame() = default;

            // 带参数的构造函数
            Frame(std::array<uint8_t, 6> address, uint8_t ctrl_code, const std::vector<uint8_t>& frame_data = {})
                : addr(address)
                , ctrlCode(ctrl_code)
                , data(frame_data)
            {
                dataLen = static_cast<uint8_t>(data.size());
            }

            // 序列化帧
            std::vector<uint8_t> serialize() const;

            // 反序列化帧
            static std::shared_ptr<Frame> deserialize(const std::vector<uint8_t>& raw);

            // 构建帧
            static std::vector<uint8_t>
            buildFrame(std::span<const uint8_t, 6> addr, uint8_t ctrlCode, const std::vector<uint8_t>& data);

            // 解码数据域（±33H转换）
            static std::vector<uint8_t> decodeData(std::span<const uint8_t> data);

            // 编码数据域（±33H转换）
            static std::vector<uint8_t> encodeData(std::span<const uint8_t> data);

        private:
            // 计算校验和（模256求和）
            static uint8_t calculateChecksum(std::span<const uint8_t> data);
        };

    } // namespace protocol
} // namespace dlt645

#endif // DLT645_PROTOCOL_H