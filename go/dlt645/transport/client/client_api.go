package client

import "main/dlt645/model"

type Dlt645Client interface {
	Read00(di uint32) (*model.DataItem, error) // 读电能量
	Read01(di uint32) (*model.DataItem, error) // 读最大需量及发生时间
	Read02(di uint32) (*model.DataItem, error) // 读变量
	// Read03(di uint32) (*model.DataItem, error)              // 读事件记录
	Read04(di uint32) (*model.DataItem, error) // 读参变量
	// Read05(di uint32) (*model.DataItem, error)              // 读冻结
	// Read06(di uint32) (*model.DataItem, error)              // 读负荷记录
	// Write(di uint32, bytes []byte) (*model.DataItem, error) // 写数据
	ReadAddress() ([]byte, error)      // 读通信地址
	WriteAddress(address []byte) error // 写通信地址
	// TimeCalibration(dateTime []byte) error                  // 广播校时
	// Freeze(address []byte, date []byte) error               // 冻结命令
	// ChangeCommunicationRate(rate CommunicationRate) error        // 更改通信速率
	ChangePassword(oldPassword []byte, newPassword []byte) error // 修改密码
	// MaximumDemandReset() error                                   // 最大需量清零
	// MeterReset() error                                           // 电表清零
	// EventReset(di []byte) error                                  // 事件清零
}
