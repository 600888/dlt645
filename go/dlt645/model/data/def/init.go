package def

import "main/dlt645/model"

var DIMap = make(map[uint32]model.DataItem)

func init() {
	initEnergyDef()
	initDemandDef()
	initVariablesDef()
}
