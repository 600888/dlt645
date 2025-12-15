package server

import (
	"fmt"
	"log"
	"main/dlt645/common"
	"main/dlt645/protocol"
	"time"

	"github.com/tarm/serial"
)

type RtuServer struct {
	Port     string
	DataBits int
	StopBits int
	BaudRate int
	Parity   serial.Parity
	Timeout  time.Duration
	Service  DLT645Server
	conn     *serial.Port
	quit     chan struct{}
}

func (s *RtuServer) Start() error {
	config := &serial.Config{
		Name:        s.Port,
		Parity:      s.Parity,
		Baud:        s.BaudRate,
		Size:        byte(s.DataBits),
		StopBits:    serial.StopBits(byte(s.StopBits)),
		ReadTimeout: s.Timeout,
	}

	conn, err := serial.OpenPort(config)
	s.conn = conn
	if err != nil {
		return fmt.Errorf("failed to open serial port: %w", err)
	}

	// 初始化退出通道
	s.quit = make(chan struct{})

	log.Printf("RTU server started on port %s", s.Port)

	// 启动连接处理goroutine
	go s.HandleConnection(s.conn)

	// 阻塞等待退出信号
	<-s.quit
	return nil
}

func (s *RtuServer) Stop() error {
	if s.conn != nil {
		log.Println("Shutting down RTU server...")
		// 发送退出信号
		if s.quit != nil {
			close(s.quit)
		}
		// 关闭连接
		err := s.conn.Close()
		return err
	}
	return nil
}

func (s *RtuServer) HandleConnection(conn interface{}) {
	serialConn, ok := conn.(*serial.Port)
	if !ok {
		log.Printf("Invalid connection type: %T", conn)
		return
	}

	defer func(conn *serial.Port) {
		err := conn.Close()
		if err != nil {
			log.Printf("Error closing connection: %v", err)
		}
	}(serialConn)

	buf := make([]byte, 256)
	for {
		// 创建一个带有超时的读取操作，以便定期检查退出信号
		readDone := make(chan error, 1)
		var n int
		go func() {
			var readErr error
			n, readErr = serialConn.Read(buf)
			readDone <- readErr
		}()

		select {
		case err := <-readDone:
			if err != nil {
				break
			}

			if n == 0 {
				continue
			}

			log.Printf("Received data: %v", common.BytesToSpacedHex(buf[:n]))

			// 协议解析
			frame, err := protocol.Deserialize(buf[:n])
			if err != nil {
				log.Printf("Error parsing frame: %v", err)
				continue
			}

			// 业务处理
			resp, err := s.Service.HandleRequest(frame)
			if err != nil {
				log.Printf("Error handling request: %v", err)
				continue
			}

			// 响应
			if resp != nil {
				_, err := serialConn.Write(resp)
				if err != nil {
					log.Printf("Error writing response: %v", err)
					continue
				}
				log.Printf("Sent response: %v", common.BytesToSpacedHex(resp))
			}
		case <-s.quit:
			// 收到退出信号，退出循环
			log.Printf("RTU server handle connection quit signal received")
			return
		}
	}
}
