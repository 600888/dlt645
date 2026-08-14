#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""data_handler 模块测试：is_value_valid 与 get_value_range"""

import os
import sys
import unittest

# 添加python目录（及其 src 源码目录）到Python路径，确保加载本地源码而非已安装的旧版
python_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(python_dir, "src"))
sys.path.insert(0, python_dir)

from dlt645.model.data.data_handler import get_value_range, is_value_valid


class TestGetValueRange(unittest.TestCase):
    """get_value_range 函数测试"""

    def test_known_formats(self):
        """常见小数格式返回与 is_value_valid 一致的范围"""
        self.assertEqual(get_value_range("XXXXXX.XX"), (-799999.99, 799999.99))
        self.assertEqual(get_value_range("XXXX.XX"), (-7999.99, 7999.99))
        self.assertEqual(get_value_range("XXX.XXX"), (-799.999, 799.999))
        self.assertEqual(get_value_range("XX.XXXX"), (-79.9999, 79.9999))
        self.assertEqual(get_value_range("XXX.X"), (-799.9, 799.9))
        self.assertEqual(get_value_range("X.XXX"), (-0.999, 0.999))

    def test_n_format_unsigned(self):
        """N 格式为无符号整数，下限为 0"""
        self.assertEqual(get_value_range("NN"), (0.0, 99.0))
        self.assertEqual(get_value_range("NNNN"), (0.0, 9999.0))
        self.assertEqual(get_value_range("NNNNNNNN"), (0.0, 99999999.0))
        self.assertEqual(get_value_range("NN.NNNN"), (0.0, 99.9999))

    def test_x_format_signed(self):
        """纯 X 数字格式按位数推导有符号范围"""
        self.assertEqual(get_value_range("XXXXXX"), (-999999.0, 999999.0))
        self.assertEqual(get_value_range("XX.XX"), (-99.99, 99.99))

    def test_non_numeric_formats(self):
        """日期时间/多段组合格式返回 None"""
        self.assertIsNone(get_value_range("YYMMDDWW"))
        self.assertIsNone(get_value_range("hhmmss"))
        self.assertIsNone(get_value_range("YYMMDDhhmm"))
        self.assertIsNone(get_value_range("XXXX.XX,XXX.XXX"))

    def test_consistency_with_is_value_valid(self):
        """已知格式的边界值应通过 is_value_valid 校验"""
        for fmt, (lo, hi) in [
            ("XXXXXX.XX", (-799999.99, 799999.99)),
            ("XXXX.XX", (-7999.99, 7999.99)),
            ("XXX.XXX", (-799.999, 799.999)),
            ("XX.XXXX", (-79.9999, 79.9999)),
            ("XXX.X", (-799.9, 799.9)),
            ("X.XXX", (-0.999, 0.999)),
        ]:
            self.assertTrue(is_value_valid(fmt, lo))
            self.assertTrue(is_value_valid(fmt, hi))
            self.assertFalse(is_value_valid(fmt, hi + 1))
            self.assertFalse(is_value_valid(fmt, lo - 1))


if __name__ == "__main__":
    unittest.main()
