#include "dlt645/model/data_item.h"
#include <fstream>
#include <memory>
#include <string>
#include "dlt645/common/log.h"
#include "dlt645/model/model.h"
#include "util/env.hpp"
#include "util/json_opt.hpp"

namespace dlt645 {
    namespace model {

        // 私有构造函数
        DataItemManager::DataItemManager()
        {
            LOG_DEBUG("DataItemManager: Constructor called - starting initialization");
            // 初始化所有类型定义
            loadTypeDefsFromJson();

            // 初始化电能、需量、变量类型定义
            initEnergyDef();
            initDemandDef();
            initVariablesDef();

            LOG_DEBUG("DataItemManager: Constructor completed - initialization finished");
        }

        // 从JSON文件加载类型定义
        void DataItemManager::loadTypeDefsFromJson()
        {
            std::lock_guard<std::mutex> lock(mutex_);

            // 构建配置文件路径
            std::string variableTypesFile = dataPath() + "variable_types.json";
            std::string energyTypesFile = dataPath() + "energy_types.json";
            std::string demandTypesFile = dataPath() + "demand_types.json";

            // 加载三种类型定义
            int loadedCount = 0;
            loadedCount += loadTypeDefsFromFile(energyTypesFile, DataType::Energy);
            loadedCount += loadTypeDefsFromFile(demandTypesFile, DataType::Demand);
            loadedCount += loadTypeDefsFromFile(variableTypesFile, DataType::Variable);

            LOG_INFO("Total loaded type definitions: {}", loadedCount);
        }

        // 添加数据项类型定义
        void DataItemManager::addDataItem(uint32_t di, const DataItem& dataItem)
        {
            std::lock_guard<std::mutex> lock(mutex_);
            diMap_[di] = dataItem;
        }

        // 移除数据项类型定义
        void DataItemManager::removeDataItem(uint32_t di)
        {
            std::lock_guard<std::mutex> lock(mutex_);
            auto it = diMap_.find(di);
            if (it != diMap_.end()) {
                diMap_.erase(it);
            }
        }

        // 从指定JSON文件加载数据项类型定义
        int DataItemManager::loadTypeDefsFromFile(const std::string& filePath, const DataType& dataType)
        {
            int count = 0;
            JsonDoc jsonDoc;

            LOG_INFO("Loading definitions from: {}", filePath);

            // 检查文件是否存在
            std::ifstream file(filePath);
            if (!file.is_open()) {
                LOG_ERROR("Failed to open file: {}", filePath);
                return count;
            }
            file.close();

            // 解析JSON文件
            if (!parseJsonDoc(filePath, jsonDoc)) {
                LOG_ERROR("Failed to parse JSON file: {}", filePath);
                return 0;
            }

            // 检查是否是数组
            if (!jsonDoc.IsArray()) {
                LOG_ERROR("JSON is not an array: {}", filePath);
                return 0;
            }

            // 遍历数组中的每个元素
            const rapidjson::Value& array = jsonDoc;
            for (rapidjson::SizeType i = 0; i < array.Size(); i++) {
                const rapidjson::Value& item = array[i];

                DataItem dataItem;

                // 解析Di (数据项地址)
                if (item.HasMember("Di") && item["Di"].IsString()) {
                    std::string diStr = item["Di"].GetString();
                    // 将16进制字符串转换为uint32_t
                    try {
                        dataItem.di = std::stoul(diStr, nullptr, 16);
                    } catch (...) {
                        LOG_WARN("Invalid Di value: {} in {} file", diStr, filePath);
                        continue;
                    }
                }

                // 解析Name (数据名称)
                if (item.HasMember("Name") && item["Name"].IsString()) {
                    dataItem.name = item["Name"].GetString();
                }

                // 解析Unit (单位)
                if (item.HasMember("Unit") && item["Unit"].IsString()) {
                    dataItem.unit = item["Unit"].GetString();
                }

                // 解析Dataformat (数据格式)
                if (item.HasMember("DataFormat") && item["DataFormat"].IsString()) {
                    dataItem.dataFormat = item["DataFormat"].GetString();
                }

                if (dataType == DataType::Energy) {
                    energyTypes.push_back(dataItem);
                } else if (dataType == DataType::Demand) {
                    demandTypes.push_back(dataItem);
                } else if (dataType == DataType::Variable) {
                    variableTypes.push_back(dataItem);
                }

                // 添加到映射表中
                diMap_[dataItem.di] = dataItem;
                count++;
            }

            LOG_INFO("Loaded {} type definitions", count);
            return count;
        }

        // 获取所有数据项类型定义
        const std::unordered_map<uint32_t, DataItem>& DataItemManager::getDataItems() const { return diMap_; }

        // 根据DI获取数据项类型定义 (保持向后兼容)
        std::shared_ptr<DataItem> DataItemManager::getDataItem(uint32_t di) const
        {
            std::lock_guard<std::mutex> lock(mutex_);

            auto it = diMap_.find(di);
            if (it != diMap_.end()) {
                return std::make_shared<DataItem>(it->second);
            }

            return nullptr;
        }

        // 根据DI获取可修改的数据项引用
        bool DataItemManager::updateDataItem(uint32_t di, const DataItem& dataItem)
        {
            std::lock_guard<std::mutex> lock(mutex_);

            auto it = diMap_.find(di);
            if (it != diMap_.end()) {
                // 更新原始数据项
                it->second = dataItem;
                return true;
            }

            return false;
        }

        // 初始化需量类型定义
        void DataItemManager::initDemandDef()
        {
            std::lock_guard<std::mutex> lock(mutex_);

            // 需求DI列表
            std::vector<uint32_t> demandDiList
                = { 0x01150000, 0x01160000, 0x01170000, 0x01180000, 0x01190000, 0x011A0000, 0x011B0000, 0x011C0000,
                    0x011D0000, 0x011E0000, 0x01290000, 0x012A0000, 0x012B0000, 0x012C0000, 0x012D0000, 0x012E0000,
                    0x012F0000, 0x01300000, 0x01310000, 0x01320000, 0x013D0000, 0x013E0000, 0x013F0000, 0x01400000,
                    0x01410000, 0x01420000, 0x01430000, 0x01440000, 0x01450000, 0x01460000 };

            LOG_INFO("Initializing demand definitions...");

            uint8_t di3 = 0; // 数据类型
            uint8_t di2 = 0; // 电能类型
            uint8_t di1 = 0; // 同一类型电能里的不同项
            uint8_t di0 = 0; // 结算日

            // 确保需求类型定义数量足够
            size_t requiredSize = 64 * 10 + demandDiList.size();
            if (demandTypes.size() < requiredSize) {
                LOG_WARN("Not enough demand types loaded, required: {}, actual: {}", requiredSize, demandTypes.size());
                // 调整循环范围以避免越界
                requiredSize = demandTypes.size();
            }

            // 遍历并创建需量数据项
            int demandSize = int(demandTypes.size());
            for (int i = 0; i < 64 && i < demandSize; ++i) {
                for (int j = 0; j < 13; ++j) {
                    std::string namePrefix;
                    if (j == 0) {
                        namePrefix = "（当前）";
                    } else {
                        namePrefix = "（上" + std::to_string(j) + "结算日）";
                    }

                    // 数据值默认为monostate
                    std::variant<std::monostate, float, int32_t, uint32_t, std::string, Demand> defaultValue;

                    // 正向有功需量
                    uint32_t key = (di3 + 1) << 24 | (di2 + 1) << 16 | (di1 + i) << 8 | (di0 + j);
                    if (i < demandSize) {
                        DataItem item(
                            key, namePrefix + demandTypes[i].name, DataFormat::XX_XXXX, defaultValue, demandTypes[i].unit);
                        diMap_[key] = item;
                    }

                    // 反向有功需量
                    key = (di3 + 1) << 24 | (di2 + 2) << 16 | (di1 + i) << 8 | (di0 + j);
                    if (64 + i < demandSize) {
                        DataItem item(key,
                                      namePrefix + demandTypes[64 + i].name,
                                      DataFormat::XX_XXXX,
                                      defaultValue,
                                      demandTypes[64 + i].unit);
                        diMap_[key] = item;
                    }

                    // 组合无功1需量
                    key = (di3 + 1) << 24 | (di2 + 3) << 16 | (di1 + i) << 8 | (di0 + j);
                    if (64 * 2 + i < demandSize) {
                        DataItem item(key,
                                      namePrefix + demandTypes[64 * 2 + i].name,
                                      DataFormat::XX_XXXX,
                                      defaultValue,
                                      demandTypes[64 * 2 + i].unit);
                        diMap_[key] = item;
                    }

                    // 组合无功2需量
                    key = (di3 + 1) << 24 | (di2 + 4) << 16 | (di1 + i) << 8 | (di0 + j);
                    if (64 * 3 + i < demandSize) {
                        DataItem item(key,
                                      namePrefix + demandTypes[64 * 3 + i].name,
                                      DataFormat::XX_XXXX,
                                      defaultValue,
                                      demandTypes[64 * 3 + i].unit);
                        diMap_[key] = item;
                    }

                    // 第一象限无功费率最大需量
                    key = (di3 + 1) << 24 | (di2 + 5) << 16 | (di1 + i) << 8 | (di0 + j);
                    if (64 * 4 + i < demandSize) {
                        DataItem item(key,
                                      namePrefix + demandTypes[64 * 4 + i].name,
                                      DataFormat::XX_XXXX,
                                      defaultValue,
                                      demandTypes[64 * 4 + i].unit);
                        diMap_[key] = item;
                    }

                    // 第二象限无功费率最大需量
                    key = (di3 + 1) << 24 | (di2 + 6) << 16 | (di1 + i) << 8 | (di0 + j);
                    if (64 * 5 + i < demandSize) {
                        DataItem item(key,
                                      namePrefix + demandTypes[64 * 5 + i].name,
                                      DataFormat::XX_XXXX,
                                      defaultValue,
                                      demandTypes[64 * 5 + i].unit);
                        diMap_[key] = item;
                    }

                    // 第三象限无功费率最大需量
                    key = (di3 + 1) << 24 | (di2 + 7) << 16 | (di1 + i) << 8 | (di0 + j);
                    if (64 * 6 + i < demandSize) {
                        DataItem item(key,
                                      namePrefix + demandTypes[64 * 6 + i].name,
                                      DataFormat::XX_XXXX,
                                      defaultValue,
                                      demandTypes[64 * 6 + i].unit);
                        diMap_[key] = item;
                    }

                    // 第四象限无功费率最大需量
                    key = (di3 + 1) << 24 | (di2 + 8) << 16 | (di1 + i) << 8 | (di0 + j);
                    if (64 * 7 + i < demandSize) {
                        DataItem item(key,
                                      namePrefix + demandTypes[64 * 7 + i].name,
                                      DataFormat::XX_XXXX,
                                      defaultValue,
                                      demandTypes[64 * 7 + i].unit);
                        diMap_[key] = item;
                    }

                    // 正向视在最大需量
                    key = (di3 + 1) << 24 | (di2 + 9) << 16 | (di1 + i) << 8 | (di0 + j);
                    if (64 * 8 + i < demandSize) {
                        DataItem item(key,
                                      namePrefix + demandTypes[64 * 8 + i].name,
                                      DataFormat::XX_XXXX,
                                      defaultValue,
                                      demandTypes[64 * 8 + i].unit);
                        diMap_[key] = item;
                    }

                    // 反向视在最大需量
                    key = (di3 + 1) << 24 | (di2 + 10) << 16 | (di1 + i) << 8 | (di0 + j);
                    if (64 * 9 + i < demandSize) {
                        DataItem item(key,
                                      namePrefix + demandTypes[64 * 9 + i].name,
                                      DataFormat::XX_XXXX,
                                      defaultValue,
                                      demandTypes[64 * 9 + i].unit);
                        diMap_[key] = item;
                    }

                    // 最后几个数据特殊处理
                    for (int k = 0; k < int(demandDiList.size()); ++k) {
                        // 提取demandDiList中的前24位，然后添加结算日信息（最后8位）
                        key = (demandDiList[k] & 0xFFFFFF00) | (di0 + j);
                        if (64 * 10 + k < demandSize) {
                            DataItem item(key,
                                          namePrefix + demandTypes[64 * 10 + k].name,
                                          DataFormat::XX_XXXX,
                                          defaultValue,
                                          demandTypes[64 * 10 + k].unit);
                            diMap_[key] = item;
                        }
                    }
                }
            }

            LOG_INFO("Demand definitions initialization completed");
        }

        // 初始化变量类型定义
        void DataItemManager::initVariablesDef() { std::lock_guard<std::mutex> lock(mutex_); }

        // 初始化电能类型定义
        void DataItemManager::initEnergyDef()
        {
            std::lock_guard<std::mutex> lock(mutex_);

            // 电能DI列表
            std::vector<uint32_t> energyDiList
                = { 0x00800000, 0x00810000, 0x00820000, 0x00830000, 0x00840000, 0x00850000, 0x00860000, 0x00150000, 0x00160000,
                    0x00170000, 0x00180000, 0x00190000, 0x001A0000, 0x001B0000, 0x001C0000, 0x001D0000, 0x001E0000, 0x00940000,
                    0x00950000, 0x00960000, 0x00970000, 0x00980000, 0x00990000, 0x009A0000, 0x00290000, 0x002A0000, 0x002B0000,
                    0x002C0000, 0x002D0000, 0x002E0000, 0x002F0000, 0x00300000, 0x00310000, 0x00320000, 0x00A80000, 0x00A90000,
                    0x00AA0000, 0x00AB0000, 0x00AC0000, 0x00AD0000, 0x00AE0000, 0x003D0000, 0x003E0000, 0x003F0000, 0x00400000,
                    0x00410000, 0x00420000, 0x00430000, 0x00440000, 0x00450000, 0x00460000, 0x00BC0000, 0x00BD0000, 0x00BE0000,
                    0x00BF0000, 0x00C00000, 0x00C10000, 0x00C20000 };

            LOG_INFO("Initializing energy definitions...");

            uint8_t di3 = 0; // 数据类型
            uint8_t di2 = 0; // 电能类型
            uint8_t di1 = 0; // 同一类型电能里的不同项
            uint8_t di0 = 0; // 结算日

            // 遍历并创建电能数据项
            for (int i = 0; i < 64; ++i) {
                for (int j = 0; j < 13; ++j) {
                    std::string namePrefix;
                    if (j == 0) {
                        namePrefix = "（当前）";
                    } else {
                        namePrefix = "（上" + std::to_string(j) + "结算日）";
                    }

                    // 数据值默认为monostate
                    std::variant<std::monostate, float, int32_t, uint32_t, std::string, Demand> defaultValue;

                    // 组合有功费率电能
                    uint32_t key = (di3 << 24) | (di2 << 16) | ((di1 + i) << 8) | (di0 + j);
                    int energySize = energyTypes.size();
                    if (i < energySize) {
                        DataItem item(
                            key, namePrefix + energyTypes[i].name, DataFormat::XXXXXX_XX, defaultValue, energyTypes[i].unit);
                        diMap_[key] = item;
                    }

                    // 正向有功费率电能
                    key = (di3 << 24) | ((di2 + 1) << 16) | ((di1 + i) << 8) | (di0 + j);
                    if (64 + i < energySize) {
                        DataItem item(key,
                                      namePrefix + energyTypes[64 + i].name,
                                      DataFormat::XXXXXX_XX,
                                      defaultValue,
                                      energyTypes[64 + i].unit);
                        diMap_[key] = item;
                    }

                    // 反向有功费率电能
                    key = (di3 << 24) | ((di2 + 2) << 16) | ((di1 + i) << 8) | (di0 + j);
                    if (64 * 2 + i < energySize) {
                        DataItem item(key,
                                      namePrefix + energyTypes[64 * 2 + i].name,
                                      DataFormat::XXXXXX_XX,
                                      defaultValue,
                                      energyTypes[64 * 2 + i].unit);
                        diMap_[key] = item;
                    }

                    // 组合无功1费率电能
                    key = (di3 << 24) | ((di2 + 3) << 16) | ((di1 + i) << 8) | (di0 + j);
                    if (64 * 3 + i < energySize) {
                        DataItem item(key,
                                      namePrefix + energyTypes[64 * 3 + i].name,
                                      DataFormat::XXXXXX_XX,
                                      defaultValue,
                                      energyTypes[64 * 3 + i].unit);
                        diMap_[key] = item;
                    }

                    // 组合无功2费率电能
                    key = (di3 << 24) | ((di2 + 4) << 16) | ((di1 + i) << 8) | (di0 + j);
                    if (64 * 4 + i < energySize) {
                        DataItem item(key,
                                      namePrefix + energyTypes[64 * 4 + i].name,
                                      DataFormat::XXXXXX_XX,
                                      defaultValue,
                                      energyTypes[64 * 4 + i].unit);
                        diMap_[key] = item;
                    }

                    // 第一象限无功电能
                    key = (di3 << 24) | ((di2 + 5) << 16) | ((di1 + i) << 8) | (di0 + j);
                    if (64 * 5 + i < energySize) {
                        DataItem item(key,
                                      namePrefix + energyTypes[64 * 5 + i].name,
                                      DataFormat::XXXXXX_XX,
                                      defaultValue,
                                      energyTypes[64 * 5 + i].unit);
                        diMap_[key] = item;
                    }

                    // 第二象限无功电能
                    key = (di3 << 24) | ((di2 + 6) << 16) | ((di1 + i) << 8) | (di0 + j);
                    if (64 * 6 + i < energySize) {
                        DataItem item(key,
                                      namePrefix + energyTypes[64 * 6 + i].name,
                                      DataFormat::XXXXXX_XX,
                                      defaultValue,
                                      energyTypes[64 * 6 + i].unit);
                        diMap_[key] = item;
                    }

                    // 第三象限无功电能
                    key = (di3 << 24) | ((di2 + 7) << 16) | ((di1 + i) << 8) | (di0 + j);
                    if (64 * 7 + i < energySize) {
                        DataItem item(key,
                                      namePrefix + energyTypes[64 * 7 + i].name,
                                      DataFormat::XXXXXX_XX,
                                      defaultValue,
                                      energyTypes[64 * 7 + i].unit);
                        diMap_[key] = item;
                    }

                    // 第四象限无功电能
                    key = (di3 << 24) | ((di2 + 8) << 16) | ((di1 + i) << 8) | (di0 + j);
                    if (64 * 8 + i < energySize) {
                        DataItem item(key,
                                      namePrefix + energyTypes[64 * 8 + i].name,
                                      DataFormat::XXXXXX_XX,
                                      defaultValue,
                                      energyTypes[64 * 8 + i].unit);
                        diMap_[key] = item;
                    }

                    // 正向视在电能
                    key = (di3 << 24) | ((di2 + 9) << 16) | ((di1 + i) << 8) | (di0 + j);
                    if (64 * 9 + i < energySize) {
                        DataItem item(key,
                                      namePrefix + energyTypes[64 * 9 + i].name,
                                      DataFormat::XXXXXX_XX,
                                      defaultValue,
                                      energyTypes[64 * 9 + i].unit);
                        diMap_[key] = item;
                    }

                    // 反向视在电能
                    key = (di3 << 24) | ((di2 + 10) << 16) | ((di1 + i) << 8) | (di0 + j);
                    if (64 * 10 + i < energySize) {
                        DataItem item(key,
                                      namePrefix + energyTypes[64 * 10 + i].name,
                                      DataFormat::XXXXXX_XX,
                                      defaultValue,
                                      energyTypes[64 * 10 + i].unit);
                        diMap_[key] = item;
                    }

                    // 最后几个数据特殊处理
                    for (int k = 0; k < int(energyDiList.size()); ++k) {
                        // 提取energyDiList中的前24位，然后添加结算日信息（最后8位）
                        key = (energyDiList[k] & 0xFFFFFF00) | (di0 + j);
                        if (64 * 11 + k < energySize) {
                            DataItem item(key,
                                          namePrefix + energyTypes[64 * 11 + k].name,
                                          DataFormat::XXXXXX_XX,
                                          defaultValue,
                                          energyTypes[64 * 11 + k].unit);
                            diMap_[key] = item;
                        }
                    }
                }
            }

            LOG_DEBUG("Energy definitions initialized");
        }

    } // namespace model
} // namespace dlt645