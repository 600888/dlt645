#include "dlt645/protocol/protocol.h"
#include <algorithm>
#include <stdexcept>
#include <array>

namespace dlt645
{
    namespace protocol
    {

        // 解码数据域（±33H转换）
        std::vector<uint8_t> Frame::decodeData(const std::vector<uint8_t>& data)
        {
            std::vector<uint8_t> result(data.size());
            std::transform(data.begin(), data.end(), result.begin(), [](uint8_t b)
                                   { return b - 0x33; });
            return result;
        }

        // 编码数据域（±33H转换）
        std::vector<uint8_t> Frame::encodeData(const std::vector<uint8_t>& data)
        {
            std::vector<uint8_t> result(data.size());
            std::transform(data.begin(), data.end(), result.begin(), [](uint8_t b)
                                   { return b + 0x33; });
            return result;
        }

        // 计算校验和（模256求和）
        uint8_t Frame::calculateChecksum(const uint8_t* data, size_t length)
        {
            uint8_t sum = 0;
            for (size_t i = 0; i < length; ++i)
            {
                sum = static_cast<uint8_t>(sum + data[i]);
            }
            return sum;
        }

        // 构建帧
        std::vector<uint8_t>
        Frame::buildFrame(const std::array<uint8_t, 6>& addr, uint8_t ctrlCode, const std::vector<uint8_t> &data)
        {
            if (data.size() > 255) {
                throw std::length_error("DL/T 645 data field exceeds 255 bytes");
            }
            std::vector<uint8_t> buf;
            buf.reserve(12 + data.size()); // 预留空间

            buf.push_back(FRAME_START_BYTE);
            buf.insert(buf.end(), addr.begin(), addr.end());
            buf.push_back(FRAME_START_BYTE);
            buf.push_back(ctrlCode);

            // 数据域编码
            auto encodedData = encodeData(data);
            buf.push_back(static_cast<uint8_t>(encodedData.size()));
            buf.insert(buf.end(), encodedData.begin(), encodedData.end());

            // 计算校验和
            uint8_t calculatedChecksum = calculateChecksum(buf.data(), buf.size());
            buf.push_back(calculatedChecksum);
            buf.push_back(FRAME_END_BYTE);

            // 前导字节添加
            std::array<uint8_t, 4> preamble = {0xFE, 0xFE, 0xFE, 0xFE};
            buf.insert(buf.begin(), preamble.begin(), preamble.end());
            return buf;
        }

        // 序列化帧
        std::vector<uint8_t> Frame::serialize() const
        {
            if (startFlag != FRAME_START_BYTE || endFlag != FRAME_END_BYTE)
            {
                throw std::runtime_error("Invalid start or end flag");
            }
            if (data.size() > 255) {
                throw std::length_error("DL/T 645 data field exceeds 255 bytes");
            }

            std::vector<uint8_t> buf;
            buf.reserve(preamble.size() + 12 + data.size()); // 预留空间

            // 写入前导字节
            buf.insert(buf.end(), preamble.begin(), preamble.end());

            // 写入起始符
            buf.push_back(startFlag);

            // 写入地址
            buf.insert(buf.end(), addr.begin(), addr.end());

            // 写入第二个起始符
            buf.push_back(startFlag);

            // 写入控制码
            buf.push_back(ctrlCode);

            // 数据域编码
            auto encodedData = encodeData(data);

            // 写入数据长度
            buf.push_back(static_cast<uint8_t>(encodedData.size()));

            // 写入编码后的数据
            buf.insert(buf.end(), encodedData.begin(), encodedData.end());

            // 计算并写入校验和
            uint8_t calculatedChecksum = calculateChecksum(buf.data() + preamble.size(), buf.size() - preamble.size());
            buf.push_back(calculatedChecksum);

            // 写入结束符
            buf.push_back(endFlag);

            return buf;
        }

        // 反序列化帧
        std::shared_ptr<Frame> Frame::deserialize(const std::vector<uint8_t> &raw)
        {
            // 基础校验
            if (raw.size() < 12)
            { // 最小帧长度=起始符(1)+地址(6)+起始符(1)+控制码(1)+数据长度(1)+结束符(1)
                return nullptr;
            }

            // 帧边界检查
            auto startIt = std::find(raw.begin(), raw.end(), FRAME_START_BYTE);
            if (startIt == raw.end() || std::distance(startIt, raw.end()) < 12)
            {
                return nullptr;
            }

            size_t startIdx = std::distance(raw.begin(), startIt);
            if (startIdx + 7 >= raw.size() || raw[startIdx + 7] != FRAME_START_BYTE)
            { // 第二个起始符位置校验
                return nullptr;
            }

            // 构建帧结构
            auto frame = std::make_shared<Frame>();
            frame->startFlag = raw[startIdx];
            std::copy_n(raw.begin() + startIdx + 1, 6, frame->addr.begin());
            frame->ctrlCode = raw[startIdx + 8];
            frame->dataLen = raw[startIdx + 9];

            // 数据域提取
            size_t dataStart = startIdx + 10;
            size_t dataEnd = dataStart + frame->dataLen;
            if (dataEnd > raw.size() || raw.size() - dataEnd < 2)
            { // 预留校验位和结束符
                return nullptr;
            }

            // 数据域解码
            frame->data = decodeData(std::vector<uint8_t>(raw.begin() + dataStart, raw.begin() + dataEnd));

            // 校验和验证（从第一个68H到校验码前）
            uint8_t calculatedSum = calculateChecksum(raw.data() + startIdx, dataEnd - startIdx);

            if (calculatedSum != raw[dataEnd])
            {
                return nullptr;
            }

            // 结束符验证
            if (dataEnd + 1 >= raw.size() || raw[dataEnd + 1] != FRAME_END_BYTE)
            {
                return nullptr;
            }

            frame->checkSum = raw[dataEnd];
            frame->endFlag = raw[dataEnd + 1];
            frame->preamble.assign(raw.begin(), startIt);

            return frame;
        }

    } // namespace protocol
} // namespace dlt645
