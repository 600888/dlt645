package def

import (
	"fmt"
	"main/dlt645/model"
	dlt645type "main/dlt645/model/type"
)

var demandDiList = []uint32{
	0x01150000,
	0x01160000,
	0x01170000,
	0x01180000,
	0x01190000,
	0x011A0000,
	0x011B0000,
	0x011C0000,
	0x011D0000,
	0x011E0000,
	0x01290000,
	0x012A0000,
	0x012B0000,
	0x012C0000,
	0x012D0000,
	0x012E0000,
	0x012F0000,
	0x01300000,
	0x01310000,
	0x01320000,
	0x013D0000,
	0x013E0000,
	0x013F0000,
	0x01400000,
	0x01410000,
	0x01420000,
	0x01430000,
	0x01440000,
	0x01450000,
	0x01460000,
}

func initDemandDef() {
	di3 := 0 //数据类型
	di2 := 0 //电能类型
	di1 := 0 //同一类型电能里的不同项
	di0 := 0 //结算日

	for i := 0; i < 64; i++ {
		for j := 0; j < 13; j++ {
			var namePrefix string
			if j == 0 {
				namePrefix = "（当前）"
			} else {
				namePrefix = fmt.Sprintf("（上%d结算日）", j)
			}

			// 正向有功需量
			DIMap[uint32((di3+1)<<24|(di2+1)<<16|(di1+i)<<8|(di0+j))] = model.DataItem{
				Name:       namePrefix + dlt645type.DemandTypes[i].Name,
				DataFormat: model.XX_XXXX,
				Unit:       dlt645type.DemandTypes[i].Unit,
			}
			// 反向有功需量
			DIMap[uint32((di3+1)<<24|(di2+2)<<16|(di1+i)<<8|(di0+j))] = model.DataItem{
				Name:       namePrefix + dlt645type.DemandTypes[64+i].Name,
				DataFormat: model.XX_XXXX,
				Unit:       dlt645type.DemandTypes[64+i].Unit,
			}
			// 组合无功1需量
			DIMap[uint32((di3+1)<<24|(di2+3)<<16|(di1+i)<<8|(di0+j))] = model.DataItem{
				Name:       namePrefix + dlt645type.DemandTypes[64*2+i].Name,
				DataFormat: model.XX_XXXX,
				Unit:       dlt645type.DemandTypes[64*2+i].Unit,
			}
			// 组合无功2需量
			DIMap[uint32((di3+1)<<24|(di2+4)<<16|(di1+i)<<8|(di0+j))] = model.DataItem{
				Name:       namePrefix + dlt645type.DemandTypes[64*3+i].Name,
				DataFormat: model.XX_XXXX,
				Unit:       dlt645type.DemandTypes[64*3+i].Unit,
			}
			// 第一象限无功费率最大需量
			DIMap[uint32((di3+1)<<24|(di2+5)<<16|(di1+i)<<8|(di0+j))] = model.DataItem{
				Name:       namePrefix + dlt645type.DemandTypes[64*4+i].Name,
				DataFormat: model.XX_XXXX,
				Unit:       dlt645type.DemandTypes[64*4+i].Unit,
			}
			// 第二象限无功费率最大需量
			DIMap[uint32((di3+1)<<24|(di2+6)<<16|(di1+i)<<8|(di0+j))] = model.DataItem{
				Name:       namePrefix + dlt645type.DemandTypes[64*5+i].Name,
				DataFormat: model.XX_XXXX,
				Unit:       dlt645type.DemandTypes[64*5+i].Unit,
			}
			// 第三象限无功费率最大需量
			DIMap[uint32((di3+1)<<24|(di2+7)<<16|(di1+i)<<8|(di0+j))] = model.DataItem{
				Name:       namePrefix + dlt645type.DemandTypes[64*6+i].Name,
				DataFormat: model.XX_XXXX,
				Unit:       dlt645type.DemandTypes[64*6+i].Unit,
			}
			// 第四象限无功费率最大需量
			DIMap[uint32((di3+1)<<24|(di2+8)<<16|(di1+i)<<8|(di0+j))] = model.DataItem{
				Name:       namePrefix + dlt645type.DemandTypes[64*7+i].Name,
				DataFormat: model.XX_XXXX,
				Unit:       dlt645type.DemandTypes[64*7+i].Unit,
			}
			// 正向视在最大需量
			DIMap[uint32((di3+1)<<24|(di2+9)<<16|(di1+i)<<8|(di0+j))] = model.DataItem{
				Name:       namePrefix + dlt645type.DemandTypes[64*8+i].Name,
				DataFormat: model.XX_XXXX,
				Unit:       dlt645type.DemandTypes[64*8+i].Unit,
			}
			// 反向视在最大需量
			DIMap[uint32((di3+1)<<24|(di2+10)<<16|(di1+i)<<8|(di0+j))] = model.DataItem{
				Name:       namePrefix + dlt645type.DemandTypes[64*9+i].Name,
				DataFormat: model.XX_XXXX,
				Unit:       dlt645type.DemandTypes[64*9+i].Unit,
			}

			// 最后几个数据特殊处理
			for k := 0; k < len(demandDiList); k++ {
				value := uint32(demandDiList[k]&0xFFFFFF00) | uint32(di0+j) // 提取demandDiList中的前24位，然后添加结算日信息（最后8位）
				DIMap[value] = model.DataItem{
					Name:       namePrefix + dlt645type.DemandTypes[64*10+k].Name,
					DataFormat: model.XX_XXXX,
					Unit:       dlt645type.DemandTypes[64*10+k].Unit,
				}
			}
		}
	}
}
