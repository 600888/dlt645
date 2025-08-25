package client

import (
	"errors"
	"fmt"
	"log"
	"main/dlt645/common"
	"net"
	"time"
)

type TcpClient struct {
	Ip      string
	Port    int
	Timeout time.Duration
	conn    net.Conn
}

func (c *TcpClient) Configure(params interface{}) error {
	if params == nil {
		return errors.New("configuration params is nil")
	}
	// 类型断言，确保 params 是 TcpClientConfig 类型
	config, ok := params.(*TcpClient)
	if !ok {
		return errors.New("invalid configuration type")
	}

	// 赋值配置参数
	c.Ip = config.Ip
	c.Port = config.Port
	c.Timeout = config.Timeout
	return nil
}

// Connect 连接到服务器
func (c *TcpClient) Connect() error {
	address := fmt.Sprintf("%v:%d", c.Ip, c.Port)
	conn, err := net.DialTimeout("tcp", address, c.Timeout)
	if err != nil {
		return fmt.Errorf("连接服务器失败: %v", err)
	}
	c.conn = conn
	log.Printf("成功连接到服务器 %s", address)
	return nil
}

// Disconnect 断开与服务器的连接
func (c *TcpClient) Disconnect() error {
	if c.conn != nil {
		err := c.conn.Close()
		if err != nil {
			return fmt.Errorf("断开连接失败: %v", err)
		}
		log.Println("已断开与服务器的连接")
	}
	return nil
}

// SendRequest 发送请求并接收响应
func (c *TcpClient) SendRequest(data []byte) ([]byte, error) {
	if c.conn == nil {
		return nil, errors.New("未连接到服务器")
	}

	// 设置写入超时
	if err := c.conn.SetWriteDeadline(time.Now().Add(c.Timeout)); err != nil {
		return nil, fmt.Errorf("设置写入超时失败: %v", err)
	}

	// 发送请求
	_, err := c.conn.Write(data)
	if err != nil {
		return nil, fmt.Errorf("发送请求失败: %v", err)
	}
	log.Printf("已发送请求: %v", common.BytesToSpacedHex(data))

	// 设置读取超时
	if err := c.conn.SetReadDeadline(time.Now().Add(c.Timeout)); err != nil {
		return nil, fmt.Errorf("设置读取超时失败: %v", err)
	}

	// 接收响应
	buf := make([]byte, 256)
	n, err := c.conn.Read(buf)
	if err != nil {
		return nil, fmt.Errorf("接收响应失败: %v", err)
	}
	log.Printf("已接收响应: %v", common.BytesToSpacedHex(buf[:n]))
	return buf[:n], nil
}
