package common

import (
	"io"
	"log"
	"os"
	"path/filepath"
)

var LogFile *os.File

func InitLogger() {
	// 1. 创建或打开日志文件（追加模式）
	logDir := "log"
	if _, err := os.Stat(logDir); os.IsNotExist(err) {
		// 递归创建目录（包括所有必要的父目录）
		err := os.MkdirAll(logDir, 0755) // 0755是常见的目录权限设置
		if err != nil {
			log.Fatal("无法创建日志目录:", err)
		}
	}

	// 2. 创建或打开日志文件（追加模式）
	LogFile, err := os.OpenFile(filepath.Join(logDir, "server.log"),
		os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0666)
	if err != nil {
		log.Fatal("无法创建日志文件:", err)
	}

	// 2. 设置日志输出到文件和控制台
	multiWriter := io.MultiWriter(os.Stdout, LogFile)
	log.SetOutput(multiWriter)

	// 3. 设置日志格式（时间+文件名+行号）
	log.SetFlags(log.LstdFlags | log.Lshortfile)
}
