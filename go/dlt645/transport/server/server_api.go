package server

import (
	"main/dlt645/model"
	"main/dlt645/protocol"
)

type DLT645Server interface {
	HandleRequest(frame *protocol.Frame) ([]byte, error) // 处理请求
	Set00(di uint32, value float32) (bool, error)        // 写电能量
	Set01(di uint32, value *model.Demand) (bool, error)  // 写最大需量及发生时间
	Set02(di uint32, value float32) (bool, error)        // 写变量
	// Set03(di uint32, value uint32) (bool, error)       // 写事件记录
	Set04(di uint32, value interface{}) (bool, error) // 写参变量
	// Set05(di uint32) (bool, error)                        // 写冻结
	// Set06(di uint32) (bool, error)                        // 写负荷记录
	// Set(di uint32, bytes []byte) (*model.DataItem, error) // 写数据
	SetAddress(address []byte) error // 写通信地址
	// TimeCalibration(dateTime []byte) error // 广播校时
	// SetFreeze(address []byte, date []byte) error          // 冻结命令
	// ChangeCommunicationRate(rate CommunicationRate) error        // 更改通信速率
	// ChangePassword(oldPassword []byte, newPassword []byte) error // 修改密码
	// MaximumDemandReset() error                                   // 最大需量清零
	// MeterReset() error                                           // 电表清零
	// EventReset(di []byte) error                                  // 事件清零
}
