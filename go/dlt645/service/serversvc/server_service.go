package serversvc

import (
	"errors"
	"log"
	"main/dlt645/common"
	"main/dlt645/model"
	"main/dlt645/model/data"
	"main/dlt645/transport/server"
	"time"

	"github.com/tarm/serial"
)

type Server interface {
	Start() error
	Stop() error
	HandleConnection(interface{})
}

type MeterServerService struct {
	Address  [model.AddrLength]byte
	Password [model.PasswordLength]byte
	Time     time.Time
	Server   Server
}

// NewTcpServer 创建新的TcpServer实例
func NewTcpServer(ip string, port int, timeout time.Duration) (*MeterServerService, error) {
	// 1. 先创建 TcpServer（不依赖 Service）
	tcpServer := &server.TcpServer{
		Ip:      ip,
		Port:    port,
		Timeout: timeout,
	}

	// 2. 创建 MeterServerService，注入 TcpServer（作为 Server 接口）
	meterService := &MeterServerService{
		Server:   tcpServer, // TcpServer 已实现 Server 接口
		Address:  [model.AddrLength]byte{},
		Password: [model.PasswordLength]byte{},
		Time:     time.Now(),
	}

	// 3. 将 MeterServerService 注入回 TcpServer
	tcpServer.Service = meterService
	return meterService, nil
}

// NewRtuServer 创建新的RtuServer实例
func NewRtuServer(port string, dataBits int, stopBits int, baudRate int, parity serial.Parity,
	timeout time.Duration) (*MeterServerService, error) {
	rtuServer := &server.RtuServer{
		Port:     port,
		DataBits: dataBits,
		StopBits: stopBits,
		BaudRate: baudRate,
		Parity:   parity,
		Timeout:  timeout,
	}
	// 2. 创建 MeterServerService，注入 RtuServer（作为 Server 接口）
	meterService := &MeterServerService{
		Server:   rtuServer, // RtuServer 已实现 Server 接口
		Address:  [model.AddrLength]byte{},
		Password: [model.PasswordLength]byte{},
		Time:     time.Now(),
	}
	// 3. 将 MeterServerService 注入回 RtuServer
	rtuServer.Service = meterService
	return meterService, nil
}

// 设备注册
func (s *MeterServerService) RegisterDevice(addr [model.AddrLength]byte) {
	s.Address = addr
}

// 验证设备
func (s *MeterServerService) validateDevice(ctrlCode byte, addr [model.AddrLength]byte) bool {
	if ctrlCode == model.ReadAddress|0x80 || ctrlCode == model.WriteAddress|0x80 { // 读通讯地址命令
		return true
	}
	if addr == model.BroadcastAddr || addr == model.BroadcastTimeAddr { // 写通讯地址命令
		return true
	}
	return s.Address == addr
}

// 写时间
func (s *MeterServerService) SetTime(t []byte) {
	timestamp := common.BytesToInt64(t)
	log.Printf("timestamp: %v", timestamp)
	s.Time = time.Unix(timestamp, 0)
}

// 写电能量
func (s *MeterServerService) Set00(di uint32, value float32) (bool, error) {
	dataItem, err := data.GetDataItem(di)
	if err != nil {
		log.Printf("获取数据项失败 %v", err.Error())
		return false, err
	}

	if !data.IsValueValid(dataItem.DataFormat, value) {
		log.Printf("写电能量失败, 数据项 %x, 值 %v", di, value)
		return false, errors.New("value out of range")
	}
	ok, err := data.SetDataItem(di, value)
	if err != nil {
		log.Printf("写电能量失败 %v", err.Error())
		return false, err
	}
	return ok, nil
}

// 写最大需量及发生时间
func (s *MeterServerService) Set01(di uint32, demand *model.Demand) (bool, error) {
	dataItem, err := data.GetDataItem(di)
	if err != nil {
		log.Printf("获取数据项失败 %v", err.Error())
		return false, err
	}

	if !data.IsValueValid(dataItem.DataFormat, demand.Value) {
		log.Printf("写最大需量及发生时间失败, 数据项 %x, 值 %v", di, demand.Value)
		return false, errors.New("value out of range")
	}
	ok, err := data.SetDataItem(di, demand)
	if err != nil {
		return false, err
	}
	return ok, nil
}

// 写变量
func (s *MeterServerService) Set02(di uint32, value float32) (bool, error) {
	dataItem, err := data.GetDataItem(di)
	if err != nil {
		log.Printf("获取数据项失败 %v", err.Error())
		return false, err
	}

	if !data.IsValueValid(dataItem.DataFormat, value) {
		log.Printf("写变量失败, 数据项 %x, 值 %v", di, value)
		return false, errors.New("value out of range")
	}

	ok, err := data.SetDataItem(di, value)
	if err != nil {
		log.Printf("写变量失败 %v", err.Error())
		return false, err
	}
	return ok, nil
}

// 写参变量
func (s *MeterServerService) Set04(di uint32, value interface{}) (bool, error) {
	dataItem, err := data.GetDataItem(di)
	if err != nil {
		log.Printf("获取数据项失败 %v", err.Error())
		return false, err
	}

	// 检查值是否符合数据项的格式
	if !data.IsValueValid(dataItem.DataFormat, value) {
		log.Printf("写参变量失败, 数据项 %x, 值 %v 类型错误或超出范围", di, value)
		return false, errors.New("value type error or out of range")
	}

	ok, err := data.SetDataItem(di, value)
	if err != nil {
		log.Printf("写参变量失败 %v", err.Error())
		return false, err
	}
	return ok, nil
}

// 写通讯地址
func (s *MeterServerService) SetAddress(address []byte) error {
	if len(address) != model.AddrLength {
		return errors.New("invalid address length")
	}
	copy(s.Address[:], address)
	log.Printf("设置通讯地址: %v", s.Address)
	return nil
}

func (s *MeterServerService) SetPassword(password []byte) error {
	if len(password) != model.PasswordLength {
		return errors.New("invalid password length")
	}
	copy(s.Password[:], password)
	log.Printf("设置密码: %v", s.Password)
	return nil
}
