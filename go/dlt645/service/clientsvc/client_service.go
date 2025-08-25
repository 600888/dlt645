package clientsvc

import (
	"encoding/binary"
	"errors"
	"log"
	"main/dlt645/common"
	"main/dlt645/model"
	"main/dlt645/protocol"
	"main/dlt645/transport/client"
	"time"

	"github.com/tarm/serial"
)

type Connection interface {
	Connect() error
	Disconnect() error
	SendRequest(frame []byte) ([]byte, error) // 发送报文并同步等待响应
}

type MeterClientService struct {
	Address  [6]byte
	Password [4]byte
	Conn     Connection
}

// NewTcpClient 创建并配置Tcp客户端，返回MeterClientService实例
// 参数：
//   - ip: 目标服务器IP地址
//   - port: 目标服务器端口
//   - timeout: 连接超时时间
//
// 返回值：
//   - MeterClientService: 业务服务接口
//   - error: 错误信息
func NewTcpClient(ip string, port int, timeout time.Duration) (*MeterClientService, error) {
	// 1. 创建TCP配置
	tcpConfig := &client.TcpClient{
		Ip:      ip,
		Port:    port,
		Timeout: timeout,
	}

	// 2. 初始化TCP客户端
	tcpClient := &client.TcpClient{}
	if err := tcpClient.Configure(tcpConfig); err != nil {
		return nil, err
	}

	// 3. 创建业务服务实例
	return NewMeterClientService(tcpClient)
}

// NewRtuClient 创建并配置Rtu客户端，返回MeterClientService实例
func NewRtuClient(port string, baudrate int, databits int, stopbits int, parity serial.Parity, timeout time.Duration) (*MeterClientService, error) {
	// 1. 创建RTU配置
	rtuConfig := &client.RtuClient{
		Port:     port,
		BaudRate: baudrate,
		DataBits: databits,
		StopBits: stopbits,
		Parity:   parity,
		Timeout:  timeout,
	}

	// 2. 初始化RTU客户端
	rtuClient := &client.RtuClient{}
	if err := rtuClient.Configure(rtuConfig); err != nil {
		return nil, err
	}

	// 3. 创建业务服务实例
	return NewMeterClientService(rtuClient)
}

// NewMeterClientService 创建新的 MeterService 实例
func NewMeterClientService(conn Connection) (*MeterClientService, error) {
	if conn == nil {
		return nil, errors.New("connection is nil")
	}

	return &MeterClientService{
		Address:  [6]byte{},
		Password: [4]byte{},
		Conn:     conn,
	}, nil
}

// 获取时间
func (s *MeterClientService) GetTime(t []byte) time.Time {
	timestamp := common.BytesToInt64(t)
	log.Printf("timestamp: %v", timestamp)
	return time.Unix(timestamp, 0)
}

// 验证设备
func (s *MeterClientService) validateDevice(addr [6]byte) bool {
	if addr == [6]byte{0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA} { // 读通讯地址命令
		return true
	}
	if addr == [6]byte{0x99, 0x99, 0x99, 0x99, 0x99, 0x99} { // 广播时间同步命令
		return true
	}
	return s.Address == addr
}

// 设置设备地址
func (s *MeterClientService) SetAddress(address []byte) error {
	if len(address) != 6 {
		return errors.New("invalid address length")
	}
	copy(s.Address[:], address)
	log.Printf("设置客户端通讯地址: %x", s.Address)
	return nil
}

// 设置设备密码
func (s *MeterClientService) SetPassword(password []byte) error {
	if len(password) != 4 {
		return errors.New("invalid password length")
	}
	copy(s.Password[:], password)
	log.Printf("设置客户端密码: %v", s.Password)
	return nil
}

// 发送请求并处理响应
func (s *MeterClientService) SendAndHandleRequest(bytes []byte) (*model.DataItem, error) {
	// 发送请求
	response, err := s.Conn.SendRequest(bytes)
	if err != nil {
		return nil, err
	}

	// 解析响应
	frame, err := protocol.Deserialize(response)
	if err != nil {
		return nil, err
	}

	// 处理响应
	dataItem, err := s.HandleResponse(frame)
	if err != nil {
		return nil, err
	}
	return dataItem, nil
}

// 读取电能
func (s *MeterClientService) Read01(di uint32) (*model.DataItem, error) {
	data := make([]byte, 4)
	binary.LittleEndian.PutUint32(data, di)
	bytes := protocol.BuildFrame(s.Address, model.CtrlReadData, data)
	// 发送请求并处理响应
	dataItem, err := s.SendAndHandleRequest(bytes)
	if err != nil {
		return nil, err
	}
	return dataItem, nil
}

// 读取最大需量及发生时间
func (s *MeterClientService) Read02(di uint32) (*model.DataItem, error) {
	data := make([]byte, 4)
	binary.LittleEndian.PutUint32(data, di)
	bytes := protocol.BuildFrame(s.Address, model.CtrlReadData, data)
	// 发送请求并处理响应
	dataItem, err := s.SendAndHandleRequest(bytes)
	if err != nil {
		return nil, err
	}
	return dataItem, nil
}

// 读取变量
func (s *MeterClientService) Read03(di uint32) (*model.DataItem, error) {
	data := make([]byte, 4)
	binary.LittleEndian.PutUint32(data, di)
	bytes := protocol.BuildFrame(s.Address, model.CtrlReadData, data)
	// 发送请求并处理响应
	dataItem, err := s.SendAndHandleRequest(bytes)
	if err != nil {
		return nil, err
	}
	return dataItem, nil
}

// 读取通讯地址
func (s *MeterClientService) ReadAddress() (*model.DataItem, error) {
	bytes := protocol.BuildFrame(s.Address, model.ReadAddress, nil)
	// 发送请求并处理响应
	dataItem, err := s.SendAndHandleRequest(bytes)
	if err != nil {
		return nil, err
	}
	return dataItem, nil
}

// 构建写通讯地址请求帧
func (s *MeterClientService) WriteAddress(newAddress [6]byte) (*model.DataItem, error) {
	bytes := protocol.BuildFrame(s.Address, model.WriteAddress, newAddress[:])
	// 发送请求并处理响应
	dataItem, err := s.SendAndHandleRequest(bytes)
	if err != nil {
		return nil, err
	}
	return dataItem, nil
}
