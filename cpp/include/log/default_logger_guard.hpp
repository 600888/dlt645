#pragma once
#include "default_logger.hpp"

//
#define LOG_FUNC_BEG LOG_DEBUG("begin func {}", __FUNCTION__);
#define LOG_FUNC_END LOG_DEBUG("end func {}", __FUNCTION__);

//
template <LV lv = LV::debug> class LogGuard {
public:
  LogGuard(const std::string &msg) : _msg(msg) {
    switch (_lv) {
    case LV::debug:
      DefaultLogger::debug(fmt::format("{} begin", _msg).c_str());
      break;
    case LV::info:
    default:
      DefaultLogger::info(fmt::format("{} begin", _msg).c_str());
      break;
    }
  }

  ~LogGuard() {
    switch (_lv) {
    case LV::debug:
      DefaultLogger::debug(fmt::format("{} end", _msg).c_str());
      break;
    case LV::info:
    default:
      DefaultLogger::info(fmt::format("{} end", _msg).c_str());
      break;
    }
  }

private:
  LV _lv = lv;
  std::string _msg;
};

#define LOG_FUNC                                                               \
  LogGuard logGuard(std::string("[")                                           \
                        .append(__FILENAME__)                                  \
                        .append(":")                                           \
                        .append(std::to_string(__LINE__))                      \
                        .append("]<")                                          \
                        .append(__FUNCTION__)                                  \
                        .append("> - ")                                        \
                        .c_str());
