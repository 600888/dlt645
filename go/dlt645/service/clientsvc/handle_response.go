package clientsvc

import (
	"encoding/binary"
	"errors"
	"fmt"
	"log"
	"main/dlt645/common"
	"main/dlt645/model"
	"main/dlt645/model/data"
	"main/dlt645/protocol"
	"time"
)

func (s *MeterClientService) isValidResponse(frame *protocol.Frame) bool {
	// 验证响应帧是否有效
	// 检测异常处理帧 (DLT645协议中，异常响应的控制码次高位为1)
	if (frame.CtrlCode & 0x40) == 0x40 { // 检查次高位
		errorMsg := "设备返回异常响应"

		// 如果数据域不为空，尝试解析错误码
		if len(frame.Data) > 0 {
			errorCode := frame.Data[0]
			// 在Go实现中，我们简化处理，直接记录错误码
			errorMsg = fmt.Sprintf("设备返回异常响应: 错误码: %02X", errorCode)
		} else {
			errorMsg = "设备返回异常响应: 未知错误码"
		}

		log.Println(errorMsg)
		return false
	}
	return true
}

func (s *MeterClientService) HandleResponse(frame *protocol.Frame) (*model.DataItem, error) {
	// 验证响应帧是否正常
	if !s.isValidResponse(frame) {
		log.Printf("异常响应帧: % x", frame.Data)
		return nil, errors.New("invalid response frame")
	}

	// 验证设备地址
	if !s.validateDevice(frame.CtrlCode, frame.Addr) {
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
		if len(frame.Data) < model.DataItemLength {
			return nil, errors.New("invalid data length for read response")
		}
		di := frame.Data[0:model.DataItemLength]
		di3 := di[3]
		switch di3 {
		case 0x00:
			log.Printf("读取电能响应: % x", frame.Data)
			dataItem, err := data.GetDataItem(common.BytesToUint32(di))
			if err != nil {
				log.Printf("获取数据项失败: %v", err)
				return nil, err
			}
			dataItem.Value, err = common.BCDToFloat32(frame.Data[model.DataItemLength:model.DataItemLength+4], dataItem.DataFormat, binary.LittleEndian)
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
			demandValue, err := common.BCDToFloat32(frame.Data[model.DataItemLength:model.DataItemLength+3], dataItem.DataFormat, binary.LittleEndian)
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
			dataItem.Value, err = common.BCDToFloat32(frame.Data[model.DataItemLength:model.DataItemLength+4], dataItem.DataFormat, binary.LittleEndian)
			if err != nil {
				log.Printf("转换BCD码到浮点数失败: %v", err)
				return nil, err
			}
			return dataItem, nil
		case 0x04:
			log.Printf("读取参变量响应: % x", frame.Data)
			dataItem, err := data.GetDataItem(common.BytesToUint32(di))
			if err != nil {
				log.Printf("获取数据项失败: %v", err)
				return nil, err
			}

			// 时段表数据处理
			diValue := common.BytesToUint32(di)
			if diValue >= 0x04010000 && diValue <= 0x04020008 {
				step := len(dataItem.DataFormat) / 2
				// 初始化 value 为字符串切片
				stringValues := make([]string, 14)
				for i := 0; i < 14; i++ {
					// 提取BCD数据部分
					startIdx := model.DataItemLength + step*i
					endIdx := model.DataItemLength + step*(i+1)
					if endIdx > len(frame.Data) {
						break
					}
					bcdData := frame.Data[startIdx:endIdx]
					// 转换为数字，先反转字节序
					reversedBcd := common.ReverseBytes(bcdData)
					stringValues[i] = common.BcdToDigits(reversedBcd)
				}
				dataItem.Value = stringValues
			} else {
				// 非时段表数据，直接处理
				// 提取BCD数据部分
				bcdData := frame.Data[model.DataItemLength:]
				// 转换为数字，先反转字节序
				reversedBcd := common.ReverseBytes(bcdData)
				dataItem.Value = common.BcdToDigits(reversedBcd)
			}
			return dataItem, nil
		default:
			log.Printf("<UNK> %x <UNK>", di3)
			return nil, errors.New("unknown di3 in read response")
		}
	case model.ReadAddress | 0x80: // 读通讯地址响应
		log.Printf("读通讯地址响应: %v", frame.Data)
		if len(frame.Data) == model.AddrLength {
			var address [model.AddrLength]byte
			copy(address[:], frame.Data)
			s.Address = address
		}
		return &model.DataItem{
			Di:         common.BytesToUint32(frame.Data[0:model.DataItemLength]),
			Name:       "通讯地址",
			DataFormat: model.XXXXXXXXXXXX,
			Value:      frame.Data,
			Unit:       "",
			Timestamp:  time.Now().Unix(),
		}, nil
	case model.WriteAddress | 0x80: // 写通讯地址响应
		log.Printf("写通讯地址响应: %v", frame.Data)
		return &model.DataItem{
			Di:         common.BytesToUint32(frame.Data[0:model.DataItemLength]),
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
