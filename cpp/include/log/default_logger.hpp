#pragma once
#include "spdlog/spdlog.h"
using LV = spdlog::level::level_enum;

// 提取文件名的辅助函数
inline const char *getFileName(const char *filePath)
{
  const char *fileName = strrchr(filePath, '/');
  return fileName ? fileName + 1 : filePath;
}

// 日志宏定义
#define LOG_TRACE(format, ...)                                                          \
  spdlog::trace("[{}:{}]<{}> - " format, getFileName(__FILE__), __LINE__, __FUNCTION__, \
                ##__VA_ARGS__)
#define LOG_DEBUG(format, ...)                                                          \
  spdlog::debug("[{}:{}]<{}> - " format, getFileName(__FILE__), __LINE__, __FUNCTION__, \
                ##__VA_ARGS__)
#define LOG_INFO(format, ...)                                                          \
  spdlog::info("[{}:{}]<{}> - " format, getFileName(__FILE__), __LINE__, __FUNCTION__, \
               ##__VA_ARGS__)
#define LOG_WARN(format, ...)                                                          \
  spdlog::warn("[{}:{}]<{}> - " format, getFileName(__FILE__), __LINE__, __FUNCTION__, \
               ##__VA_ARGS__)
#define LOG_ERROR(format, ...)                                                          \
  spdlog::error("[{}:{}]<{}> - " format, getFileName(__FILE__), __LINE__, __FUNCTION__, \
                ##__VA_ARGS__)
#define LOG_CRITICAL(format, ...)                                                          \
  spdlog::critical("[{}:{}]<{}> - " format, getFileName(__FILE__), __LINE__, __FUNCTION__, \
                   ##__VA_ARGS__)
// LOG_SEPARATOR 宏保持不变
#define LOG_SEPARATOR(content)                                             \
  spdlog::info("---------------------------{}---------------------------", \
               content)

// 保留DefaultLogger类以保持向后兼容性
class DefaultLogger
{
  DefaultLogger() = delete;
  DefaultLogger(const DefaultLogger &) = delete;

public:
  template <typename... Args>
  static inline void trace(const char *format, const Args &...args) noexcept
  {
    spdlog::trace(format, args...);
  }

  template <typename... Args>
  static inline void debug(const char *format, const Args &...args) noexcept
  {
    spdlog::debug(format, args...);
  }

  template <typename... Args>
  static inline void info(const char *format, const Args &...args) noexcept
  {
    spdlog::info(format, args...);
  }

  template <typename... Args>
  static inline void warn(const char *format, const Args &...args) noexcept
  {
    spdlog::warn(format, args...);
  }

  template <typename... Args>
  static inline void error(const char *format, const Args &...args) noexcept
  {
    spdlog::error(format, args...);
  }

  template <typename... Args>
  static inline void critical(const char *format,
                              const Args &...args) noexcept
  {
    spdlog::critical(format, args...);
  }
};
