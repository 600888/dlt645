"""
数据项处理模块。

本模块提供了数据项的获取和设置功能，用于管理 DLT645 协议中各类数据项的值。
"""

from typing import Optional, Union, List

from ...model.types.data_type import DataItem, DataFormat
from ...model.types.dlt645_type import Demand, EventRecord
from ...model.log import log
from .define import DIMap


def get_data_item(di: int) -> Optional[DataItem | List[DataItem]]:
    """
    根据数据标识 (DI) 获取数据项。

    :param di: 数据标识，4字节整数。
    :type di: int
    :return: 对应的数据项，可能是单个 DataItem 或 DataItem 列表。
             如果未找到则返回 None。
    :rtype: Optional[DataItem | List[DataItem]]
    """
    item = DIMap.get(di)
    if item is None:
        log.error(f"未通过di {hex(di)} 找到映射")
        return None
    return item


def set_data_item(di: int, data: Union[int, float, str, Demand, list, tuple]) -> bool:
    """
    设置指定数据标识 (DI) 的数据项值。

    根据 DI 的类型自动处理不同的数据格式：
    - 需量数据 (Demand): 验证值后直接设置
    - 事件记录 (0x03xxxxxx): 批量设置事件记录值
    - 参变量时段表 (0x04xxxxxx): 批量设置时段表值
    - 其他数据: 验证后直接设置

    :param di: 数据标识，4字节整数。
    :type di: int
    :param data: 要设置的数据值，类型取决于数据项类型。
    :type data: Union[int, float, str, Demand, list, tuple]
    :return: 设置成功返回 True，失败返回 False。
    :rtype: bool
    """
    if di in DIMap:
        item = DIMap[di]
        if isinstance(data, Demand):
            if not is_value_valid(item.data_format, data.value):
                log.error(f"值 {data} 不符合数据格式: {item.data_format}")
                return False
            item.value = data
        elif 0x03010000 <= di <= 0x03300E0A:  # 事件记录数据
            for data_item, value in zip(item, data):  # data的每一条数据是一个事件记录
                if not is_value_valid(data_item.data_format, value):
                    log.error(f"值 {value} 不符合数据格式: {data_item.data_format}")
                    return False
                data_item.value.event = value
        elif 0x04010000 <= di <= 0x04020008:  # 参变量时段表数据
            for data_item, value in zip(item, data):
                if not is_value_valid(data_item.data_format, value):
                    log.error(f"值 {value} 不符合数据格式: {data_item.data_format}")
                    return False
                data_item.value = value
        else:
            if not is_value_valid(item.data_format, data):
                log.error(f"值 {data} 不符合数据格式: {item.data_format}")
                return False
            item.value = data
        log.debug(f"设置数据项 {hex(di)} 成功, 值 {item}")
        return True
    return False


def is_value_valid(data_format: str, value: Union[int, float, str, tuple]) -> bool:
    """
    检查值是否符合指定的数据格式。

    根据数据格式字符串验证值的有效范围：
    - XXXXXX.XX: 范围 [-799999.99, 799999.99]
    - XXXX.XX: 范围 [-7999.99, 7999.99]
    - XXX.XXX: 范围 [-799.999, 799.999]
    - XX.XXXX: 范围 [-79.9999, 79.9999]
    - XXX.X: 范围 [-799.9, 799.9]
    - X.XXX: 范围 [-0.999, 0.999]
    - 其他格式: 检查字符串长度或递归验证元组

    :param data_format: 数据格式字符串。
    :type data_format: str
    :param value: 待验证的值。
    :type value: Union[int, float, str, tuple]
    :return: 值有效返回 True，无效返回 False。
    :rtype: bool
    """
    if data_format == DataFormat.XXXXXX_XX.value:
        return -799999.99 <= value <= 799999.99
    elif data_format == DataFormat.XXXX_XX.value:
        return -7999.99 <= value <= 7999.99
    elif data_format == DataFormat.XXX_XXX.value:
        return -799.999 <= value <= 799.999
    elif data_format == DataFormat.XX_XXXX.value:
        return -79.9999 <= value <= 79.9999
    elif data_format == DataFormat.XXX_X.value:
        return -799.9 <= value <= 799.9
    elif data_format == DataFormat.X_XXX.value:
        return -0.999 <= value <= 0.999
    else:
        if isinstance(value, str) and len(value) == len(data_format):
            return True
        elif isinstance(value, tuple):
            fmt = data_format.split(",")
            for v, fmt in zip(value, fmt):
                if not is_value_valid(fmt, v):
                    return False
            return True
        else:
            return False

