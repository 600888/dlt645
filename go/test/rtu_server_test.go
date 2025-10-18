package test

import (
	"main/dlt645/service/serversvc"
	"testing"
	"time"

	"github.com/tarm/serial"
)

func TestRTUServerStart(t *testing.T) {
	serverSvc, err := serversvc.NewRtuServer("COM11", 8, 1, 9600, serial.ParityNone, 5*time.Second)
	if err != nil {
		t.Fatalf("创建RTU服务器失败: %v", err)
	}
	serverSvc.SetAddress([]byte{0x00, 0x00, 0x00, 0x00, 0x00, 0x00})

	// 启动服务器
	if err := serverSvc.Server.Start(); err != nil {
		t.Fatalf("启动RTU服务器失败: %v", err)
	}
}
