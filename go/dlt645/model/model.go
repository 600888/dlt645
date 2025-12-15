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
	XXXXXX_XX    = "XXXXXX.XX"
	XXXX_XX      = "XXXX.XX"
	XXX_XXX      = "XXX.XXX"
	XX_XXXX      = "XX.XXXX"
	YYMMDDWW     = "YYMMDDWW"   // 日年月日星期
	HHMMSS       = "HHMMSS"     // 时分秒
	YYMMDDHHMM   = "YYMMDDHHMM" // 日年月日时分
	NN           = "NN"
	NNNN         = "NNNN"
	NNNNNNNN     = "NNNNNNNN"
)

// 地址
var BroadcastAddr = [6]byte{0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA}
var BroadcastTimeAddr = [6]byte{0x99, 0x99, 0x99, 0x99, 0x99, 0x99}

const (
	AddrLength     = 6 // 地址长度
	PasswordLength = 4 //密码长度
	DataItemLength = 4 // 数据项地址长度
)

// 错误码
const (
	OtherError          = 0b0000001 // 其他错误
	RequestDataEmpty    = 0b0000010 // 无请求数据
	AuthFailed          = 0b0000100 // 认证失败
	CommRateImmutable   = 0b0001000 // 通信速率不可改变
	YearZoneNumExceeded = 0b0010000 // 年区数超出范围
	DaySlotNumExceeded  = 0b0100000 // 日区数超出范围
	RateNumExceeded     = 0b1000000 // 速率数超出范围
)

var errorMessages = map[uint32]string{
	OtherError:          "其他错误",
	RequestDataEmpty:    "无请求数据",
	AuthFailed:          "认证失败",
	CommRateImmutable:   "通信速率不可改变",
	YearZoneNumExceeded: "年区数超出范围",
	DaySlotNumExceeded:  "日区数超出范围",
	RateNumExceeded:     "速率数超出范围",
}

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
