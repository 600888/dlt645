#pragma once
#include "util/log_base.h"

// 移除静态初始化，改为手动初始化
// 在main函数中调用LogInitializer手动初始化日志系统