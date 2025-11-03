package test

import (
	"fmt"
	"main/dlt645/service/clientsvc"
	"testing"
	"time"

	"github.com/tarm/serial"
)

func TestRtuClientStart(t *testing.T) {
	clientSvc, err := clientsvc.NewRtuClient("COM10", 2400, 8, 1, serial.ParityNone, 5*time.Second)
	if err != nil {
		t.Fatalf("创建RTU客户端失败: %v", err)
	}
	clientSvc.SetAddress([]byte{0x00, 0x00, 0x00, 0x00, 0x00, 0x00})

	// 连接串口
	if err := clientSvc.Conn.Connect(); err != nil {
		t.Log("连接串口失败")
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
