#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""data_handler 模块测试：点位级上下限校验（is_value_valid / set_data_item / DIMap）"""

import os
import sys
import unittest

# 添加python目录（及其 src 源码目录）到Python路径，确保加载本地源码而非已安装的旧版
python_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(python_dir, "src"))
sys.path.insert(0, python_dir)

from dlt645.model.data.data_handler import (
    clone_data_map,
    is_value_valid,
    set_data_item,
)
from dlt645.model.data.define import DIMap


class TestIsValueValid(unittest.TestCase):
    """is_value_valid 点位级上下限校验测试"""

    def test_with_limits(self):
        """配置了上下限时校验数值范围"""
        self.assertTrue(is_value_valid("XXXXXX.XX", 123.45, -799999.99, 799999.99))
        self.assertTrue(is_value_valid("XXXXXX.XX", -799999.99, -799999.99, 799999.99))
        self.assertTrue(is_value_valid("XXXXXX.XX", 799999.99, -799999.99, 799999.99))
        self.assertFalse(is_value_valid("XXXXXX.XX", 800000.0, -799999.99, 799999.99))
        self.assertFalse(is_value_valid("XXXXXX.XX", -800000.0, -799999.99, 799999.99))

    def test_n_format_unsigned(self):
        """N 格式点位（如 NN 0~99）下限为 0"""
        self.assertTrue(is_value_valid("NN", 50, 0.0, 99.0))
        self.assertTrue(is_value_valid("NN", 0, 0.0, 99.0))
        self.assertFalse(is_value_valid("NN", -1, 0.0, 99.0))
        self.assertFalse(is_value_valid("NN", 100, 0.0, 99.0))

    def test_without_limits_checks_string_length(self):
        """无上下限的点位（日期时间等）按字符串长度校验"""
        # 日期时间格式 YYMMDDWW 无数值上下限
        self.assertTrue(is_value_valid("YYMMDDWW", "24010101", None, None))
        self.assertFalse(is_value_valid("YYMMDDWW", "2401010", None, None))


class TestDataItemLimits(unittest.TestCase):
    """DIMap 中每个点位都应携带上下限"""

    def test_energy_item(self):
        """电能点位格式 XXXXXX.XX -> ±799999.99"""
        item = DIMap[0x00000000]  # （当前）组合有功总电能
        self.assertEqual(item.min_value, -799999.99)
        self.assertEqual(item.max_value, 799999.99)

    def test_demand_item(self):
        """需量点位格式 XX.XXXX -> ±79.9999"""
        item = DIMap[0x01010000]
        self.assertEqual(item.min_value, -79.9999)
        self.assertEqual(item.max_value, 79.9999)

    def test_variable_item(self):
        """变量点位 A相电压 XXX.X -> ±799.9"""
        item = DIMap[0x02010100]
        self.assertEqual(item.min_value, -799.9)
        self.assertEqual(item.max_value, 799.9)

    def test_parameter_item(self):
        """参变量：NN 格式 0~99；日期格式默认 0 ~ 长度个9"""
        item = DIMap[0x04000103]  # 最大需量周期 NN
        self.assertEqual(item.min_value, 0.0)
        self.assertEqual(item.max_value, 99.0)
        item = DIMap[0x04000101]  # 日期及星期 YYMMDDWW -> 8个9
        self.assertEqual(item.min_value, 0.0)
        self.assertEqual(item.max_value, 99999999.0)

    def test_mixed_format_item(self):
        """混合格式（如 YYMMDDNN）按格式总长度默认 0 ~ 8个9"""
        item = DIMap[0x04030001]  # 第1套日时段表切换的日时段表号 YYMMDDNN
        self.assertEqual(item.min_value, 0.0)
        self.assertEqual(item.max_value, 99999999.0)

    def test_time_format_string_value(self):
        """时间格式点位（hhmmss -> 0~999999）写字符串按长度校验，不触发数值比较"""
        item = DIMap[0x04000102]  # 时间 hhmmss
        self.assertEqual(item.min_value, 0.0)
        self.assertEqual(item.max_value, 999999.0)
        # 字符串值走长度校验
        self.assertTrue(is_value_valid(item.data_format, "123456", item.min_value, item.max_value))
        self.assertFalse(is_value_valid(item.data_format, "12345", item.min_value, item.max_value))
        # 数值值走范围校验
        self.assertTrue(is_value_valid(item.data_format, 123456, item.min_value, item.max_value))
        self.assertFalse(is_value_valid(item.data_format, 1000000, item.min_value, item.max_value))

    def test_all_items_have_limit_fields(self):
        """所有点位都存在 min_value/max_value 属性（值可为 None）"""
        checked = 0
        for di, item in DIMap.items():
            if isinstance(item, list):
                for it in item:
                    self.assertTrue(hasattr(it, "min_value"), f"{hex(di)} 缺 min_value")
                    self.assertTrue(hasattr(it, "max_value"), f"{hex(di)} 缺 max_value")
                    checked += 1
            else:
                self.assertTrue(hasattr(item, "min_value"), f"{hex(di)} 缺 min_value")
                self.assertTrue(hasattr(item, "max_value"), f"{hex(di)} 缺 max_value")
                checked += 1
        self.assertGreater(checked, 1000)


class TestSetDataItem(unittest.TestCase):
    """set_data_item 使用点位自身上下限校验"""

    def test_variable_out_of_range_rejected(self):
        """A相电压（±799.9）写 800 被拒绝，写 220 成功"""
        data_map = clone_data_map()
        self.assertFalse(set_data_item(0x02010100, 800.0, data_map))
        self.assertTrue(set_data_item(0x02010100, 220.0, data_map))

    def test_parameter_out_of_range_rejected(self):
        """最大需量周期 NN（0~99）写 100 被拒绝，写 15 成功"""
        data_map = clone_data_map()
        self.assertFalse(set_data_item(0x04000103, 100, data_map))
        self.assertTrue(set_data_item(0x04000103, 15, data_map))


if __name__ == "__main__":
    unittest.main()
