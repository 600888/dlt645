#pragma once

// 整数类型文件行号
#ifdef _WIN32
#define __FILENAME__ (strrchr(__FILE__, '\\') ? (strrchr(__FILE__, '\\') + 1) : __FILE__)
#else
#define __FILENAME__ (strrchr(__FILE__, '/') ? (strrchr(__FILE__, '/') + 1) : __FILE__)
#endif

// 格式化
#ifndef FORMATTED
#define FORMATTED(format) "[" __FILENAME__ "]<" __FUNCTION__ "> - " format
#endif