#include <cstdio>
#include <iostream>
#include <vector>
#include <string>
#include "dlt645/common/transform.h"

int main()
{
    // 测试数据: BCD码12345678应该转换为123456.78
    std::vector<uint8_t> bcdData = { 0x12, 0x34, 0x56, 0x78 };
    std::string dataFormat = "XXXXXX.XX"; // 6位整数，2位小数

    // 使用原函数转换
    float result = dlt645::common::bcdToFloat(bcdData, dataFormat, false);
    std::printf("原始函数结果: %f\n", result);
    return 0;
}