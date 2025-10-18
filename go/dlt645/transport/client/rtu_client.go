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
	// 类型断言，确保 params 是 RtuClient 类型的指针
	config, ok := params.(*RtuClient)
	if !ok {
		return errors.New("invalid configuration type, expected *RtuClient")
	}

	// 赋值配置参数
	c.Port = config.Port
	c.DataBits = config.DataBits
	c.StopBits = config.StopBits
	c.BaudRate = config.BaudRate
	c.Parity = config.Parity
	c.Timeout = config.Timeout
	log.Printf("RTU客户端配置成功: 端口=%s, 波特率=%d, 数据位=%d, 停止位=%d, 校验=%v, 超时=%v",
		c.Port, c.BaudRate, c.DataBits, c.StopBits, c.Parity, c.Timeout)
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
	written, err := c.conn.Write(data)
	if err != nil {
		return nil, fmt.Errorf("发送请求失败: %v", err)
	}
	log.Printf("已发送请求: %v (%d bytes)", common.BytesToSpacedHex(data), written)

	// 使用动态缓冲区接收完整的响应帧
	var response []byte
	buf := make([]byte, 256)
	startTime := time.Now()
	found := false

	// 循环读取直到找到完整的帧或超时
	for time.Since(startTime) < c.Timeout && !found {
		n, err := c.conn.Read(buf)
		if err != nil {
			// 如果是超时但已经读取了部分数据，继续等待
			if n > 0 && time.Since(startTime) < c.Timeout {
				log.Printf("部分读取: %v (%d bytes)", common.BytesToSpacedHex(buf[:n]), n)
				response = append(response, buf[:n]...)
				continue
			}
			return nil, fmt.Errorf("接收响应失败: %v", err)
		}

		if n > 0 {
			response = append(response, buf[:n]...)
			log.Printf("读取数据: %v (%d bytes)", common.BytesToSpacedHex(buf[:n]), n)

			// 检查是否是有效的DLT645帧
			if len(response) >= 11 { // 最小帧长度
				// 检查帧结束标记 (DLT645协议通常以0x16结尾)
				for i := range response {
					if i >= 10 && response[i] == 0x16 {
						// 检查是否有足够的数据构成完整帧
						if i+1 >= 11 {
							found = true
							break
						}
					}
				}
			}
		}
	}

	if !found && len(response) == 0 {
		return nil, errors.New("未接收到任何响应数据")
	}

	log.Printf("已接收完整响应: %v (%d bytes)", common.BytesToSpacedHex(response), len(response))
	return response, nil
}
