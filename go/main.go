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

	serverSvc, err := serversvc.NewTcpServer("10.10.112.5", 10521, 5*time.Second)
	if err != nil {
		log.Printf("创建TCP服务器失败: %v", err)
	}
	serverSvc.SetAddress([]byte{0x50, 0x05, 0x00, 0x66, 0x16, 0x57})

	// 设置电能数据
	serverSvc.Set00(0x00000000, 123456.78)

	// 启动服务器
	if err := serverSvc.Server.Start(); err != nil {
		log.Printf("启动TCP服务器失败: %v", err)
	}
}
