#ifndef DLT645_DATA_ITEM_H
#define DLT645_DATA_ITEM_H

#include "model.h"
#include "util/singleton.hpp"
#include <cstdint>
#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

namespace dlt645 {
    namespace model {

        // 数据项结构体
        class DataItem {
        public:
            uint32_t di = 0;                                                                   // 数据项地址
            std::string name;                                                                  // 数据名称
            std::string dataFormat;                                                            // 数据格式
            std::variant<std::monostate, float, int32_t, uint32_t, std::string, Demand> value; // 实际值
            std::string unit;                                                                  // 单位（kW/kWh等）
            std::chrono::system_clock::time_point timestamp;                                   // 数据时间戳

            // 默认构造函数
            DataItem() = default;

            // 带参数的构造函数
            DataItem(uint32_t di,
                     const std::string& name,
                     const std::string& dataFormat,
                     const std::variant<std::monostate, float, int32_t, uint32_t, std::string, Demand>& value,
                     const std::string& unit)
                : di(di)
                , name(name)
                , dataFormat(dataFormat)
                , value(value)
                , unit(unit)
            {
            }

            // 从时间戳获取时间
            inline std::chrono::system_clock::time_point getTimestamp() const { return timestamp; }

            // 设置时间戳
            inline void setTimestamp(const std::chrono::system_clock::time_point& timePoint) { timestamp = timePoint; }

            inline void setValue(const std::variant<std::monostate, float, int32_t, uint32_t, std::string, Demand>& value)
            {
                this->value = value;
            }
        };

        // 全局数据项映射表管理类
        class DataItemManager {
        public:
            // 构造函数
            DataItemManager();

            // 初始化变量类型定义
            void initVariablesDef();

            // 初始化电能类型定义
            void initEnergyDef();

            // 初始化需量类型定义
            void initDemandDef();

            // 从JSON文件加载类型定义
            void loadTypeDefsFromJson();

            // 从指定JSON文件加载类型定义
            int loadTypeDefsFromFile(const std::string& filePath, const DataType& dataType);

            // 获取所有数据项类型定义
            const std::unordered_map<uint32_t, DataItem>& getDataItems() const;

            // 根据DI获取数据项类型定义 - 保持向后兼容
            std::shared_ptr<DataItem> getDataItem(uint32_t di) const;

            // 根据DI更新数据项
            bool updateDataItem(uint32_t di, const DataItem& dataItem);

            // 添加数据项类型定义
            void addDataItem(uint32_t di, const DataItem& dataItem);

            // 移除数据项类型定义
            void removeDataItem(uint32_t di);

        private:
            // 数据项映射表
            std::unordered_map<uint32_t, DataItem> diMap_;
            // 互斥锁，用于线程安全
            mutable std::mutex mutex_;
            std::vector<DataItem> energyTypes;
            std::vector<DataItem> demandTypes;
            std::vector<DataItem> variableTypes;
        };

    } // namespace model
} // namespace dlt645

using DIManager = Singleton<dlt645::model::DataItemManager>;
#endif // DLT645_DATA_ITEM_H
