package test

import (
	"main/dlt645/model"
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

	// 写电能量
	serverSvc.Set00(0x00000000, 87.5)
	// 写最大需量及发生时间
	serverSvc.Set01(0x01010000, &model.Demand{Value: 50.5, OccurTime: time.Now()})
	// 写变量
	serverSvc.Set02(0x02010100, 50.5)
	// 写参变量
	serverSvc.Set04(0x04000101, "25110201") // 2025年11月2日星期一
	serverSvc.Set04(0x04000204, "10")       // 设置费率数为10

	var scheduleList = []string{"120901", "120902", "120903", "120904", "120905", "120906",
		"120907", "120908", "120909", "120910", "120911", "120912", "120913", "120914"}
	serverSvc.Set04(0x04010000, scheduleList) // 第一套时区表数据
	// 启动服务器
	if err := serverSvc.Server.Start(); err != nil {
		t.Fatalf("启动RTU服务器失败: %v", err)
	}
}
