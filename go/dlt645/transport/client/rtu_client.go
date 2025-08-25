package client

import (
	"errors"
	"fmt"
	"log"
	"main/dlt645/common"
	"time"

	"github.com/tarm/serial"
)

type RtuClient struct {
	Port     string
	BaudRate int
	DataBits int
	StopBits int
	Parity   serial.Parity
	Timeout  time.Duration
	conn     *serial.Port
}

func (c *RtuClient) Configure(params interface{}) error {
	if params == nil {
		return errors.New("configuration params is nil")
	}
	// 类型断言，确保 params 是 TcpClientConfig 类型
	config, ok := params.(*RtuClient)
	if !ok {
		return errors.New("invalid configuration type")
	}

	// 赋值配置参数
	c.Port = config.Port
	c.DataBits = config.DataBits
	c.StopBits = config.StopBits
	c.BaudRate = config.BaudRate
	c.Parity = config.Parity
	c.Timeout = config.Timeout
	return nil
}

func (c *RtuClient) Connect() error {
	config := &serial.Config{
		Name:        c.Port,
		Parity:      c.Parity,
		Baud:        c.BaudRate,
		Size:        byte(c.DataBits),
		StopBits:    serial.StopBits(byte(c.StopBits)),
		ReadTimeout: c.Timeout,
	}

	conn, err := serial.OpenPort(config)
	if err != nil {
		return fmt.Errorf("failed to open serial port: %w", err)
	}
	c.conn = conn

	log.Printf("Rtu client connected to port %s", c.Port)
	return nil
}

func (c *RtuClient) Disconnect() error {
	if c.conn == nil {
		return nil
	}
	err := c.conn.Close()
	if err != nil {
		return fmt.Errorf("failed to close serial port: %w", err)
	}
	c.conn = nil
	log.Printf("Rtu client disconnected from port %s", c.Port)
	return nil
}

// SendRequest 发送请求并接收响应
func (c *RtuClient) SendRequest(data []byte) ([]byte, error) {
	if c.conn == nil {
		return nil, errors.New("未连接到串口")
	}

	// 发送请求
	_, err := c.conn.Write(data)
	if err != nil {
		return nil, fmt.Errorf("发送请求失败: %v", err)
	}
	log.Printf("已发送请求: %v", common.BytesToSpacedHex(data))

	// 接收响应
	buf := make([]byte, 256)
	n, err := c.conn.Read(buf)
	if err != nil {
		return nil, fmt.Errorf("接收响应失败: %v", err)
	}
	log.Printf("已接收响应: %v", common.BytesToSpacedHex(buf[:n]))
	return buf[:n], nil
}
