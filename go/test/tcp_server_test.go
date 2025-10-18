package test

import (
	"main/dlt645/service/serversvc"
	"testing"
	"time"
)

func TestTcpServerStart(t *testing.T) {
	serverSvc, err := serversvc.NewTcpServer("10.10.112.5", 10523, 5*time.Second)
	if err != nil {
		t.Fatalf("创建TCP服务器失败: %v", err)
	}
	serverSvc.SetAddress([]byte{0x00, 0x00, 0x00, 0x00, 0x00, 0x00})

	// 启动服务器
	if err := serverSvc.Server.Start(); err != nil {
		t.Fatalf("启动TCP服务器失败: %v", err)
	}
}
