#pragma once
#include "env.hpp"
#include <string>

// 日志配置文件
inline std::string logConfPath() { return confBasePath() + "/log.json"; }