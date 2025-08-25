package test

import (
	"fmt"
	"main/dlt645/service/clientsvc"
	"testing"
	"time"
)

func TestTcpClientStart(t *testing.T) {
	clientSvc, err := clientsvc.NewTcpClient("10.10.112.5", 10521, 5*time.Second)
	if err != nil {
		t.Fatalf("创建TCP客户端失败: %v", err)
	}
	clientSvc.SetAddress([]byte{0x50, 0x05, 0x00, 0x66, 0x16, 0x57})

	// 连接服务器
	if err := clientSvc.Conn.Connect(); err != nil {
		t.Log("连接服务器失败")
		t.Fatal(err)
	}

	dataItem, err := clientSvc.Read01(0x00000000)
	if err != nil {
		t.Log("读取数据项失败")
		t.Fatal(err)
	}
	fmt.Printf("%.2f %v\n", dataItem.Value.(float32), dataItem.Unit)
}
