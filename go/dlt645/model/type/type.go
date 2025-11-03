package dlt645type

import (
	"encoding/json"
	"fmt"
	"log"
	"main/dlt645/common"
	"os"
	"strconv"
)

type DICategory uint32

const (
	CategoryEnergy    DICategory = 0 // 电能
	CategoryDemand    DICategory = 1 // 需量
	CategoryVariable  DICategory = 2 // 变量
	CategoryEvent     DICategory = 3 // 事件记录
	CategoryParameter DICategory = 4 // 参变量
	CategoryFreeze    DICategory = 5 // 冻结量
	CategoryLoad      DICategory = 6 // 负荷纪录
)

type Uint32FromString uint32

func (u *Uint32FromString) UnmarshalJSON(data []byte) error {
	var s string
	if err := json.Unmarshal(data, &s); err != nil {
		return err
	}
	num, err := strconv.ParseUint(s, 16, 32)
	if err != nil {
		return fmt.Errorf("无法转换为uint32: %v", err)
	}
	*u = Uint32FromString(num)
	return nil
}

type DataType struct {
	Di         Uint32FromString
	Name       string
	Unit       string
	DataFormat string
}

var EnergyTypes = []DataType{}
var DemandTypes = []DataType{}
var VariableTypes = []DataType{}
var ParameterTypes = []DataType{}

func initDataTypeFromJson(filePath string) []DataType {
	// 1. 读取 JSON 文件
	jsonData, err := os.ReadFile(filePath)
	if err != nil {
		log.Fatalf("读取文件失败: %v", err)
	}

	var dataTypes []DataType
	// 2. 解析 JSON 到切片
	if err := json.Unmarshal(jsonData, &dataTypes); err != nil {
		log.Fatalf("解析 JSON 失败: %v", err)
	}

	log.Printf("初始化 %s 完成，共加载 %d 种数据类型\n", filePath, len(dataTypes))
	return dataTypes
}

func init() {
	// 读取config下的json文件
	EnergyTypes = initDataTypeFromJson(common.GetProjectRoot() + "/config/energy_types.json")
	DemandTypes = initDataTypeFromJson(common.GetProjectRoot() + "/config/demand_types.json")
	VariableTypes = initDataTypeFromJson(common.GetProjectRoot() + "/config/variable_types.json")
	ParameterTypes = initDataTypeFromJson(common.GetProjectRoot() + "/config/parameter_types.json")
}
