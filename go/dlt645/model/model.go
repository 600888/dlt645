package model

import "time"

// 控制码定义
const (
	BroadcastTimeSync = 0x08 // 广播校时
	CtrlReadData      = 0x11 // 读数据
	ReadAddress       = 0x13 // 读通讯地址
	CtrlWriteData     = 0x14 // 写数据
	WriteAddress      = 0x15 // 写通讯地址
	CtrlFreezeCmd     = 0x16 // 冻结命令
	ChangeBaudRate    = 0x17 //修改通信速率
	ChangePassword    = 0x18 // 改变密码
	// ...其他控制码
)

const (
	XXXXXXXXXXXX = "XXXXXXXXXXXX"
	XXXXXX_XX = "XXXXXX.XX"
	XXXX_XX   = "XXXX.XX"
	XXX_XXX   = "XXX.XXX"
	XX_XXXX   = "XX.XXXX"
)

// 数据项结构体
type DataItem struct {
	Di         uint32      // 数据项地址
	Name       string      // 数据名称
	DataFormat string      // 数据格式
	Value      interface{} // 实际值
	Unit       string      // 单位（kW/kWh等）
	Timestamp  int64       // 数据时间戳
}

// 电表设备实体
type MeterDevice struct {
	Addr       [6]byte // 电表地址
	Protocol   string  // 协议版本（2007/1997）
	BaudRate   int     // 通信波特率
	LastActive int64   // 最后活跃时间
}

// 需量
type Demand struct {
	Value     float32   // 需量值
	OccurTime time.Time // 需量发生时间
}
