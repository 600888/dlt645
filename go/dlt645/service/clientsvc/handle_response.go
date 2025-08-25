package clientsvc

import (
	"encoding/binary"
	"errors"
	"log"
	"main/dlt645/common"
	"main/dlt645/model"
	"main/dlt645/model/data"
	"main/dlt645/protocol"
	"time"
)

func (s *MeterClientService) HandleResponse(frame *protocol.Frame) (*model.DataItem, error) {
	// 验证设备地址
	if !s.validateDevice(frame.Addr) {
		log.Printf("验证设备地址: %x 失败", common.BytesToSpacedHex(frame.Addr[:]))
		return nil, errors.New("unauthorized device")
	}

	// 根据控制码判断响应类型
	switch frame.CtrlCode {
	case model.BroadcastTimeSync | 0x80: // 广播校时响应
		log.Printf("广播校时响应: % x", frame.Data)
		time := s.GetTime(frame.Data[0:4])
		dataItem, err := data.GetDataItem(common.BytesToUint32(frame.Data[0:4]))
		if err != nil {
			log.Printf("获取数据项失败: %v", err)
			return nil, err
		}
		dataItem.Value = time
		return dataItem, nil
	case model.CtrlReadData | 0x80: // 读数据响应
		// 解析数据标识
		if len(frame.Data) < 4 {
			return nil, errors.New("invalid data length for read response")
		}
		di := frame.Data[0:4]
		di3 := di[3]
		switch di3 {
		case 0x00:
			log.Printf("读取电能响应: % x", frame.Data)
			dataItem, err := data.GetDataItem(common.BytesToUint32(di))
			if err != nil {
				log.Printf("获取数据项失败: %v", err)
				return nil, err
			}
			dataItem.Value, err = common.BCDToFloat32(frame.Data[4:8], dataItem.DataFormat, binary.LittleEndian)
			if err != nil {
				log.Printf("转换BCD码到浮点数失败: %v", err)
				return nil, err
			}
			return dataItem, nil
		case 0x01:
			log.Printf("读取最大需量及发生时间响应: % x", frame.Data)
			dataItem, err := data.GetDataItem(common.BytesToUint32(di))
			if err != nil {
				log.Printf("获取数据项失败: %v", err)
				return nil, err
			}
			t, err := common.BCDToTime(frame.Data[7:12])
			if err != nil {
				log.Printf("转换时间失败: %v", err)
				return nil, err
			}
			demandValue, err := common.BCDToFloat32(frame.Data[4:7], dataItem.DataFormat, binary.LittleEndian)
			if err != nil {
				log.Printf("转换BCD码到浮点数失败: %v", err)
				return nil, err
			}
			dataItem.Value = model.Demand{
				Value:     demandValue,
				OccurTime: t,
			}
			return dataItem, nil
		case 0x02:
			dataItem, err := data.GetDataItem(common.BytesToUint32(di))
			if err != nil {
				log.Printf("获取数据项失败: %v", err)
				return nil, err
			}
			dataItem.Value, err = common.BCDToFloat32(frame.Data[4:8], dataItem.DataFormat, binary.LittleEndian)
			if err != nil {
				log.Printf("转换BCD码到浮点数失败: %v", err)
				return nil, err
			}
			return dataItem, nil
		default:
			log.Printf("<UNK> %x <UNK>", di3)
			return nil, errors.New("unknown di3 in read response")
		}
	case model.ReadAddress | 0x80: // 读通讯地址响应
		log.Printf("读通讯地址响应: %v", frame.Data)
		if len(frame.Data) == 6 {
			var address [6]byte
			copy(address[:], frame.Data)
			s.Address = address
		}
		return &model.DataItem{
			Di:         common.BytesToUint32(frame.Data[0:4]),
			Name:       "通讯地址",
			DataFormat: model.XXXXXXXXXXXX,
			Value:      frame.Data,
			Unit:       "",
			Timestamp:  time.Now().Unix(),
		}, nil
	case model.WriteAddress | 0x80: // 写通讯地址响应
		log.Printf("写通讯地址响应: %v", frame.Data)
		return &model.DataItem{
			Di:         common.BytesToUint32(frame.Data[0:4]),
			Name:       "通讯地址",
			DataFormat: model.XXXXXXXXXXXX,
			Value:      frame.Data,
			Unit:       "",
			Timestamp:  time.Now().Unix(),
		}, nil
	default:
		log.Printf("<UNK> %x <UNK>", frame.CtrlCode)
		return nil, errors.New("unknown control code for response")
	}
}
