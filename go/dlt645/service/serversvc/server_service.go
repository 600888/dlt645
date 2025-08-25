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
	Address  [6]byte
	Password [4]byte
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
		Address:  [6]byte{},
		Password: [4]byte{},
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
		Address:  [6]byte{},
		Password: [4]byte{},
		Time:     time.Now(),
	}
	// 3. 将 MeterServerService 注入回 RtuServer
	rtuServer.Service = meterService
	return meterService, nil
}

// 设备注册
func (s *MeterServerService) RegisterDevice(addr [6]byte) {
	s.Address = addr
}

// 验证设备
func (s *MeterServerService) validateDevice(addr [6]byte) bool {
	if addr == [6]byte{0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA} { //读通讯地址命令
		return true
	}
	if addr == [6]byte{0x99, 0x99, 0x99, 0x99, 0x99, 0x99} { //广播时间同步命令
		return true
	}
	return s.Address == addr
}

// 写时间
func (s *MeterServerService) SetTime(t []byte) {
	timestamp := common.BytesToInt64(t)
	log.Printf("timestamp: %v", timestamp)
	// s.Time = time.Unix(timestamp, 0)
}

// 写电能量
func (s *MeterServerService) Set00(di uint32, value float32) (bool, error) {
	if value < -799999.99 || value > 799999.99 {
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
	if demand.Value < -79 || demand.Value > 79 {
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

// 写通讯地址
func (s *MeterServerService) SetAddress(address []byte) error {
	if len(address) != 6 {
		return errors.New("invalid address length")
	}
	copy(s.Address[:], address)
	log.Printf("设置通讯地址: %v", s.Address)
	return nil
}

func (s *MeterServerService) SetPassword(password []byte) error {
	if len(password) != 4 {
		return errors.New("invalid password length")
	}
	copy(s.Password[:], password)
	log.Printf("设置密码: %v", s.Password)
	return nil
}
