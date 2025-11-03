package def

import (
	"main/dlt645/model"
	dlt645type "main/dlt645/model/type"
)

func padWithZeros(length int) string {
	pad := ""
	for i := 0; i < length; i++ {
		pad += "0"
	}
	return pad
}

func initParaMeterDef() {
	for _, v := range dlt645type.ParameterTypes {
		var value interface{}
		if v.Di >= 0x04010000 && v.Di <= 0x04020008 {
			var scheduleList []string
			for i := 0; i < 14; i++ {
				scheduleList = append(scheduleList, padWithZeros(len(v.DataFormat)))
			}
			value = scheduleList
		} else {
			value = padWithZeros(len(v.DataFormat))
		}
		DIMap[uint32(v.Di)] = model.DataItem{
			Di:         uint32(v.Di),
			Name:       v.Name,
			DataFormat: v.DataFormat,
			Value:      value,
			Unit:       v.Unit,
		}
	}
}
