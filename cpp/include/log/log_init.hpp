#pragma once

#include <filesystem>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

#include "spdlog/async.h"
#include "spdlog/sinks/rotating_file_sink.h"
#include "spdlog/sinks/stdout_color_sinks.h"
#include "spdlog/spdlog.h"
#include "util/env.hpp"

using LV = spdlog::level::level_enum;

class LogInitializer {
public:
    LogInitializer(const std::string& loggerName, LV level = LV::info,
                   bool enableTerminalLog = false, int threadNum = 1) noexcept
    {
        static std::once_flag flag;
        std::call_once(flag, init, loggerName, level, enableTerminalLog, threadNum);
    }

private:
    LogInitializer(const LogInitializer&) = delete;
    LogInitializer& operator=(const LogInitializer&) = delete;

    static void init(const std::string& loggerName, LV level,
                     bool enableTerminalLog, int threadNum) noexcept
    {
        try {
            if (loggerName.empty() || spdlog::get(loggerName)) return;

            std::vector<spdlog::sink_ptr> sinks;
            if (enableTerminalLog) {
                sinks.push_back(std::make_shared<spdlog::sinks::stdout_color_sink_mt>());
            }

            const auto directory = std::filesystem::path(logPath()) / loggerName;
            std::filesystem::create_directories(directory);
            const auto filename = loggerName + (level == LV::debug ? "-debug.log" : ".log");
            constexpr size_t fileSize = 10 * 1024 * 1024;
            constexpr size_t fileCount = 10;
            sinks.push_back(std::make_shared<spdlog::sinks::rotating_file_sink_mt>(
                (directory / filename).string(), fileSize, fileCount));

            spdlog::init_thread_pool(8192, threadNum > 0 ? threadNum : 1);
            auto logger = std::make_shared<spdlog::async_logger>(
                loggerName, sinks.begin(), sinks.end(), spdlog::thread_pool(),
                spdlog::async_overflow_policy::block);
            spdlog::register_logger(logger);
            logger->set_level(level);
            logger->set_pattern("[%Y-%m-%d %H:%M:%S.%e][%P:%t][%l]%v");
            logger->flush_on(level);
            spdlog::set_default_logger(logger);
        } catch (...) {
            spdlog::drop_all();
        }
    }
};
