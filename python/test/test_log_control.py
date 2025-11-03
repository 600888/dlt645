#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志控制接口测试
"""
import sys

sys.path.append("..")
import unittest
import time
import os
from src.common.base_log import Log


class TestLogControl(unittest.TestCase):
    """日志控制接口测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.log_file = "test_log_control.log"
        self.log = Log(filename=self.log_file, cmdlevel="DEBUG", filelevel="DEBUG")
    
    def test_enable_disable_log(self):
        """测试开启和关闭日志功能"""
        # 测试开启日志
        self.log.enable_log()
        self.log.debug("This is a debug message when log is enabled")
        self.log.info("This is an info message when log is enabled")
        
        # 测试关闭日志
        self.log.disable_log()
        # 这些消息不应该被记录
        self.log.debug("This debug message should not be logged")
        self.log.info("This info message should not be logged")
        
        # 重新开启日志
        self.log.enable_log()
        self.log.warning("Log is enabled again")
        
        # 验证日志文件是否存在
        self.assertTrue(os.path.exists(self.log_file), "Log file should be created")
    
    def test_set_log_level(self):
        """测试设置日志等级功能"""
        # 首先记录一些不同等级的日志
        self.log.debug("Initial debug message")
        self.log.info("Initial info message")
        self.log.warning("Initial warning message")
        
        # 设置日志等级为 WARNING
        result = self.log.set_log_level("WARNING")
        self.assertTrue(result, "Setting log level should return True")
        
        # 只有 WARNING 及以上等级的日志应该被记录
        self.log.debug("This debug message should not be shown with WARNING level")
        self.log.info("This info message should not be shown with WARNING level")
        self.log.warning("This warning message should be shown")
        self.log.error("This error message should be shown")
        
        # 单独设置控制台日志等级
        result = self.log.set_log_level("INFO", is_console=True, is_file=False)
        self.assertTrue(result, "Setting console log level should return True")
        
        # 单独设置文件日志等级
        result = self.log.set_log_level("ERROR", is_console=False, is_file=True)
        self.assertTrue(result, "Setting file log level should return True")
        
        # 测试无效的日志等级
        result = self.log.set_log_level("INVALID_LEVEL")
        self.assertFalse(result, "Setting invalid log level should return False")
    
    def test_console_and_file_levels(self):
        """测试控制台和文件日志等级分别设置"""
        # 设置控制台为 INFO，文件为 ERROR
        self.log.set_log_level("INFO", is_console=True, is_file=False)
        self.log.set_log_level("ERROR", is_console=False, is_file=True)
        
        # 这些日志在控制台和文件中的表现应该不同
        self.log.debug("This debug message should not be shown anywhere")
        self.log.info("This info message should be shown in console only")
        self.log.warning("This warning message should be shown in console only")
        self.log.error("This error message should be shown in both console and file")
    
    def test_log_rotation_configuration(self):
        """测试日志配置的保留"""
        # 验证初始配置是否被正确保留
        self.assertEqual(self.log.cmdlevel, "DEBUG", "Console level should be DEBUG initially")
        self.assertEqual(self.log.filelevel, "DEBUG", "File level should be DEBUG initially")
        
        # 更改配置后验证
        self.log.set_log_level("INFO")
        self.assertEqual(self.log.cmdlevel, "INFO", "Console level should be updated to INFO")
        self.assertEqual(self.log.filelevel, "INFO", "File level should be updated to INFO")


if __name__ == "__main__":
    unittest.main()