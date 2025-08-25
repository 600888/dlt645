package def

import (
	"main/dlt645/model"
	dlt645type "main/dlt645/model/type"
)

func initVariablesDef() {
	for _, v := range dlt645type.VariableTypes {
		DIMap[uint32(v.Di)] = model.DataItem{
			Di:         uint32(v.Di),
			Name:       v.Name,
			DataFormat: v.DataFormat,
			Value:      nil,
			Unit:       v.Unit,
		}
	}
}
