package test

import (
	"fmt"
	"main/dlt645/service/clientsvc"
	"testing"
	"time"
)

func TestTcpClientStart(t *testing.T) {
	clientSvc, err := clientsvc.NewTcpClient("127.0.0.1", 10521, 5*time.Second)
	if err != nil {
		t.Fatalf("创建TCP客户端失败: %v", err)
	}
	// 连接服务器
	if err := clientSvc.Conn.Connect(); err != nil {
		t.Log("连接服务器失败")
		t.Fatal(err)
	}

	address, err := clientSvc.ReadAddress()
	if err != nil {
		t.Log("读取通讯地址失败")
		t.Fatal(err)
	}
	fmt.Printf("当前通讯地址: %x\n", address.Value)

	err = clientSvc.SetAddress(address.Value.([]byte))
	if err != nil {
		t.Log("设置通讯地址失败")
		t.Fatal(err)
	}

	dataItem, err := clientSvc.Read00(0x00000000)
	if err != nil {
		t.Log("读取数据项失败")
		t.Fatal(err)
	}
	fmt.Printf("%.2f %v\n", dataItem.Value.(float32), dataItem.Unit)

	// 读取第一套时区表
	dataItem, err = clientSvc.Read04(0x04010000)
	if err != nil {
		t.Log("读取数据项失败")
		t.Fatal(err)
	}
	fmt.Printf("%v\n", dataItem.Value)
}
