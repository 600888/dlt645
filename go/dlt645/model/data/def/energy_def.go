// 数据标识DI（完整定义）
package def

import (
	"fmt"
	"main/dlt645/model"
	dlt645type "main/dlt645/model/type"
)

var energyDiList = []uint32{
	0x00800000,
	0x00810000,
	0x00820000,
	0x00830000,
	0x00840000,
	0x00850000,
	0x00860000,
	0x00150000,
	0x00160000,
	0x00170000,
	0x00180000,
	0x00190000,
	0x001A0000,
	0x001B0000,
	0x001C0000,
	0x001D0000,
	0x001E0000,
	0x00940000,
	0x00950000,
	0x00960000,
	0x00970000,
	0x00980000,
	0x00990000,
	0x009A0000,
	0x00290000,
	0x002A0000,
	0x002B0000,
	0x002C0000,
	0x002D0000,
	0x002E0000,
	0x002F0000,
	0x00300000,
	0x00310000,
	0x00320000,
	0x00A80000,
	0x00A90000,
	0x00AA0000,
	0x00AB0000,
	0x00AC0000,
	0x00AD0000,
	0x00AE0000,
	0x003D0000,
	0x003E0000,
	0x003F0000,
	0x00400000,
	0x00410000,
	0x00420000,
	0x00430000,
	0x00440000,
	0x00450000,
	0x00460000,
	0x00BC0000,
	0x00BD0000,
	0x00BE0000,
	0x00BF0000,
	0x00C00000,
	0x00C10000,
	0x00C20000,
}

func initEnergyDef() {
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

			// 组合有功费率电能
			DIMap[uint32(di3<<24|di2<<16|(di1+i)<<8|(di0+j))] = model.DataItem{
				Name:       namePrefix + dlt645type.EnergyTypes[i].Name,
				DataFormat: model.XXXXXX_XX,
				Unit:       dlt645type.EnergyTypes[i].Unit,
			}
			// 正向有功费率电能
			DIMap[uint32(di3<<24|(di2+1)<<16|(di1+i)<<8|(di0+j))] = model.DataItem{
				Name:       namePrefix + dlt645type.EnergyTypes[64+i].Name,
				DataFormat: model.XXXXXX_XX,
				Unit:       dlt645type.EnergyTypes[64+i].Unit,
			}
			// 反向有功费率电能
			DIMap[uint32(di3<<24|(di2+2)<<16|(di1+i)<<8|(di0+j))] = model.DataItem{
				Name:       namePrefix + dlt645type.EnergyTypes[64*2+i].Name,
				DataFormat: model.XXXXXX_XX,
				Unit:       dlt645type.EnergyTypes[64*2+i].Unit,
			}
			// 组合无功1费率电能
			DIMap[uint32(di3<<24|(di2+3)<<16|(di1+i)<<8|(di0+j))] = model.DataItem{
				Name:       namePrefix + dlt645type.EnergyTypes[64*3+i].Name,
				DataFormat: model.XXXXXX_XX,
				Unit:       dlt645type.EnergyTypes[64*3+i].Unit,
			}
			// 组合无功2费率电能地址
			DIMap[uint32(di3<<24|(di2+4)<<16|(di1+i)<<8|(di0+j))] = model.DataItem{
				Name:       namePrefix + dlt645type.EnergyTypes[64*4+i].Name,
				DataFormat: model.XXXXXX_XX,
				Unit:       dlt645type.EnergyTypes[64*4+i].Unit,
			}
			// 第一象限无功电能
			DIMap[uint32(di3<<24|(di2+5)<<16|(di1+i)<<8|(di0+j))] = model.DataItem{
				Name:       namePrefix + dlt645type.EnergyTypes[64*5+i].Name,
				DataFormat: model.XXXXXX_XX,
				Unit:       dlt645type.EnergyTypes[64*5+i].Unit,
			}
			// 第二象限无功电能
			DIMap[uint32(di3<<24|(di2+6)<<16|(di1+i)<<8|(di0+j))] = model.DataItem{
				Name:       namePrefix + dlt645type.EnergyTypes[64*6+i].Name,
				DataFormat: model.XXXXXX_XX,
				Unit:       dlt645type.EnergyTypes[64*6+i].Unit,
			}
			// 第三象限无功电能
			DIMap[uint32(di3<<24|(di2+7)<<16|(di1+i)<<8|(di0+j))] = model.DataItem{
				Name:       namePrefix + dlt645type.EnergyTypes[64*7+i].Name,
				DataFormat: model.XXXXXX_XX,
				Unit:       dlt645type.EnergyTypes[64*7+i].Unit,
			}
			// 第四象限无功电能
			DIMap[uint32(di3<<24|(di2+8)<<16|(di1+i)<<8|(di0+j))] = model.DataItem{
				Name:       namePrefix + dlt645type.EnergyTypes[64*8+i].Name,
				DataFormat: model.XXXXXX_XX,
				Unit:       dlt645type.EnergyTypes[64*8+i].Unit,
			}
			// 正向视在电能
			DIMap[uint32(di3<<24|(di2+9)<<16|(di1+i)<<8|(di0+j))] = model.DataItem{
				Name:       namePrefix + dlt645type.EnergyTypes[64*9+i].Name,
				DataFormat: model.XXXXXX_XX,
				Unit:       dlt645type.EnergyTypes[64*9+i].Unit,
			}
			// 反向视在电能
			DIMap[uint32(di3<<24|(di2+10)<<16|(di1+i)<<8|(di0+j))] = model.DataItem{
				Name:       namePrefix + dlt645type.EnergyTypes[64*10+i].Name,
				DataFormat: model.XXXXXX_XX,
				Unit:       dlt645type.EnergyTypes[64*10+i].Unit,
			}

			// 最后几个数据特殊处理
			for k := 0; k < len(energyDiList); k++ {
				value := uint32(energyDiList[k]&0xFFFFFF00) | uint32(di0+j) // 提取energyDiList中的前24位，然后添加结算日信息（最后8位）
				DIMap[value] = model.DataItem{
					Name:       namePrefix + dlt645type.EnergyTypes[64*11+k].Name,
					DataFormat: model.XXXXXX_XX,
					Unit:       dlt645type.EnergyTypes[64*11+k].Unit,
				}
			}
		}
	}
}
