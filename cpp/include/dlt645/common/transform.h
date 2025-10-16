#ifndef DLT645_TRANSFORM_H
#define DLT645_TRANSFORM_H

#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <limits>
#include <optional>
#include <sstream>
#include <string>
#include <type_traits>
#include <vector>

namespace dlt645 {
    namespace common {

        // 字节数组转十六进制字符串
        std::string bytesToHexString(const std::vector<uint8_t>& bytes, bool uppercase = true, bool withSpace = true);

        // 十六进制字符串转字节数组
        std::optional<std::vector<uint8_t>> hexStringToBytes(const std::string& hex);

        // 计算CRC校验
        uint16_t calculateCRC(const std::vector<uint8_t>& data);

        // 计算LRC校验
        uint8_t calculateLRC(const std::vector<uint8_t>& data);

        // 将整数转换为BCD码
        std::vector<uint8_t> intToBCD(uint32_t value, size_t byteCount, bool littleEndian = true);

        // 从BCD码转换为整数
        uint32_t bcdToInt(const std::vector<uint8_t>& bcd);

        // 将浮点数转换为BCD码（根据数据格式）
        std::vector<uint8_t> floatToBcd(float value, const std::string& dataFormat, bool littleEndian = true);
        // BCD码转换为浮点数（根据数据格式）
        float bcdToFloat(const std::vector<uint8_t>& bcd, const std::string& dataFormat, bool littleEndian = true);

        // 时间转换为BCD码
        std::array<uint8_t, 5> timeToBcd(const std::chrono::system_clock::time_point& timePoint, bool littleEndian = true);

        // 辅助函数：将单个BCD字节转换为十进制数
        template <typename T>
        T bcdToByte(T bcd)
        {
            static_assert(std::is_integral<T>::value, "bcdToByte requires integral type");
            return ((bcd >> 4) * 10) + (bcd & 0x0F);
        }

        // 主转换函数：将BCD码字节数组转换为std::chrono::system_clock::time_point
        std::chrono::system_clock::time_point bcdToTime(std::vector<uint8_t> bcd);

        // 将小端序的字节数组转换为整数
        template <typename T = uint32_t>
        T bytesToIntLittleEndian(const std::vector<uint8_t>& bytes)
        {
            T result = 0;

            // 确保字节数不超过目标类型的大小
            size_t byteCount = std::min(bytes.size(), sizeof(T));

            // 小端序：低字节在前，高字节在后
            for (size_t i = 0; i < byteCount; ++i) {
                result |= static_cast<T>(bytes[i]) << (i * 8);
            }

            return result;
        }

    } // namespace common
} // namespace dlt645

#endif // DLT645_TRANSFORM_H