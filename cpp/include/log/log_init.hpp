#pragma once
#include <cstdlib>
#include <iostream>
#include <string>
#include <unordered_map>

#include "spdlog/async.h"
#include "spdlog/sinks/basic_file_sink.h"
#include "spdlog/sinks/rotating_file_sink.h"
#include "spdlog/sinks/stdout_color_sinks.h"
#include "spdlog/spdlog.h"
#include "util/json_opt.hpp"

#include "util/conf.hpp"

// 编译release、链接时优化选项增加速度：-Wall -pthread -O3 -flto -DNDEBUG

#ifdef DEBUG
// 在spdlog.h之前定义才有效
#ifndef SPDLOG_TRACE_ON
#define SPDLOG_TRACE_ON
#endif

#ifndef SPDLOG_DEBUG_ON
#define SPDLOG_DEBUG_ON
#endif

#endif

// Linux使用CLOCK_REALTIME_COARSE
#ifndef SPDLOG_CLOCK_COARSE
#define SPDLOG_CLOCK_COARSE
#endif

using LV = spdlog::level::level_enum;

struct LogInfo {
  LV level = LV::debug;
  long long fileSize = 1024 * 1024 * 10 * 10;
  int count = 10;
  bool console = false;
};

class LogInitializer {
public:
  LogInitializer(const std::string &defaultLoggerName,
                 LV defalutLogLevel = LV::info, bool enableTerminalLog = false,
                 const int threadNum = 1) noexcept {
    static std::once_flag flag = std::once_flag();
    std::call_once(flag, init, defaultLoggerName, defalutLogLevel,
                   enableTerminalLog, threadNum);
  }

private:
  LogInitializer(const LogInitializer &) = delete;
  LogInitializer &operator=(const LogInitializer &) = delete;

  // 读取日志配置文件
  static inline std::unordered_map<std::string, LogInfo> _readLogConf() {
    std::unordered_map<std::string, LogInfo> logConfMap;
    std::unordered_map<std::string, LV> logLevelMap{{"debug", LV::debug},
                                                    {"info", LV::info},
                                                    {"trace", LV::critical},
                                                    {"error", LV::err},
                                                    {"critical", LV::critical},
                                                    {"warn", LV::warn},
                                                    {"off", LV::off}};

    try {
      std::ifstream in(logConfPath(), std::ios::in);
      if (!in.is_open()) {
        throw std::runtime_error("无法打开设备配置文件!");
      }
      std::string jsonContent((std::istreambuf_iterator<char>(in)),
                              std::istreambuf_iterator<char>());
      in.close();

      JsonDoc jsonDoc;
      if (jsonDoc.Parse(jsonContent.c_str()).HasParseError()) {
        throw std::runtime_error("读取json错误!");
      }

      // 遍历所有模块并打印其级别和文件大小
      if (jsonDoc.HasMember("modules") && jsonDoc["modules"].IsObject()) {
        LogInfo logInfo;
        for (auto it = jsonDoc["modules"].MemberBegin();
             it != jsonDoc["modules"].MemberEnd(); ++it) {
          std::string modulesStr = std::string(it->name.GetString());
          if (it->value.HasMember("level") && it->value["level"].IsString()) {
            auto level = it->value["level"].GetString();
            std::string levelStr = std::string(level);
            if (logLevelMap.find(levelStr) != logLevelMap.end()) {
              logInfo.level = logLevelMap[levelStr];
            }
          }
          if (it->value.HasMember("file_size") &&
              it->value["file_size"].IsInt()) {
            auto fileSize = it->value["file_size"].GetInt();
            logInfo.fileSize = fileSize;
          }
          if (it->value.HasMember("count") && it->value["count"].IsInt()) {
            auto count = it->value["count"].GetInt();
            logInfo.count = count;
          }
          if (it->value.HasMember("console") && it->value["console"].IsBool()) {
            auto console = it->value["console"].GetBool();
            logInfo.console = console;
          }
          logConfMap[modulesStr] = logInfo;
        }
      }
    } catch (const std::exception &e) {
      throw std::runtime_error("导入配置文件失败!");
    }
    return logConfMap;
  }

  static inline void init(const std::string &defaultLoggerName,
                          LV /*defalutLogLevel*/, bool enableTerminalLog,
                          const int threadNum) noexcept {
    try {
      if (defaultLoggerName.empty() ||
          spdlog::get(defaultLoggerName) != nullptr) {
        return;
      }

      // 读取配置文件
      std::unordered_map<std::string, LogInfo> logConfMap = _readLogConf();
      constexpr int oneMb = 1024 * 1024;
      long long fileSize = 10 * oneMb;
      LV logLevel = LV::debug;
      int count = 10;
      bool console = enableTerminalLog;  // 默认使用构造函数参数，可被配置文件覆盖
      if (logConfMap.find(defaultLoggerName) != logConfMap.end()) {
        logLevel = logConfMap[defaultLoggerName].level;
        fileSize = logConfMap[defaultLoggerName].fileSize * oneMb;
        count = logConfMap[defaultLoggerName].count;
        console = logConfMap[defaultLoggerName].console;
      }

      // 添加目的端
      std::vector<spdlog::sink_ptr> sinks;

      // 检查是否开启控制台
      if (console) {
        sinks.push_back(
            std::make_shared<spdlog::sinks::stdout_color_sink_mt>());
      }

      // 日志路径
      std::string logFilePath =
          logPath() + defaultLoggerName + "/" + defaultLoggerName;
      if (logLevel == LV::debug) {
        logFilePath += "-debug.log";
      } else {
        logFilePath += ".log";
      }

      // 设置为滚动模式
      auto rotating_sink =
          std::make_shared<spdlog::sinks::rotating_file_sink_mt>(
              logFilePath, fileSize, count);
      sinks.push_back(rotating_sink);

      // 设置为异步模式
      spdlog::init_thread_pool(
          8192,
          threadNum); // 不要在其他地方再次调用init_thread_pool，否则会导致线程池析构
      std::shared_ptr<spdlog::logger> defaultLogger =
          std::make_shared<spdlog::async_logger>(
              defaultLoggerName, begin(sinks), end(sinks),
              spdlog::thread_pool(), spdlog::async_overflow_policy::block);

      // register日志
      spdlog::register_logger(defaultLogger);

      // 设置日志等级
      defaultLogger->set_level(logLevel);

      // 设置日志格式[年-月-日
      // 时:分:秒.毫秒][进程号:线程号][调试级别](宏定义中添加:
      // [文件名:行号]<函数名> - 具体内容)
      defaultLogger->set_pattern("[%Y-%m-%d %H:%M:%S.%e][%P:%t][%l]%v");

      // 设置当出发debug或更严重的错误时立刻刷新日志到disk
      defaultLogger->flush_on(logLevel);

      spdlog::set_default_logger(defaultLogger);
    } catch (...) {
      spdlog::drop_all();
    }
  };
};