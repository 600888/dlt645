package main

import (
	"log"
	"main/dlt645/common"
	"main/dlt645/service/serversvc"
	"time"
)

func main() {
	common.InitLogger()
	defer common.LogFile.Close()
	log.Println("start server")

	serverSvc, err := serversvc.NewTcpServer("127.0.0.1", 10521, 5*time.Second)
	if err != nil {
		log.Printf("创建TCP服务器失败: %v", err)
	}
	//serverSvc, err := serversvc.NewRtuServer("COM11", 8, 1, 2400, serial.ParityEven, 1000)
	//if err != nil {
	//	log.Printf("创建RTU服务器失败: %v", err)
	//}
	err = serverSvc.SetAddress([]byte{0x00, 0x00, 0x00, 0x00, 0x00, 0x00})
	if err != nil {
		log.Printf("设置通讯地址失败: %v", err)
		return
	}

	// 设置电能数据
	_, err = serverSvc.Set00(0x00000000, 123456.78)
	if err != nil {
		log.Printf("设置电能数据失败: %v", err)
		return
	}

	// 启动服务器
	if err := serverSvc.Server.Start(); err != nil {
		log.Printf("启动TCP服务器失败: %v", err)
	}
}
