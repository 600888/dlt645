package server

import (
	"errors"
	"fmt"
	"log"
	"main/dlt645/common"
	"main/dlt645/protocol"
	"net"
	"sync"
	"time"
)

type TcpServer struct {
	Service DLT645Server
	Ip      string
	Port    int
	Timeout time.Duration
	ln      net.Listener
	quit    chan struct{}
	conns   map[net.Conn]bool
	mu      sync.Mutex
}

func (s *TcpServer) Start() error {
	ln, err := net.Listen("tcp", fmt.Sprintf(":%d", s.Port))
	if err != nil {
		return err // 监听初始化失败，直接返回错误
	}

	s.ln = ln
	// 初始化退出通道和连接映射
	s.quit = make(chan struct{})
	s.conns = make(map[net.Conn]bool)

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
			// 检查是否是因为服务器停止导致的错误
			select {
			case <-s.quit:
				return nil
			default:
				return err // 非临时错误，终止监听并返回
			}
		}

		// 跟踪新连接
		s.mu.Lock()
		s.conns[conn] = true
		s.mu.Unlock()

		// 正常接受连接，启动 goroutine 处理
		go s.HandleConnection(conn)
	}
}

// Stop 方法用于关闭 TCP 服务器
func (s *TcpServer) Stop() error {
	if s.ln == nil {
		return nil
	}

	log.Println("Shutting down TCP server...")

	// 发送退出信号
	if s.quit != nil {
		close(s.quit)
	}

	// 关闭监听器
	err := s.ln.Close()
	if err != nil {
		log.Printf("Error closing listener: %v", err)
	}

	// 关闭所有已建立的连接
	s.mu.Lock()
	for conn := range s.conns {
		if conn != nil {
			connErr := conn.Close()
			if connErr != nil {
				log.Printf("Error closing connection: %v", connErr)
			}
		}
	}
	// 清空连接映射
	s.conns = nil
	s.mu.Unlock()

	log.Println("TCP server shutdown complete")
	return nil
}

func (s *TcpServer) HandleConnection(conn interface{}) {
	tcpConn := conn.(net.Conn)
	defer func() {
		// 从连接映射中移除
		s.mu.Lock()
		if s.conns != nil {
			delete(s.conns, tcpConn)
		}
		s.mu.Unlock()

		// 关闭连接
		err := tcpConn.Close()
		if err != nil {
			log.Printf("Error closing connection: %v", err)
		}
	}()

	buf := make([]byte, 256)
	for {
		// 设置连接读取超时，以便定期检查退出信号
		tcpConn.SetReadDeadline(time.Now().Add(500 * time.Millisecond))

		select {
		case <-s.quit:
			// 收到退出信号，退出循环
			log.Printf("TCP server handle connection quit signal received")
			return
		default:
			// 尝试读取数据
			n, err := tcpConn.Read(buf)
			if err != nil {
				// 检查是否是超时错误
				if netErr, ok := err.(net.Error); ok && netErr.Timeout() {
					// 超时，继续循环检查退出信号
					continue
				}
				// 其他错误，退出循环
				break
			}

			// 重置读取超时
			tcpConn.SetReadDeadline(time.Time{})

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
			}

			// 响应
			if resp != nil {
				_, err := tcpConn.Write(resp)
				if err != nil {
					log.Printf("Error writing response: %v", err)
				}
				log.Printf("Sent response: %v", common.BytesToSpacedHex(resp))
			}
		}
	}
}
