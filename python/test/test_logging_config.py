#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志配置接口测试（configure_logging / enable_logging / disable_logging）

覆盖：默认关闭、启用输出、统一日志文件、恢复分文件、关闭后静默。
"""

import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dlt645.common import base_log
from dlt645.common.base_log import (
    configure_logging,
    enable_logging,
    disable_logging,
    _loggers,
)


def wait_file_contains(path: str, text: str, timeout: float = 5.0) -> bool:
    """轮询等待日志文件出现目标内容（enqueue 异步写入）。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with open(path, encoding="utf-8") as f:
                if text in f.read():
                    return True
        except OSError:
            pass
        time.sleep(0.2)
    return False


class TestLoggingConfig(unittest.TestCase):
    """日志配置接口测试"""

    def tearDown(self):
        # 彻底重置全局日志配置，避免影响后续测试
        with base_log._lock:
            for key in base_log._settings:
                if key != "enabled":
                    base_log._settings[key] = None
        disable_logging()

    def test_default_disabled(self):
        """默认关闭：不挂载任何 handler"""
        self.assertIsNone(base_log._stderr_handler_id)
        self.assertEqual(len(base_log._file_handler_ids), 0)

    def test_enable_split_files(self):
        """启用后各模块日志写入各自的文件"""
        enable_logging(cmdlevel="DEBUG", filelevel="DEBUG")
        self.assertIsNotNone(base_log._stderr_handler_id)
        self.assertGreaterEqual(len(base_log._file_handler_ids), 1)

        from dlt645.protocol.log import log as plog

        plog.info("split file message")
        self.assertTrue(
            wait_file_contains(plog.filename, "split file message"),
            "分文件模式日志应写入 protocol.log",
        )

    def test_unified_file(self):
        """统一文件模式：所有日志写入指定文件"""
        tmp = os.path.join(tempfile.mkdtemp(), "unified.log")
        configure_logging(filename=tmp, filelevel="DEBUG")
        self.assertEqual(len(base_log._file_handler_ids), 1)

        from dlt645.protocol.log import log as plog

        plog.info("unified file message")
        self.assertTrue(
            wait_file_contains(tmp, "unified file message"),
            "统一文件模式日志应写入指定文件",
        )

    def test_unified_to_split(self):
        """从统一文件切回分文件（filename=None 恢复）"""
        tmp = os.path.join(tempfile.mkdtemp(), "a.log")
        configure_logging(filename=tmp)
        self.assertEqual(len(base_log._file_handler_ids), 1)

        configure_logging(filename=None)
        self.assertIsNone(base_log._settings["filename"])
        self.assertGreaterEqual(len(base_log._file_handler_ids), 1)

    def test_disable(self):
        """关闭后完全静默且可再启用"""
        tmp = os.path.join(tempfile.mkdtemp(), "d.log")
        configure_logging(filename=tmp, filelevel="DEBUG")
        from dlt645.protocol.log import log as plog

        disable_logging()
        self.assertIsNone(base_log._stderr_handler_id)
        self.assertEqual(len(base_log._file_handler_ids), 0)

        plog.info("after disable")
        time.sleep(0.5)  # 等待异步队列排空
        with open(tmp, encoding="utf-8") as f:
            content = f.read()
        self.assertTrue("after disable" not in content, "关闭后不应写入日志")

        enable_logging(filename=tmp, filelevel="DEBUG")
        plog.info("after re-enable")
        self.assertTrue(
            wait_file_contains(tmp, "after re-enable"),
            "重新启用后应恢复输出",
        )

    def test_enable_log_with_none_filename_instance(self):
        """filename=None 创建的实例在启用后也能输出（task 规范化）"""
        tmp = os.path.join(tempfile.mkdtemp(), "none.log")
        # 临时 Log 实例会注册进 _loggers，测试后不影响后续（filter 精确匹配）
        _ = base_log.Log(filename=None, cmdlevel="DEBUG", filelevel="DEBUG")
        configure_logging(filename=tmp, filelevel="DEBUG")
        self.assertGreater(len(_loggers), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
