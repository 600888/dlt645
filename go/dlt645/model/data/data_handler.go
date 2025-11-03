package data

import (
	"errors"
	"log"
	"main/dlt645/model"
	def "main/dlt645/model/data/def"
	"reflect"
)

func GetDataItem(di uint32) (*model.DataItem, error) {
	dataItem, exists := def.DIMap[di]
	if !exists {
		log.Printf("未通过di3 %x 找到映射", di)
		return nil, errors.New("di not found")
	}
	return &dataItem, nil
}

func SetDataItem(di uint32, data interface{}) (bool, error) {
	if data == nil {
		log.Printf("data is nil")
		return false, errors.New("data is nil")
	}
	if item, exists := def.DIMap[di]; exists {
		item.Value = data
		def.DIMap[di] = item
		log.Printf("设置数据项 %x 成功, 值 %v", di, item)
		return true, nil
	}
	return false, errors.New("di not found")
}

func IsValueValid(dataFormat string, value interface{}) bool {
	// 检查值类型
	switch v := value.(type) {
	case float32, float64:
		// 转换为float64进行比较
		var floatVal float64
		if val, ok := v.(float32); ok {
			floatVal = float64(val)
		} else {
			floatVal = v.(float64)
		}

		// 根据数据格式进行范围验证
		switch dataFormat {
		case model.XXXXXX_XX:
			return -799999.99 <= floatVal && floatVal <= 799999.99
		case model.XXXX_XX:
			return -7999.99 <= floatVal && floatVal <= 7999.99
		case model.XXX_XXX:
			return -799.999 <= floatVal && floatVal <= 799.999
		case model.XX_XXXX:
			return -79.9999 <= floatVal && floatVal <= 79.9999
		default:
			return true
		}
	case string:
		// 对于字符串类型，验证长度是否与数据格式一致
		return len(v) == len(dataFormat)
	default:
		// 使用反射检查是否为数组或切片类型
		val := reflect.ValueOf(v)
		if val.Kind() == reflect.Slice || val.Kind() == reflect.Array {
			// 对于任何数组或切片类型，验证每一项数据是否合法
			for i := 0; i < val.Len(); i++ {
				if !IsValueValid(dataFormat, val.Index(i).Interface()) {
					return false
				}
			}
			return true
		}
		// 其他类型默认返回false
		return false
	}
}
