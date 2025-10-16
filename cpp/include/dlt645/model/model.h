#ifndef DLT645_MODEL_H
#define DLT645_MODEL_H

#include <array>
#include <chrono>
#include <compare>
#include <cstdint>
#include <span>
#include <string>
#include <variant>

namespace dlt645 {
    namespace model {

        enum class DataType {
            Energy = 0,
            Demand = 1,
            Variable = 2,
        };

        // 控制码定义
        inline constexpr uint8_t BROADCAST_TIME_SYNC = 0x08; // 广播校时
        inline constexpr uint8_t CTRL_READ_DATA = 0x11;      // 读数据
        inline constexpr uint8_t READ_ADDRESS = 0x13;        // 读通讯地址
        inline constexpr uint8_t CTRL_WRITE_DATA = 0x14;     // 写数据
        inline constexpr uint8_t WRITE_ADDRESS = 0x15;       // 写通讯地址
        inline constexpr uint8_t CTRL_FREEZE_CMD = 0x16;     // 冻结命令
        inline constexpr uint8_t CHANGE_BAUD_RATE = 0x17;    // 修改通信速率
        inline constexpr uint8_t CHANGE_PASSWORD = 0x18;     // 改变密码

        // 数据格式常量
        struct DataFormat {
            inline constexpr static auto XXXXXXXXXXXX = "XXXXXXXXXXXX";
            inline constexpr static auto XXXXXX_XX = "XXXXXX.XX";
            inline constexpr static auto XXXX_XX = "XXXX.XX";
            inline constexpr static auto XXX_XXX = "XXX.XXX";
            inline constexpr static auto XXX_X = "XXX.X";
            inline constexpr static auto XX_XXXX = "XX.XXXX";
            inline constexpr static auto XX_XX = "XX.XX";
            inline constexpr static auto X_XXX = "X.XXX";
        };

        // 需量结构体
        struct Demand {
            float value = 0.0f;                              // 需量值
            std::chrono::system_clock::time_point occurTime; // 需量发生时间
            Demand(float value, std::chrono::system_clock::time_point occurTime)
                : value(value)
                , occurTime(occurTime)
            {
            }
        };

        bool isValueValid(const std::string& dataFormat, float value);

    } // namespace model
} // namespace dlt645

#endif // DLT645_MODEL_H