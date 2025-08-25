package server

import (
	"errors"
	"fmt"
	"log"
	"main/dlt645/common"
	"main/dlt645/protocol"
	"net"
	"time"
)

type TcpServer struct {
	Service DLT645Server
	Ip      string
	Port    int
	Timeout time.Duration
	ln      net.Listener
}

func (s *TcpServer) Start() error {
	ln, err := net.Listen("tcp", fmt.Sprintf(":%d", s.Port))
	s.ln = ln
	if err != nil {
		return err // 监听初始化失败，直接返回错误
	}

	log.Printf("TCP server started on port %d", s.Port)

	for {
		// 修复：捕获并处理 Accept() 错误
		conn, err := ln.Accept()
		if err != nil {
			log.Printf("Failed to accept connection: %v", err)
			// 根据错误类型决定是否退出循环（如 listener 关闭时）
			var netErr net.Error
			if errors.As(err, &netErr) && netErr.Temporary() {
				continue // 临时错误，继续监听
			}
			return err // 非临时错误，终止监听并返回
		}

		// 正常接受连接，启动 goroutine 处理
		go s.HandleConnection(conn)
	}
}

// Stop 方法用于关闭 TCP 服务器
func (s *TcpServer) Stop() error {
	if s.ln != nil {
		log.Println("Shutting down TCP server...")
		return s.ln.Close()
	}
	return nil
}

func (s *TcpServer) HandleConnection(conn interface{}) {
	defer func(conn net.Conn) {
		err := conn.Close()
		if err != nil {
			log.Printf("Error closing connection: %v", err)
		}
	}(conn.(net.Conn))

	buf := make([]byte, 256)
	for {
		n, err := conn.(net.Conn).Read(buf)
		if err != nil {
			break
		}

		log.Printf("Received data: %v", common.BytesToSpacedHex(buf[:n]))

		// 协议解析
		frame, err := protocol.Deserialize(buf[:n])
		if err != nil {
			log.Printf("Error parsing frame: %v", err)
			continue
		}

		// 业务处理
		var resp []byte
		resp, err = s.Service.HandleRequest(frame)

		if err != nil {
			log.Printf("Error handling request: %v", err)
			continue
		}

		// 响应
		if resp != nil {
			_, err := conn.(net.Conn).Write(resp)
			if err != nil {
				log.Printf("Error writing response: %v", err)
			}
			log.Printf("Sent response: %v", common.BytesToSpacedHex(resp))
		}
	}
}
