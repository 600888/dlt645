"""数据项处理模块。

本模块提供了数据项的获取和设置功能，用于管理 DLT645 协议中各类数据项的值。
"""

from copy import deepcopy
from typing import Dict, List, Optional, Union

from ...model.types.data_type import DataItem
from ...model.types.dlt645_type import Demand
from ...model.log import log
from .define import DIMap

DataMap = Dict[int, DataItem | List[DataItem]]


def clone_data_map() -> DataMap:
    """为单个客户端或服务端创建隔离的数据项快照。"""
    return deepcopy(DIMap)


def get_data_item(
    di: int, data_map: Optional[DataMap] = None
) -> Optional[DataItem | List[DataItem]]:
    """根据数据标识 (DI) 获取数据项。

    :param di: 数据标识，4字节整数。
    :type di: int
    :return: 对应的数据项，可能是单个 DataItem 或 DataItem 列表。
             如果未找到则返回 None。
    :rtype: Optional[DataItem | List[DataItem]]
    """
    item = (DIMap if data_map is None else data_map).get(di)
    if item is None:
        log.error(f"未通过di {hex(di)} 找到映射")
        return None
    return item


def set_data_item(
    di: int,
    data: Union[int, float, str, Demand, list, tuple],
    data_map: Optional[DataMap] = None,
) -> bool:
    """设置指定数据标识 (DI) 的数据项值。

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
    registry = DIMap if data_map is None else data_map
    if di in registry:
        item = registry[di]
        if isinstance(data, Demand):
            if not is_value_valid(
                item.data_format,
                data.value,
                item.min_value,
                item.max_value,
            ):
                log.error(f"值 {data} 不符合数据格式: {item.data_format}")
                return False
            item.value = data
        elif 0x03010000 <= di <= 0x03300E0A:  # 事件记录数据
            for data_item, value in zip(item, data):  # data的每一条数据是一个事件记录
                if not is_value_valid(
                    data_item.data_format,
                    value,
                    data_item.min_value,
                    data_item.max_value,
                ):
                    log.error(f"值 {value} 不符合数据格式: {data_item.data_format}")
                    return False
                data_item.value.event = value
        elif 0x04010000 <= di <= 0x04020008:  # 参变量时段表数据
            for data_item, value in zip(item, data):
                if not is_value_valid(
                    data_item.data_format,
                    value,
                    data_item.min_value,
                    data_item.max_value,
                ):
                    log.error(f"值 {value} 不符合数据格式: {data_item.data_format}")
                    return False
                data_item.value = value
        else:
            if not is_value_valid(
                item.data_format,
                data,
                item.min_value,
                item.max_value,
            ):
                log.error(f"值 {data} 不符合数据格式: {item.data_format}")
                return False
            item.value = data
        log.debug(f"设置数据项 {hex(di)} 成功, 值 {item}")
        return True
    return False


def is_value_valid(
    data_format: str,
    value: Union[int, float, str, tuple],
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
) -> bool:
    """检查值是否符合数据项定义的上下限及数据格式。

    校验规则：
    - 数值类型的值且点位配置了上下限（min_value/max_value 均非 None）时，
      校验数值是否在范围内；
    - 字符串类型检查长度是否与格式一致；
    - 元组递归验证（多段格式）。

    :param data_format: 数据格式字符串。
    :type data_format: str
    :param value: 待验证的值。
    :type value: Union[int, float, str, tuple]
    :param min_value: 数据项允许的最小值，None 表示不限制。
    :type min_value: Optional[float], 可选
    :param max_value: 数据项允许的最大值，None 表示不限制。
    :type max_value: Optional[float], 可选
    :return: 值有效返回 True，无效返回 False。
    :rtype: bool
    """
    if (
        min_value is not None
        and max_value is not None
        and isinstance(value, (int, float))
    ):
        return min_value <= value <= max_value
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

