package data

import (
	"errors"
	"log"
	"main/dlt645/model"
	def "main/dlt645/model/data/def"
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
	switch dataFormat {
	case model.XXXXXX_XX:
		if -799999.99 <= value.(float32) && value.(float32) <= 799999.99 {
			return true
		}
		return false
	case model.XXXX_XX:
		if -7999.99 <= value.(float32) && value.(float32) <= 7999.99 {
			return true
		}
		return false
	case model.XXX_XXX:
		if -799.999 <= value.(float32) && value.(float32) <= 799.999 {
			return true
		}
		return false
	case model.XX_XXXX:
		if -79.9999 <= value.(float32) && value.(float32) <= 79.9999 {
			return true
		}
		return false
	default:
		return true
	}
}
