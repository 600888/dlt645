package common

import (
	"encoding/binary"
	"fmt"
	"log"
	"math"
	"strconv"
	"strings"
	"time"
)

// BytesToInt64 将字节数组转换为有符号 64 位整数
func BytesToInt64(bytes []byte) int64 {
	if len(bytes) < 8 {
		// 补零操作
		padded := make([]byte, 8)
		copy(padded, bytes)
		bytes = padded
	}
	return int64(binary.LittleEndian.Uint64(bytes))
}

// BytesToUint32 将字节数组转换为无符号 32 位整数
func BytesToUint32(bytes []byte) uint32 {
	if len(bytes) < 4 {
		// 补零操作
		padded := make([]byte, 4)
		copy(padded, bytes)
		bytes = padded
	}
	return binary.LittleEndian.Uint32(bytes)
}

// BytesToFloat32 将字节数组转换为浮点数
func BytesToFloat32(bytes []byte) float32 {
	if len(bytes) < 4 {
		// 补零操作
		padded := make([]byte, 4)
		copy(padded, bytes)
		bytes = padded
	}
	return math.Float32frombits(binary.LittleEndian.Uint32(bytes))
}

func ReverseBytes(src []byte) []byte {
	dst := make([]byte, len(src))
	for i := range src {
		dst[len(src)-1-i] = src[i]
	}
	return dst
}

func Uint8ToBCD(value uint8) byte {
	digit1 := value / 10
	digit2 := value % 10
	return byte(digit1<<4 | digit2)
}

// BcdToDigits 将 BCD 码字节数组转换为数字字符串
func BcdToDigits(bcd []byte) string {
	digits := make([]byte, 0, len(bcd)*2)
	for _, b := range bcd {
		high := (b >> 4) & 0x0F
		low := b & 0x0F
		digits = append(digits, byte(high+'0'))
		digits = append(digits, byte(low+'0'))
	}
	return string(digits)
}

// Float32ToBCD 将float32数值转换为BCD码字节数组，支持不同数据格式和字节序
func Float32ToBCD(value float32, format string, endian binary.ByteOrder) ([]byte, error) {
	// 判断正负
	isNegative := value < 0
	absValue := math.Abs(float64(value))

	// 解析格式获取小数位数和总长度
	decimalPlaces, _, err := parseFormat(format)
	if err != nil {
		return nil, err
	}
	// 去除小数点后的格式字符串
	formatWithoutDot := strings.ReplaceAll(format, ".", "")
	totalLength := len(formatWithoutDot)

	// 四舍五入并格式化为字符串
	rounded := roundFloat(float32(absValue), decimalPlaces)
	strValue := formatFloat(rounded, decimalPlaces, 0) // 不需要总长度参数

	// 分离整数部分和小数部分
	parts := strings.Split(strValue, ".")
	integerPart := parts[0]
	decimalPart := ""
	if len(parts) > 1 {
		decimalPart = parts[1]
	}

	// 计算整数部分和小数部分需要的长度
	intLength := totalLength - decimalPlaces

	// 整数部分往前补 0
	if len(integerPart) < intLength {
		integerPart = strings.Repeat("0", intLength-len(integerPart)) + integerPart
	}

	// 小数部分往后补 0
	if len(decimalPart) < decimalPlaces {
		decimalPart += strings.Repeat("0", decimalPlaces-len(decimalPart))
	}

	// 合并整数部分和小数部分并移除小数点
	digits := integerPart + decimalPart

	// 转换为BCD码
	bcd, err := StringToBCD(digits, endian)
	if err != nil {
		return nil, err
	}

	// 设置符号位
	if isNegative {
		if len(bcd) > 0 {
			if endian == binary.BigEndian {
				bcd[0] |= 0x80 // 大端序设置第一个字节的最高位
			} else {
				bcd[len(bcd)-1] |= 0x80 // 小端序设置最后一个字节的最高位
			}
		}
	}
	return bcd, nil
}

// BCDToFloat32 将BCD码字节数组转换为float32数值，支持不同字节序
func BCDToFloat32(bcd []byte, format string, endian binary.ByteOrder) (float32, error) {
	// 检查符号位
	isNegative := false
	if len(bcd) > 0 {
		if endian == binary.BigEndian {
			isNegative = (bcd[0] & 0x80) != 0
			bcd[0] &= 0x7F // 清除符号位
		} else {
			isNegative = (bcd[len(bcd)-1] & 0x80) != 0
			bcd[len(bcd)-1] &= 0x7F // 清除符号位
		}
	}

	// 根据字节序调整BCD码顺序, 默认转换成大端序处理
	if endian == binary.LittleEndian {
		bcdCopy := make([]byte, len(bcd))
		copy(bcdCopy, bcd)
		for i, j := 0, len(bcdCopy)-1; i < j; i, j = i+1, j-1 {
			bcdCopy[i], bcdCopy[j] = bcdCopy[j], bcdCopy[i]
		}
		bcd = bcdCopy
	}

	// 转换为字符串
	digits := BcdToDigits(bcd)

	// 解析格式获取小数位数和总长度
	decimalPlaces, _, err := parseFormat(format)
	if err != nil {
		return 0, err
	}
	formatWithoutDot := strings.ReplaceAll(format, ".", "")
	totalLength := len(formatWithoutDot)

	// 若总长度不足，往前补 0
	if len(digits) < totalLength {
		digits = strings.Repeat("0", totalLength-len(digits)) + digits
	}

	// 分离整数部分和小数部分
	integerPart := digits[:len(digits)-decimalPlaces]
	decimalPart := digits[len(digits)-decimalPlaces:]

	// 重新组合并插入小数点
	valueStr := integerPart + "." + decimalPart

	// 解析为浮点数
	value, err := strconv.ParseFloat(valueStr, 32)
	if err != nil {
		return 0, err
	}

	if isNegative {
		value = -value
	}
	return float32(value), nil
}

// 解析格式字符串，返回小数位数和总位数
func parseFormat(format string) (decimalPlaces int, totalDigits int, err error) {
	parts := strings.Split(format, ".")
	if len(parts) != 2 {
		return 0, 0, fmt.Errorf("invalid format: %s", format)
	}
	decimalPlaces = len(parts[1])
	totalDigits = len(parts[0]) + len(parts[1])
	return decimalPlaces, totalDigits, nil
}

// 浮点数四舍五入到指定小数位
func roundFloat(value float32, decimalPlaces int) float32 {
	scale := math.Pow10(decimalPlaces)
	return float32(math.Round(float64(value)*scale) / scale)
}

// 格式化浮点数为固定长度字符串（补零对齐）
func formatFloat(value float32, decimalPlaces, totalDigits int) string {
	format := fmt.Sprintf("%%0%d.%df", totalDigits, decimalPlaces)
	return fmt.Sprintf(format, value)
}

// 将数字字符串转换为BCD码（小端序）
func StringToBCD(digits string, endian binary.ByteOrder) ([]byte, error) {
	if len(digits)%2 != 0 {
		digits = "0" + digits // 奇数位补零
	}

	bcd := make([]byte, len(digits)/2)
	// 从字符串末尾开始处理（低位优先）
	for i := len(digits) - 1; i >= 0; i -= 2 {
		digit1, err := strconv.Atoi(string(digits[i-1]))
		if err != nil || digit1 > 9 {
			return nil, fmt.Errorf("invalid digit: %c", digits[i-1])
		}

		digit2, err := strconv.Atoi(string(digits[i]))
		if err != nil || digit2 > 9 {
			return nil, fmt.Errorf("invalid digit: %c", digits[i])
		}

		if endian == binary.LittleEndian {
			// 存储时反向填充（低字节在前）
			bcd[(len(digits)-i-1)/2] = byte(digit1<<4 | digit2)
		} else {
			// 存储时按正常顺序填充
			bcd[i/2] = byte(digit1<<4 | digit2)
		}
	}
	return bcd, nil
}

// TimeToBCD 将时间转换为BCD码字节数组（小端序）
func TimeToBCD(t time.Time) []byte {
	// 获取当前时间（年月日时分）
	year := uint8(t.Year() % 100) // 取年份后两位（如2025→25）
	month := uint8(t.Month())     // 月份（1-12）
	day := uint8(t.Day())         // 日（1-31）
	hour := uint8(t.Hour())       // 时（0-23）
	minute := uint8(t.Minute())   // 分（0-59）

	log.Printf("Year: %d, Month: %d, Day: %d, Hour: %d, Minute: %d", year, month, day, hour, minute)

	// 组合为BCD格式：YYMMDDHHmm（每个字段占1字节BCD码）
	timeBCD := make([]byte, 5)
	timeBCD[0] = Uint8ToBCD(year)   // 年（后两位）
	timeBCD[1] = Uint8ToBCD(month)  // 月
	timeBCD[2] = Uint8ToBCD(day)    // 日
	timeBCD[3] = Uint8ToBCD(hour)   // 时
	timeBCD[4] = Uint8ToBCD(minute) // 分
	return ReverseBytes(timeBCD)
}

// BCDToByte 将一个字节的BCD码转换为对应的整数
func BCDToByte(b byte) int {
	return int((b>>4)*10 + (b & 0x0F))
}

// BCDToTime 将BCD码字节数组转换为时间
func BCDToTime(bcd []byte) (time.Time, error) {
	if len(bcd) < 5 { // 至少需要5字节（YY MM DD HH mm）
		return time.Time{}, fmt.Errorf("invalid BCD length")
	}
	year := BCDToByte(bcd[0]) + 2000 // 假设为21世纪年份
	month := BCDToByte(bcd[1])
	day := BCDToByte(bcd[2])
	hour := BCDToByte(bcd[3])
	minute := BCDToByte(bcd[4])

	// 直接构造time.Time
	return time.Date(year, time.Month(month), day, hour, minute, 0, 0, time.Local), nil
}

// BytesToSpacedHex 将字节切片转换为每两个字符用空格分隔的十六进制字符串，不足的补0
func BytesToSpacedHex(data []byte) string {
	hexStr := fmt.Sprintf("%x", data)
	// 若十六进制字符串长度为奇数，在前面补0
	if len(hexStr)%2 == 1 {
		hexStr = "0" + hexStr
	}
	var spacedHex string
	for i := 0; i < len(hexStr); i += 2 {
		spacedHex += hexStr[i:i+2] + " "
	}
	// 去掉最后一个多余的空格
	if len(spacedHex) > 0 {
		spacedHex = spacedHex[:len(spacedHex)-1]
	}
	return spacedHex
}

func InterfaceToUint32(i interface{}) (uint32, error) {
	switch v := i.(type) {
	case uint32:
		return v, nil
	case int:
		return uint32(v), nil
	case float32:
		return uint32(v), nil
	case float64:
		return uint32(v), nil
	case string:
		// 处理字符串转uint32
		val, err := strconv.ParseUint(v, 10, 32)
		return uint32(val), err
	default:
		return 0, fmt.Errorf("unsupported type: %T", i)
	}
}

func InterfaceToFloat32(i interface{}) (float32, error) {
	switch v := i.(type) {
	case int:
		return float32(v), nil
	case uint32:
		return float32(v), nil
	case float32:
		return v, nil
	case float64:
		return float32(v), nil
	case string:
		// 处理字符串转float32
		val, err := strconv.ParseFloat(v, 32)
		return float32(val), err
	default:
		return 0, fmt.Errorf("unsupported type: %T", i)
	}
}
