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
	defer func(conn *serial.Port) {
		_ = s.conn.Close()
	}(s.conn)

	log.Printf("RTU server started on port %s", s.Port)

	go s.HandleConnection(s.conn)
	return nil
}

func (s *RtuServer) Stop() error {
	if s.conn != nil {
		log.Println("Shutting down RTU server...")
		return s.conn.Close()
	}
	return nil
}

func (s *RtuServer) HandleConnection(conn interface{}) {
	serialConn, ok := conn.(*serial.Port)
	if !ok {
		log.Printf("Invalid connection type: %T", conn)
	}

	defer func(conn *serial.Port) {
		err := conn.Close()
		if err != nil {
			log.Printf("Error closing connection: %v", err)
		}
	}(serialConn)

	buf := make([]byte, 256)
	for {
		n, err := serialConn.Read(buf)
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
	}
}
