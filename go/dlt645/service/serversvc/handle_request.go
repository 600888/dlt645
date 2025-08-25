package serversvc

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

// 处理读数据请求（协议与业务分离）
func (s *MeterServerService) HandleRequest(frame *protocol.Frame) ([]byte, error) {
	// 1. 验证设备
	if !s.validateDevice(frame.Addr) {
		log.Printf("验证设备地址: %v 失败", common.BytesToSpacedHex(frame.Addr[:]))
		return nil, errors.New("unauthorized device")
	}

	// 2. 根据控制码判断请求类型
	switch frame.CtrlCode {
	case model.BroadcastTimeSync: // 广播校时
		log.Printf("广播校时: % x", frame.Data)
		s.SetTime(frame.Data)
		return protocol.BuildFrame(frame.Addr, frame.CtrlCode|0x80, frame.Data), nil
	case model.CtrlReadData:
		// 解析数据标识
		di := frame.Data
		di3 := di[3]
		switch di3 {
		case 0x00: // 读取电能
			// 构建响应帧
			resData := make([]byte, 8)
			dataItem, err := data.GetDataItem(binary.LittleEndian.Uint32(frame.Data))
			if err != nil {
				return nil, err
			}
			copy(resData[:4], frame.Data[:4]) // 仅复制前4字节数据标识
			value, _ := common.InterfaceToFloat32(dataItem.Value)
			// 转换为BCD码
			bcdValue, _ := common.Float32ToBCD(value, dataItem.DataFormat, binary.LittleEndian)
			copy(resData[4:], bcdValue)
			return protocol.BuildFrame(frame.Addr, frame.CtrlCode|0x80, resData), nil
		case 0x01: //读取最大需量及发生时间
			resData := make([]byte, 12)
			dataItem, err := data.GetDataItem(binary.LittleEndian.Uint32(frame.Data))
			if err != nil {
				return nil, err
			}
			copy(resData[:], frame.Data[:4]) //返回数据标识
			value, _ := common.InterfaceToFloat32(dataItem.Value)
			// 转换为BCD码
			bcdValue, _ := common.Float32ToBCD(value, dataItem.DataFormat, binary.LittleEndian)
			copy(resData[4:7], bcdValue[:3])
			// 需量发生时间
			copy(resData[7:12], common.TimeToBCD(time.Now()))
			log.Printf("读取最大需量及发生时间: %v", resData)
			return protocol.BuildFrame(frame.Addr, frame.CtrlCode|0x80, resData), nil
		case 0x02: // 读变量
			dataItem, err := data.GetDataItem(binary.LittleEndian.Uint32(frame.Data))
			if err != nil {
				return nil, err
			}
			// 变量数据长度
			dataLen := 4
			dataLen += (len(dataItem.DataFormat) - 1) / 2 // (数据格式长度-1位小数点)/2
			// 构建响应帧
			resData := make([]byte, dataLen)
			copy(resData[:4], frame.Data[:4]) // 仅复制前4字节
			value, _ := common.InterfaceToFloat32(dataItem.Value)
			// 转换为BCD码（小端序）
			bcdValue, _ := common.Float32ToBCD(value, dataItem.DataFormat, binary.LittleEndian)
			copy(resData[4:dataLen], bcdValue)
			return protocol.BuildFrame(frame.Addr, frame.CtrlCode|0x80, resData), nil
		default:
			log.Printf("<UNK> %x <UNK>", di3)
			return nil, errors.New("unknown di3")
		}
	case model.ReadAddress:
		// 构建响应帧
		resData := make([]byte, 6)
		copy(resData[:], s.Address[:])
		return protocol.BuildFrame(s.Address, frame.CtrlCode|0x80, resData), nil
	case model.WriteAddress:
		resData := make([]byte, 0) // 写通讯地址不需要返回数据
		// 解析数据
		addr := frame.Data[:6]
		s.SetAddress(addr) //设置通讯地址
		return protocol.BuildFrame(s.Address, frame.CtrlCode|0x80, resData), nil
	default:
		log.Printf("<UNK> %x <UNK>", frame.CtrlCode)
		return nil, errors.New("unknown control code")
	}
}
