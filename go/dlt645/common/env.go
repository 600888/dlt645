package common

import (
	"os"
	"path/filepath"
	"runtime"
	"strings"
)

func GetProjectRoot() string {
	// 优先通过 Caller 获取路径（兼容 go run 和 go build）
	_, filename, _, _ := runtime.Caller(0)
	projectRoot := filepath.Dir(filepath.Dir(filepath.Dir(filename)))

	// 检查是否为临时目录（如 go run 模式）
	if strings.Contains(projectRoot, os.TempDir()) {
		// 回退到基于工作目录的路径
		wd, _ := os.Getwd()
		return wd
	}
	return projectRoot
}
