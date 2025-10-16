#include "dlt645/common/transform.h"
#include "dlt645/common/log.h"
#include <cmath>

namespace dlt645 {
    namespace common {

        // 字节数组转十六进制字符串
        std::string bytesToHexString(const std::vector<uint8_t>& bytes, bool uppercase, bool withSpace)
        {
            std::ostringstream oss;
            oss << std::setfill('0');

            for (size_t i = 0; i < bytes.size(); ++i) {
                if (i > 0 && withSpace) {
                    oss << ' ';
                }
                oss << std::hex << std::setw(2);
                if (uppercase) {
                    oss << std::uppercase;
                }
                oss << static_cast<int>(bytes[i]);
            }

            return oss.str();
        }

        // 十六进制字符串转字节数组
        std::optional<std::vector<uint8_t>> hexStringToBytes(const std::string& hex)
        {
            std::vector<uint8_t> outBytes;

            // 去除所有空格
            std::string cleanHex = hex;
            cleanHex.erase(std::remove(cleanHex.begin(), cleanHex.end(), ' '), cleanHex.end());

            // 检查长度是否为偶数
            if (cleanHex.length() % 2 != 0) {
                return std::nullopt;
            }

            try {
                outBytes.reserve(cleanHex.length() / 2);
                for (size_t i = 0; i < cleanHex.length(); i += 2) {
                    std::string byteString = cleanHex.substr(i, 2);
                    uint8_t byte = static_cast<uint8_t>(std::stoi(byteString, nullptr, 16));
                    outBytes.push_back(byte);
                }
                return outBytes;
            } catch (const std::exception&) {
                return std::nullopt;
            }
        }

        // 计算CRC校验
        uint16_t calculateCRC(const std::vector<uint8_t>& data)
        {
            uint16_t crc = 0xFFFF;

            for (uint8_t byte : data) {
                crc ^= static_cast<uint16_t>(byte);
                for (int i = 0; i < 8; ++i) {
                    if (crc & 0x0001) {
                        crc = (crc >> 1) ^ 0xA001;
                    } else {
                        crc = crc >> 1;
                    }
                }
            }

            return crc;
        }

        // 计算LRC校验
        uint8_t calculateLRC(const std::vector<uint8_t>& data)
        {
            uint8_t lrc = 0;

            for (uint8_t byte : data) {
                lrc ^= byte;
            }

            return lrc;
        }

        // 将整数转换为BCD码
        std::vector<uint8_t> intToBCD(uint32_t value, size_t byteCount, bool littleEndian)
        {
            std::vector<uint8_t> bcd;

            if (value == 0) {
                bcd.push_back(0x00);
            } else {
                while (value > 0) {
                    uint8_t digit = static_cast<uint8_t>(value % 10);
                    value /= 10;
                    uint8_t nextDigit = static_cast<uint8_t>(value % 10);
                    value /= 10;
                    bcd.push_back(static_cast<uint8_t>((nextDigit << 4) | digit));
                }
            }

            // 如果指定了字节数，填充或截断
            if (byteCount > 0) {
                if (bcd.size() < byteCount) {
                    // 填充零
                    bcd.insert(bcd.begin(), byteCount - bcd.size(), 0x00);
                } else if (bcd.size() > byteCount) {
                    // 截断
                    bcd.resize(byteCount);
                }
            }

            if (littleEndian) {
                std::reverse(bcd.begin(), bcd.end());
            }
            return bcd;
        }

        // 从BCD码转换为整数
        uint32_t bcdToInt(const std::vector<uint8_t>& bcd)
        {
            uint64_t result = 0; // 先用更大的类型避免溢出

            for (uint8_t byte : bcd) {
                // 检查BCD格式是否有效
                if (((byte >> 4) & 0x0F) > 9 || (byte & 0x0F) > 9) {
                    return 0;
                }

                // 高位
                result = result * 10 + ((byte >> 4) & 0x0F);
                // 低位
                result = result * 10 + (byte & 0x0F);

                // 检查是否溢出
                if (result > std::numeric_limits<uint32_t>::max()) {
                    return 0;
                }
            }

            return static_cast<uint32_t>(result);
        }

        // 浮点数转换为BCD码（支持大小端序）
        std::vector<uint8_t> floatToBcd(float value, const std::string& dataFormat, bool littleEndian)
        {
            std::vector<uint8_t> bcd;

            // 确定小数位数
            int decimalPlaces = 0;
            if (dataFormat.find('.') != std::string::npos) {
                size_t dotPos = dataFormat.find('.');
                decimalPlaces = static_cast<int>(dataFormat.length() - dotPos - 1);
            }

            // 计算缩放因子
            uint64_t scaleFactor = 1;
            for (int i = 0; i < decimalPlaces; ++i) {
                scaleFactor *= 10;
            }

            // 处理负值：取绝对值，后续可添加符号处理
            bool isNegative = value < 0;
            float absValue = std::abs(value);

            // 将浮点数转换为整数（四舍五入）
            uint64_t intValue = static_cast<uint64_t>(std::round(absValue * scaleFactor));

            // 特殊情况处理：值为0
            if (intValue == 0) {
                bcd.push_back(0x00);
                return bcd;
            }

            // 将整数转换为数字字符串以便处理
            std::string digits = std::to_string(intValue);

            // 确保数字位数为偶数，便于BCD编码
            if (digits.size() % 2 != 0) {
                digits = "0" + digits; // 前补0
            }

            // 转换为BCD码（压缩BCD：每个字节存储两个十进制数字）
            for (size_t i = 0; i < digits.size(); i += 2) {
                uint8_t highDigit = static_cast<uint8_t>(digits[i] - '0');
                uint8_t lowDigit = static_cast<uint8_t>(digits[i + 1] - '0');
                uint8_t bcdByte = static_cast<uint8_t>((highDigit << 4) | lowDigit);
                bcd.push_back(bcdByte);
            }

            // 处理符号位（如果需要）
            if (isNegative) {
                // 在最高字节添加符号标识，常见做法是最高位设为1
                if (!bcd.empty()) {
                    bcd[0] |= 0x80; // 设置最高位为1表示负数
                }
            }

            // 补齐到指定字节数
            while (bcd.size() < 4) {
                bcd.insert(bcd.begin(), 0x00);
            }

            // 大小端序处理
            if (littleEndian) {
                std::reverse(bcd.begin(), bcd.end());
            }

            return bcd;
        }

        // BCD码转换为浮点数（支持大小端序）
        float bcdToFloat(const std::vector<uint8_t>& bcd, const std::string& dataFormat, bool littleEndian)
        {
            // 检查输入参数
            if (bcd.empty()) {
                return 0.0f;
            }

            // 确定小数位数
            int decimalPlaces = 0;
            if (dataFormat.find('.') != std::string::npos) {
                size_t dotPos = dataFormat.find('.');
                decimalPlaces = static_cast<int>(dataFormat.length() - dotPos - 1);
            }

            // 复制BCD数据以便处理
            std::vector<uint8_t> bcdCopy = bcd;

            // 处理大小端序
            if (littleEndian) {
                std::reverse(bcdCopy.begin(), bcdCopy.end());
            }

            // 处理符号位
            bool isNegative = false;
            if ((bcdCopy[0] & 0x80) != 0) {
                isNegative = true;
                bcdCopy[0] &= 0x7F; // 清除符号位
            }

            // 将BCD码转换为数字字符串
            std::string digits;
            for (uint8_t byte : bcdCopy) {
                // 提取高位数字
                uint8_t highDigit = (byte >> 4) & 0x0F;
                // 提取低位数字
                uint8_t lowDigit = byte & 0x0F;

                // 检查BCD格式是否有效
                if (highDigit > 9 || lowDigit > 9) {
                    return 0.0f; // 无效的BCD格式
                }

                // 添加到数字字符串
                digits += (highDigit + '0');
                digits += (lowDigit + '0');
            }

            // 移除前导零
            size_t firstNonZero = digits.find_first_not_of('0');
            if (firstNonZero != std::string::npos) {
                digits = digits.substr(firstNonZero);
            } else {
                digits = "0"; // 所有位都是零
            }

            // 如果数字位数小于小数位数，前面补零
            while (digits.size() <= static_cast<size_t>(decimalPlaces)) {
                digits = "0" + digits;
            }

            // 插入小数点
            std::string floatStr;
            if (decimalPlaces > 0) {
                floatStr = digits.substr(0, digits.size() - decimalPlaces) + "." + digits.substr(digits.size() - decimalPlaces);
            } else {
                floatStr = digits;
            }

            // 转换为浮点数
            float result = std::stof(floatStr);

            // 应用符号
            if (isNegative) {
                result = -result;
            }

            return result;
        }

        // 时间转换为BCD码
        std::array<uint8_t, 5> timeToBcd(const std::chrono::system_clock::time_point& timePoint, bool littleEndian)
        {
            std::array<uint8_t, 5> result = { 0 };

            // 转换为本地时间
            auto time = std::chrono::system_clock::to_time_t(timePoint);
            std::tm localTime = *std::localtime(&time);

            // 年（后两位）
            uint8_t year = static_cast<uint8_t>(localTime.tm_year % 100);
            result[0] = static_cast<uint8_t>(((year / 10) << 4) | (year % 10));

            // 月
            uint8_t month = static_cast<uint8_t>(localTime.tm_mon + 1);
            result[1] = static_cast<uint8_t>(((month / 10) << 4) | (month % 10));

            // 日
            uint8_t day = static_cast<uint8_t>(localTime.tm_mday);
            result[2] = static_cast<uint8_t>(((day / 10) << 4) | (day % 10));

            // 时
            uint8_t hour = static_cast<uint8_t>(localTime.tm_hour);
            result[3] = static_cast<uint8_t>(((hour / 10) << 4) | (hour % 10));

            // 分
            uint8_t minute = static_cast<uint8_t>(localTime.tm_min);
            result[4] = static_cast<uint8_t>(((minute / 10) << 4) | (minute % 10));

            // 大小端序处理
            if (littleEndian) {
                std::reverse(result.begin(), result.end());
            }
            return result;
        }

        // 主转换函数：将BCD码字节数组转换为std::chrono::system_clock::time_point
        std::chrono::system_clock::time_point bcdToTime(std::vector<uint8_t> bcd)
        {
            // 提取并转换各时间字段
            int year = bcdToByte(bcd[0]) + 2000; // 假设为21世纪年份
            int month = bcdToByte(bcd[1]);
            int day = bcdToByte(bcd[2]);
            int hour = bcdToByte(bcd[3]);
            int minute = bcdToByte(bcd[4]);

            // 构造tm结构体
            std::tm time_struct = {};
            time_struct.tm_year = year - 1900; // tm_year从1900开始
            time_struct.tm_mon = month - 1;    // tm_mon从0开始（1月为0）
            time_struct.tm_mday = day;
            time_struct.tm_hour = hour;
            time_struct.tm_min = minute;

            // 将tm转换为time_t，再转换为system_clock::time_point
            std::time_t time_t_val = std::mktime(&time_struct);
            return std::chrono::system_clock::from_time_t(time_t_val);
        }

    } // namespace common
} // namespace dlt645