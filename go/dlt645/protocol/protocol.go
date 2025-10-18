package protocol

import (
	"bytes"
	"errors"
	"fmt"
	"log"
)

const (
	FrameStartByte = 0x68
	FrameEndByte   = 0x16
	BroadcastAddr  = 0xAA
)

// 帧结构体（严格对应协议规范）
type Frame struct {
	Preamble  []byte  `json:"preamble"` // 添加json标签
	StartFlag byte    `json:"startFlag"`
	Addr      [6]byte `json:"addr"`
	CtrlCode  byte    `json:"ctrlCode"`
	DataLen   byte    `json:"dataLen"`
	Data      []byte  `json:"data"`
	CheckSum  byte    `json:"checkSum"`
	EndFlag   byte    `json:"endFlag"`
}

// 数据域解码（±33H转换）
func DecodeData(data []byte) []byte {
	result := make([]byte, len(data))
	for i, b := range data {
		result[i] = b - 0x33
	}
	return result
}

// 校验和计算（模256求和）
func calculateChecksum(data []byte) byte {
	var sum byte
	for _, b := range data {
		sum += b
	}
	return sum
}

// 帧构建（支持广播和单播）
func BuildFrame(addr [6]byte, ctrlCode byte, data []byte) []byte {
	buf := new(bytes.Buffer)
	buf.WriteByte(FrameStartByte)
	buf.Write(addr[:])
	buf.WriteByte(FrameStartByte)
	buf.WriteByte(ctrlCode)

	// 数据域编码
	encodedData := make([]byte, len(data))
	for i, b := range data {
		encodedData[i] = b + 0x33
	}

	buf.WriteByte(byte(len(encodedData)))
	buf.Write(encodedData)

	// 计算校验和
	checkData := buf.Bytes()
	checkSum := calculateChecksum(checkData)
	buf.WriteByte(checkSum)
	buf.WriteByte(FrameEndByte)

	// 前导字节添加
	var finalBuf bytes.Buffer
	var preamble [4]byte = [4]byte{0xFE, 0xFE, 0xFE, 0xFE}
	finalBuf.Write(preamble[:])
	finalBuf.Write(buf.Bytes())
	return finalBuf.Bytes()
}

// Deserialize 将字节切片反序列化为 Frame 结构体
func Deserialize(raw []byte) (*Frame, error) {
	// 基础校验
	if len(raw) < 12 { // 最小帧长度=起始符(1)+地址(6)+起始符(1)+控制码(1)+数据长度(1)+结束符(1)
		return nil, errors.New("frame too short")
	}

	// 帧边界检查（需考虑前导FE）
	startIdx := bytes.IndexByte(raw, FrameStartByte)
	if startIdx == -1 || startIdx+10 >= len(raw) {
		return nil, errors.New("invalid start flag")
	}
	if startIdx+7 >= len(raw) || raw[startIdx+7] != FrameStartByte { // 第二个起始符位置校验
		return nil, errors.New("missing second start flag")
	}

	// 构建帧结构
	frame := &Frame{
		StartFlag: raw[startIdx],
		Addr: [6]byte{
			raw[startIdx+1], raw[startIdx+2], raw[startIdx+3],
			raw[startIdx+4], raw[startIdx+5], raw[startIdx+6],
		},
		CtrlCode: raw[startIdx+8],
		DataLen:  raw[startIdx+9],
	}

	// 数据域提取（严格按协议1.2.5节处理）
	dataStart := startIdx + 10
	dataEnd := dataStart + int(frame.DataLen)
	if dataEnd > len(raw)-2 { // 预留校验位和结束符
		return nil, fmt.Errorf("invalid data length %d", frame.DataLen)
	}

	// 数据域解码（需处理加33H/减33H）
	frame.Data = make([]byte, frame.DataLen)
	for i := 0; i < int(frame.DataLen); i++ {
		if dataStart+i >= len(raw) {
			return nil, errors.New("data field truncated")
		}
		frame.Data[i] = raw[dataStart+i] - 0x33
	}

	// 校验和验证（从第一个68H到校验码前）
	checksumStart := startIdx
	checksumEnd := dataEnd
	if checksumEnd >= len(raw) {
		return nil, errors.New("frame truncated")
	}

	calculatedSum := byte(0)
	for i := checksumStart; i < checksumEnd; i++ {
		calculatedSum += raw[i]
	}

	if calculatedSum != raw[checksumEnd] {
		return nil, fmt.Errorf("checksum error: calc=0x%X, actual=0x%X",
			calculatedSum, raw[checksumEnd])
	}

	// 结束符验证
	if checksumEnd+1 >= len(raw) || raw[checksumEnd+1] != FrameEndByte {
		return nil, errors.New("invalid end flag")
	}

	// 转换为带缩进的JSON
	log.Printf("frame: %v", frame)
	return frame, nil
}

// Serialize 将 Frame 结构体序列化为字节切片
func (f *Frame) Serialize() ([]byte, error) {
	if f.StartFlag != FrameStartByte || f.EndFlag != FrameEndByte {
		return nil, errors.New("invalid start or end flag")
	}

	buf := new(bytes.Buffer)

	// 写入前导字节
	if len(f.Preamble) > 0 {
		buf.Write(f.Preamble)
	}

	// 写入起始符
	buf.WriteByte(f.StartFlag)

	// 写入地址
	buf.Write(f.Addr[:])

	// 写入第二个起始符
	buf.WriteByte(f.StartFlag)

	// 写入控制码
	buf.WriteByte(f.CtrlCode)

	// 数据域编码
	encodedData := make([]byte, len(f.Data))
	for i, b := range f.Data {
		encodedData[i] = b + 0x33
	}

	// 写入数据长度
	buf.WriteByte(byte(len(encodedData)))

	// 写入编码后的数据
	buf.Write(encodedData)

	// 计算并写入校验和
	checkData := buf.Bytes()
	checkSum := calculateChecksum(checkData)
	buf.WriteByte(checkSum)

	// 写入结束符
	buf.WriteByte(f.EndFlag)

	return buf.Bytes(), nil
}
